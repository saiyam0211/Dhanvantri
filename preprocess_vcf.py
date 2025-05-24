#!/usr/bin/env python3
"""
VCF Preprocessing and Parallel Annotation

This script preprocesses VCF files by filtering low-confidence variants and
normalizing multi-allelic sites, then performs parallel annotation with SnpEff.
"""

import argparse
import logging
import os
import sys
import subprocess
import tempfile
from pathlib import Path
import multiprocessing
import shutil
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Preprocess and annotate VCF files in parallel"
    )
    parser.add_argument(
        "--vcf", 
        required=True, 
        help="Path to the input VCF file"
    )
    parser.add_argument(
        "--output", 
        help="Path to the output annotated VCF file (default: input.ann.vcf.gz)"
    )
    parser.add_argument(
        "--genome", 
        default="hg38", 
        help="Genome version for SnpEff annotation (default: hg38)"
    )
    parser.add_argument(
        "--threads", 
        type=int, 
        default=multiprocessing.cpu_count(),
        help=f"Number of parallel processes (default: {multiprocessing.cpu_count()})"
    )
    parser.add_argument(
        "--min-depth", 
        type=int, 
        default=10,
        help="Minimum read depth for variant filtering (default: 10)"
    )
    parser.add_argument(
        "--bed", 
        help="Optional BED file to restrict to coding regions"
    )
    parser.add_argument(
        "--snpeff-path", 
        default="snpEff.jar",
        help="Path to SnpEff JAR file (default: snpEff.jar)"
    )
    parser.add_argument(
        "--memory", 
        default="2g",
        help="Memory allocation for Java (default: 2g)"
    )
    parser.add_argument(
        "--temp-dir",
        help="Directory to store temporary files (default: system temp directory)"
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temporary files after processing"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    return parser.parse_args()

def check_dependencies():
    """Check if required tools are installed."""
    tools = ["bcftools", "bgzip", "tabix", "java"]
    
    for tool in tools:
        try:
            subprocess.run([tool, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            logger.debug(f"{tool} is installed")
        except FileNotFoundError:
            logger.error(f"{tool} is not installed. Please install it before running this script.")
            sys.exit(1)
    
    return True

def preprocess_vcf(input_vcf, output_vcf, min_depth=10, bed_file=None):
    """
    Preprocess VCF file by filtering low-confidence variants and normalizing multi-allelic sites.
    
    Args:
        input_vcf: Path to input VCF file
        output_vcf: Path to output filtered VCF file
        min_depth: Minimum read depth for variant filtering
        bed_file: Optional BED file to restrict to coding regions
        
    Returns:
        Path to preprocessed VCF file
    """
    logger.info(f"Preprocessing VCF file: {input_vcf}")
    start_time = time.time()
    
    # Build the bcftools command
    cmd = ["bcftools", "view"]
    
    # Add depth filter if DP field exists
    cmd.extend(["-i", f"INFO/DP>{min_depth}"])
    
    # Add BED file if provided
    if bed_file:
        cmd.extend(["-R", str(bed_file)])
    
    cmd.append(str(input_vcf))
    
    # Pipe to normalization
    cmd.extend(["| bcftools", "norm", "-m", "-any"])
    
    # Compress output
    cmd.extend(["-Oz", "-o", str(output_vcf)])
    
    # Run the command
    # Convert any Path objects to strings before joining
    cmd_str = [str(item) for item in cmd]
    logger.info(f"Running: {' '.join(cmd_str)}")
    
    # Since we have pipes, we need to use shell=True
    shell_cmd = " ".join(cmd_str)
    process = subprocess.run(shell_cmd, shell=True, check=False, stderr=subprocess.PIPE)
    
    if process.returncode != 0:
        logger.error(f"Error preprocessing VCF file: {process.stderr.decode()}")
        sys.exit(1)
    
    # Index the output file
    logger.info(f"Indexing preprocessed VCF file: {output_vcf}")
    subprocess.run(["bcftools", "index", str(output_vcf)], check=True)
    
    elapsed_time = time.time() - start_time
    logger.info(f"Preprocessing completed in {elapsed_time:.2f} seconds")
    
    return output_vcf

def split_vcf_by_chromosome(input_vcf, output_dir):
    """
    Split VCF file by chromosome.
    
    Args:
        input_vcf: Path to input VCF file
        output_dir: Directory to store split VCF files
        
    Returns:
        List of paths to split VCF files
    """
    logger.info(f"Splitting VCF file by chromosome: {input_vcf}")
    start_time = time.time()
    
    # Get list of chromosomes
    cmd = ["bcftools", "index", "--stats", input_vcf]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
    
    # Parse the output to get chromosomes
    chromosomes = []
    for line in process.stdout.decode().splitlines():
        if line and not line.startswith("#"):
            chrom = line.split()[0]
            chromosomes.append(chrom)
    
    logger.info(f"Found {len(chromosomes)} chromosomes: {', '.join(chromosomes[:5])}...")
    
    # Split VCF by chromosome
    split_files = []
    for chrom in chromosomes:
        output_file = os.path.join(output_dir, f"{chrom}.vcf.gz")
        cmd = ["bcftools", "view", "-r", chrom, input_vcf, "-Oz", "-o", output_file]
        
        logger.debug(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        # Index the split file
        subprocess.run(["bcftools", "index", output_file], check=True)
        
        split_files.append(output_file)
    
    elapsed_time = time.time() - start_time
    logger.info(f"Split VCF into {len(split_files)} files in {elapsed_time:.2f} seconds")
    
    return split_files

def split_vcf_by_lines(input_vcf, output_dir, num_parts):
    """
    Split VCF file by lines into equal parts.
    
    Args:
        input_vcf: Path to input VCF file
        output_dir: Directory to store split VCF files
        num_parts: Number of parts to split into
        
    Returns:
        List of paths to split VCF files
    """
    logger.info(f"Splitting VCF file into {num_parts} parts: {input_vcf}")
    start_time = time.time()
    
    # Count non-header lines in VCF
    cmd = ["bcftools", "view", "-H", input_vcf, "-Oz", "-o", "/dev/null", "--output-type", "z"]
    process = subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
    
    # Extract the number of records from stderr
    stderr = process.stderr.decode()
    num_records = 0
    for line in stderr.splitlines():
        if "number of records" in line.lower():
            num_records = int(line.split()[-1])
            break
    
    if num_records == 0:
        logger.warning("Could not determine number of records, using alternative method")
        # Alternative method: count lines
        cmd = f"bcftools view -H {input_vcf} | wc -l"
        process = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, check=True)
        num_records = int(process.stdout.decode().strip())
    
    logger.info(f"VCF file contains {num_records} variants")
    
    # Calculate lines per part
    lines_per_part = max(1, num_records // num_parts)
    logger.info(f"Splitting into {num_parts} parts with ~{lines_per_part} variants each")
    
    # Extract header
    header_file = os.path.join(output_dir, "header.txt")
    subprocess.run(["bcftools", "view", "-h", input_vcf, "-o", header_file], check=True)
    
    # Split VCF into parts
    split_files = []
    for i in range(num_parts):
        start_line = i * lines_per_part + 1
        end_line = (i + 1) * lines_per_part if i < num_parts - 1 else num_records
        
        # Skip if this part would be empty
        if start_line > num_records:
            continue
        
        output_file = os.path.join(output_dir, f"part_{i:03d}.vcf.gz")
        
        # Extract variants for this part
        cmd = f"bcftools view -H {input_vcf} | sed -n '{start_line},{end_line}p' | cat {header_file} - | bcftools view -Oz -o {output_file}"
        logger.debug(f"Running: {cmd}")
        subprocess.run(cmd, shell=True, check=True)
        
        # Index the split file
        subprocess.run(["bcftools", "index", output_file], check=True)
        
        split_files.append(output_file)
    
    # Remove header file
    os.unlink(header_file)
    
    elapsed_time = time.time() - start_time
    logger.info(f"Split VCF into {len(split_files)} parts in {elapsed_time:.2f} seconds")
    
    return split_files

def annotate_vcf(input_vcf, output_vcf, genome, snpeff_path, memory):
    """
    Annotate VCF file with SnpEff.
    
    Args:
        input_vcf: Path to input VCF file
        output_vcf: Path to output annotated VCF file
        genome: Genome version for SnpEff
        snpeff_path: Path to SnpEff JAR file
        memory: Memory allocation for Java
        
    Returns:
        Path to annotated VCF file
    """
    logger.info(f"Annotating VCF file: {input_vcf}")
    start_time = time.time()
    
    # Build the SnpEff command
    cmd = [
        "java", f"-Xmx{memory}", "-jar", snpeff_path,
        "-noLog", "-canon", "-noStats",
        genome, input_vcf, ">", output_vcf
    ]
    
    # Run the command
    logger.debug(f"Running: {' '.join(cmd)}")
    shell_cmd = " ".join(cmd)
    process = subprocess.run(shell_cmd, shell=True, check=False, stderr=subprocess.PIPE)
    
    if process.returncode != 0:
        logger.error(f"Error annotating VCF file: {process.stderr.decode()}")
        sys.exit(1)
    
    elapsed_time = time.time() - start_time
    logger.info(f"Annotation completed in {elapsed_time:.2f} seconds")
    
    return output_vcf

def annotate_in_parallel(split_files, output_dir, genome, snpeff_path, memory, threads):
    """
    Annotate split VCF files in parallel.
    
    Args:
        split_files: List of paths to split VCF files
        output_dir: Directory to store annotated VCF files
        genome: Genome version for SnpEff
        snpeff_path: Path to SnpEff JAR file
        memory: Memory allocation for Java
        threads: Number of parallel processes
        
    Returns:
        List of paths to annotated VCF files
    """
    logger.info(f"Annotating {len(split_files)} VCF files in parallel using {threads} threads")
    start_time = time.time()
    
    # Prepare arguments for parallel annotation
    annotation_tasks = []
    for input_file in split_files:
        output_file = os.path.join(output_dir, os.path.basename(input_file).replace(".vcf.gz", ".ann.vcf"))
        annotation_tasks.append((input_file, output_file, genome, snpeff_path, memory))
    
    # Run annotation in parallel
    from concurrent.futures import ProcessPoolExecutor
    annotated_files = []
    
    with ProcessPoolExecutor(max_workers=threads) as executor:
        # Submit tasks
        futures = [executor.submit(annotate_vcf, *task) for task in annotation_tasks]
        
        # Wait for completion and collect results
        for future in futures:
            try:
                annotated_file = future.result()
                annotated_files.append(annotated_file)
            except Exception as e:
                logger.error(f"Error in parallel annotation: {e}")
    
    elapsed_time = time.time() - start_time
    logger.info(f"Parallel annotation completed in {elapsed_time:.2f} seconds")
    
    return annotated_files

def merge_vcf_files(input_files, output_file):
    """
    Merge multiple VCF files into one.
    
    Args:
        input_files: List of paths to input VCF files
        output_file: Path to output merged VCF file
        
    Returns:
        Path to merged VCF file
    """
    logger.info(f"Merging {len(input_files)} VCF files")
    start_time = time.time()
    
    # Build the bcftools command
    cmd = ["bcftools", "concat"]
    cmd.extend(input_files)
    cmd.extend(["-Oz", "-o", output_file])
    
    # Run the command
    logger.debug(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    # Index the merged file
    subprocess.run(["bcftools", "index", output_file], check=True)
    
    elapsed_time = time.time() - start_time
    logger.info(f"Merging completed in {elapsed_time:.2f} seconds")
    
    return output_file

def main():
    """Main entry point for VCF preprocessing and parallel annotation."""
    args = parse_arguments()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check dependencies
    check_dependencies()
    
    # Validate input file
    input_vcf = Path(args.vcf)
    if not input_vcf.exists():
        logger.error(f"Input VCF file not found: {input_vcf}")
        sys.exit(1)
    
    # Set output file
    if args.output:
        output_vcf = Path(args.output)
    else:
        output_vcf = input_vcf.with_suffix(".ann.vcf.gz")
    
    # Create temporary directory
    if args.temp_dir:
        temp_dir = Path(args.temp_dir)
        temp_dir.mkdir(exist_ok=True)
        cleanup_temp = False
    else:
        temp_dir = Path(tempfile.mkdtemp())
        cleanup_temp = True
    
    logger.info(f"Using temporary directory: {temp_dir}")
    
    try:
        # Preprocess VCF
        filtered_vcf = os.path.join(temp_dir, "filtered.vcf.gz")
        preprocess_vcf(input_vcf, filtered_vcf, args.min_depth, args.bed)
        
        # Split VCF
        split_dir = os.path.join(temp_dir, "split")
        os.makedirs(split_dir, exist_ok=True)
        
        # Determine split method based on file size
        vcf_size = os.path.getsize(filtered_vcf)
        if vcf_size > 1_000_000_000:  # 1GB
            # For very large files, split by lines
            split_files = split_vcf_by_lines(filtered_vcf, split_dir, args.threads)
        else:
            # For smaller files, split by chromosome
            split_files = split_vcf_by_chromosome(filtered_vcf, split_dir)
        
        # Annotate in parallel
        annotated_dir = os.path.join(temp_dir, "annotated")
        os.makedirs(annotated_dir, exist_ok=True)
        annotated_files = annotate_in_parallel(
            split_files, annotated_dir, args.genome, args.snpeff_path, args.memory, args.threads
        )
        
        # Merge annotated files
        merge_vcf_files(annotated_files, output_vcf)
        
        logger.info(f"Annotation completed. Output file: {output_vcf}")
        
    finally:
        # Clean up temporary files
        if cleanup_temp and not args.keep_temp:
            logger.info(f"Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir)
        elif args.keep_temp:
            logger.info(f"Temporary files kept in: {temp_dir}")

if __name__ == "__main__":
    main() 
