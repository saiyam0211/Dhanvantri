#!/usr/bin/env python3
import os
import logging
import json
import time
import multiprocessing
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import tempfile
import shutil
import subprocess

from simple_vcf_parser import SimpleVCFParser, Variant
from annotator import SnpEffAnnotator, AnnotatedVariant
from drug_mapper import DrugMapper, DrugGeneInteraction

logger = logging.getLogger(__name__)

def count_variants(vcf_path: Path) -> int:
    logger.info(f"Counting variants in {vcf_path}")
    count = 0
    
    try:
        with open(vcf_path, 'r') as vcf_file:
            for line in vcf_file:
                if not line.startswith('#'):
                    count += 1
                    if count % 100000 == 0:
                        logger.debug(f"Counted {count} variants so far")
    except Exception as e:
        logger.error(f"Error counting variants: {e}")
        raise
    
    logger.info(f"Total variants in {vcf_path}: {count}")
    return count

def extract_batch(vcf_path: Path, batch_index: int, batch_size: int) -> Path:
    start_line = batch_index * batch_size
    end_line = start_line + batch_size
    
    logger.info(f"Extracting batch {batch_index} (variants {start_line}-{end_line}) from {vcf_path}")
    
    # Create a temporary file for the batch
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.vcf')
    temp_path = Path(temp_file.name)
    temp_file.close()
    
    try:
        with open(vcf_path, 'r') as vcf_file, open(temp_path, 'w') as batch_file:
            # Copy header lines
            for line in vcf_file:
                if line.startswith('#'):
                    batch_file.write(line)
                else:
                    break
            
            # Skip to the start of the batch
            vcf_file.seek(0)
            line_count = 0
            for line in vcf_file:
                if line.startswith('#'):
                    continue
                
                line_count += 1
                if line_count > end_line:
                    break
                
                if line_count > start_line:
                    batch_file.write(line)
    
    except Exception as e:
        logger.error(f"Error extracting batch: {e}")
        os.unlink(temp_path)
        raise
    
    logger.info(f"Batch {batch_index} extracted to {temp_path}")
    return temp_path

def process_batch(
    vcf_path: Path,
    batch_index: int,
    batch_size: int,
    drugs: List[str],
    genome_version: str,
    skip_annotation: bool,
    output_dir: Path
) -> Path:
    logger.info(f"Processing batch {batch_index}")
    start_time = time.time()
    
    # Extract the batch
    batch_file = extract_batch(vcf_path, batch_index, batch_size)
    
    try:
        # Parse the batch
        vcf_parser = SimpleVCFParser()
        variants = vcf_parser.parse_vcf(str(batch_file))
        logger.info(f"Parsed {len(variants)} variants in batch {batch_index}")
        
        # Annotate variants
        if skip_annotation:
            logger.info(f"Skipping annotation for batch {batch_index}")
            annotated_variants = [AnnotatedVariant(variant=v) for v in variants]
        else:
            logger.info(f"Annotating batch {batch_index} with SnpEff using genome {genome_version}")
            annotator = SnpEffAnnotator(genome_version=genome_version)
            annotated_variants = annotator.annotate(variants)
            logger.info(f"Annotated {len(annotated_variants)} variants in batch {batch_index}")
        
        # Map drugs to genes
        drug_mapper = DrugMapper(data_dir=Path("data"))
        drug_gene_interactions = drug_mapper.map_drugs_to_genes(drugs, annotated_variants)
        logger.info(f"Found {len(drug_gene_interactions)} drug-gene interactions in batch {batch_index}")
        
        # Save results
        output_file = output_dir / f"batch_{batch_index}.json"
        save_batch_results(drug_gene_interactions, output_file)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Batch {batch_index} processed in {elapsed_time:.2f} seconds")
        
        return output_file
        
    finally:
        # Clean up temporary batch file
        try:
            os.unlink(batch_file)
        except Exception as e:
            logger.warning(f"Error deleting temporary batch file {batch_file}: {e}")

def save_batch_results(interactions: List[DrugGeneInteraction], output_file: Path) -> None:
    # Convert interactions to dictionaries
    interaction_dicts = []
    for interaction in interactions:
        interaction_dicts.append(interaction.to_dict())
    
    # Create directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save to JSON file
    with open(output_file, 'w') as f:
        json.dump(interaction_dicts, f)
    
    logger.debug(f"Saved {len(interactions)} interactions to {output_file}")

def load_batch_results(batch_file: Path) -> List[DrugGeneInteraction]:
    if not batch_file.exists():
        logger.warning(f"Batch file not found: {batch_file}")
        return []
    
    try:
        with open(batch_file, 'r') as f:
            interaction_dicts = json.load(f)
        
        # Convert dictionaries to DrugGeneInteraction objects
        interactions = []
        for interaction_dict in interaction_dicts:
            interactions.append(DrugGeneInteraction.from_dict(interaction_dict))
        
        logger.debug(f"Loaded {len(interactions)} interactions from {batch_file}")
        return interactions
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse JSON from {batch_file}, file may be empty or invalid")
        return []

def merge_batch_results(batch_files: List[Path]) -> List[DrugGeneInteraction]:
    logger.info(f"Merging results from {len(batch_files)} batches")
    
    all_interactions = []
    
    for batch_file in batch_files:
        try:
            interactions = load_batch_results(batch_file)
            all_interactions.extend(interactions)
            logger.debug(f"Loaded {len(interactions)} interactions from {batch_file}")
        except Exception as e:
            logger.error(f"Error loading batch results from {batch_file}: {e}")
    
    # Deduplicate interactions based on drug-gene pairs
    unique_interactions = {}
    
    for interaction in all_interactions:
        key = f"{interaction.drug.lower()}_{interaction.gene.lower()}"
        
        if key not in unique_interactions:
            unique_interactions[key] = interaction
        else:
            # Merge information from multiple sources
            existing = unique_interactions[key]
            
            # Combine sources
            if existing.source != interaction.source:
                existing.source = f"{existing.source}, {interaction.source}"
            
            # Take non-None phenotype
            if existing.phenotype is None and interaction.phenotype is not None:
                existing.phenotype = interaction.phenotype
            
            # Take highest evidence level
            if interaction.evidence_level and (
                existing.evidence_level is None or 
                interaction.evidence_level < existing.evidence_level
            ):
                existing.evidence_level = interaction.evidence_level
            
            # Combine recommendations
            if interaction.recommendation and existing.recommendation:
                existing.recommendation = f"{existing.recommendation}\n\n{interaction.recommendation}"
            elif interaction.recommendation:
                existing.recommendation = interaction.recommendation
            
            # Combine literature references
            existing.literature_refs.extend(interaction.literature_refs)
            existing.literature_refs = list(set(existing.literature_refs))  # Remove duplicates
    
    logger.info(f"Merged {len(all_interactions)} interactions into {len(unique_interactions)} unique interactions")
    
    return list(unique_interactions.values())

def process_in_parallel(
    vcf_path: Path,
    total_variants: int,
    batch_size: int,
    drugs: List[str],
    genome_version: str,
    skip_annotation: bool,
    num_processes: int
) -> List[DrugGeneInteraction]:
    logger.info(f"Processing {total_variants} variants in parallel using {num_processes} processes")
    
    # Calculate number of batches
    num_batches = (total_variants + batch_size - 1) // batch_size
    logger.info(f"Splitting into {num_batches} batches of {batch_size} variants each")
    
    # Create temporary directory for batch results
    temp_dir = Path(tempfile.mkdtemp())
    logger.debug(f"Created temporary directory for batch results: {temp_dir}")
    
    try:
        # Process batches in parallel
        if num_processes > 1:
            pool = multiprocessing.Pool(processes=num_processes)
            batch_results = []
            
            # Submit batch processing tasks
            for batch_index in range(num_batches):
                result = pool.apply_async(
                    process_batch,
                    args=(vcf_path, batch_index, batch_size, drugs, genome_version, skip_annotation, temp_dir)
                )
                batch_results.append(result)
            
            # Close the pool and wait for all tasks to complete
            pool.close()
            pool.join()
            
            # Get the results
            batch_files = [result.get() for result in batch_results]
            
        else:
            # Process batches sequentially
            batch_files = []
            for batch_index in range(num_batches):
                batch_file = process_batch(
                    vcf_path, batch_index, batch_size, drugs, genome_version, skip_annotation, temp_dir
                )
                batch_files.append(batch_file)
        
        # Merge results
        all_interactions = merge_batch_results(batch_files)
        return all_interactions
        
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Error deleting temporary directory {temp_dir}: {e}")

def process_single_batch(
    vcf_path: Path,
    batch_index: int,
    batch_size: int,
    drugs: List[str],
    genome_version: str,
    skip_annotation: bool
) -> List[DrugGeneInteraction]:
    logger.info(f"Processing single batch {batch_index}")
    
    # Create temporary directory for batch results
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Process the batch
        batch_file = process_batch(
            vcf_path, batch_index, batch_size, drugs, genome_version, skip_annotation, temp_dir
        )
        
        # Load the results
        interactions = load_batch_results(batch_file)
        return interactions
        
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Error deleting temporary directory {temp_dir}: {e}")

def estimate_batch_count(vcf_path: Path, batch_size: int) -> int:
    # Get file size
    file_size = os.path.getsize(vcf_path)
    
    # Count header lines and estimate data lines
    header_lines = 0
    header_size = 0
    sample_lines = 0
    sample_size = 0
    
    with open(vcf_path, 'r') as f:
        # First pass: count headers and sample some data lines
        for i, line in enumerate(f):
            if line.startswith('#'):
                header_lines += 1
                header_size += len(line.encode('utf-8'))
            else:
                sample_lines += 1
                sample_size += len(line.encode('utf-8'))
                
                # Sample at most 1000 data lines
                if sample_lines >= 1000:
                    break
    
    # If we have sample data lines, use them to estimate
    if sample_lines > 0:
        # Calculate average data line size
        avg_line_size = sample_size / sample_lines
        
        # Estimate total data size and number of variants
        data_size = file_size - header_size
        estimated_variants = int(data_size / avg_line_size)
        
        # Calculate number of batches
        num_batches = (estimated_variants + batch_size - 1) // batch_size
        
        logger.info(f"Estimated {estimated_variants} variants in {vcf_path}")
        logger.info(f"Estimated {num_batches} batches of {batch_size} variants each")
        
        return num_batches
    
    # Fallback: count all variants (slower but reliable)
    logger.warning("Could not estimate variant count, falling back to counting all variants")
    count = 0
    with open(vcf_path, 'r') as f:
        for line in f:
            if not line.startswith('#'):
                count += 1
    
    num_batches = (count + batch_size - 1) // batch_size
    logger.info(f"Counted {count} variants in {vcf_path}")
    logger.info(f"Will use {num_batches} batches of {batch_size} variants each")
    
    return num_batches 
