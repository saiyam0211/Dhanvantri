#!/usr/bin/env python3

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import httpx
from vcf_parser import Variant

logger = logging.getLogger(__name__)

@dataclass
class AnnotatedVariant:
    """Class representing an annotated genetic variant."""
    chrom: str
    pos: int
    ref: str
    alt: str
    gene_symbol: Optional[str] = None
    variant_id: Optional[str] = None
    annotations: List[Dict[str, Any]] = None
    info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.annotations is None:
            self.annotations = []
        if self.info is None:
            self.info = {}

class BaseAnnotator:
    """Base class for variant annotators."""
    
    def annotate(self, variants: List[Variant]) -> List[AnnotatedVariant]:
        if not variants:
            return []
            
        logger.info(f"Annotating {len(variants)} variants using SnpEff")
        
        try:
            # Check if we need to use file-based processing for large batches
            if len(variants) > 1000:
                logger.info("Large batch detected, using file-based processing")
                return self.annotate_from_file(variants)
                
            # For smaller batches, use direct annotation
            annotated_variants = []
            for variant in variants:
                annotated_variant = self.annotate_variant(variant)
                annotated_variants.append(annotated_variant)
                
            return annotated_variants
            
        except Exception as e:
            logger.error(f"Error during annotation: {e}")
            logger.warning("Falling back to unannotated variants due to error")
            # Create basic annotated variants without annotation
            return [
                AnnotatedVariant(
                    chrom=v.chrom,
                    pos=v.pos,
                    ref=v.ref,
                    alt=v.alt,
                    variant_id=v.id,
                    info=v.info
                ) for v in variants
            ]

class SnpEffAnnotator(BaseAnnotator):
    """Annotator using SnpEff for variant annotation."""
    
    def __init__(self, snpeff_jar: Optional[Path] = None, genome: str = "hg38", memory: str = "4g", genome_version: str = None):
        self.genome = genome_version if genome_version else genome
        
        # Use JAVA_OPTS environment variable for memory if available
        java_opts = os.environ.get("JAVA_OPTS", "")
        if "-Xmx" in java_opts:
            self.memory = java_opts.split("-Xmx")[1].split()[0]
        else:
            self.memory = memory
        
        logger.info(f"Using Java memory setting: -Xmx{self.memory}")
        
        # Get config file path from environment variable
        self.config_file = os.environ.get("SNPEFF_CONFIG")
        if self.config_file:
            logger.info(f"Using SnpEff config file from environment: {self.config_file}")
        
        # Find SnpEff JAR
        if snpeff_jar:
            self.snpeff_jar = snpeff_jar
        else:
            # Try common locations and environment variable
            snpeff_jar_env = os.environ.get("SNPEFF_JAR")
            possible_paths = [
                Path(snpeff_jar_env) if snpeff_jar_env else None,
                Path("~/tools/snpEff/snpEff.jar").expanduser(),
                Path("tools/snpEff/snpEff.jar"),
                Path("snpEff/snpEff.jar"),
                Path("/usr/local/bin/snpEff.jar"),
                Path("/opt/snpeff/snpEff/snpEff.jar")
            ]
            
            for path in possible_paths:
                if path and path.exists():
                    self.snpeff_jar = path
                    break
            
            if not hasattr(self, 'snpeff_jar'):
                raise FileNotFoundError("SnpEff JAR file not found. Please specify the path or set SNPEFF_JAR environment variable.")
            
            logger.info(f"Using SnpEff JAR: {self.snpeff_jar}")
        
        # Verify database exists
        self._verify_database()
    
    def _verify_database(self):
        """Verify that the SnpEff database exists and is properly configured."""
        snpeff_home = os.environ.get("SNPEFF_HOME", str(self.snpeff_jar.parent))
        database_path = Path(snpeff_home) / "data" / self.genome / "snpEffectPredictor.bin"
        
        if not database_path.exists():
            logger.warning(f"SnpEff database not found at {database_path}")
            logger.info("Attempting to download database...")
            
            try:
                # Try to download the database
                cmd = [
                    "java", f"-Xmx{self.memory}", "-jar", str(self.snpeff_jar), 
                    "download", "-v", self.genome
                ]
                
                if self.config_file:
                    cmd.extend(["-c", self.config_file])
                
                logger.info(f"Running: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                
                if result.returncode != 0:
                    logger.error(f"Failed to download SnpEff database: {result.stderr}")
                    
                    # Try with less memory if that might be the issue
                    if "OutOfMemoryError" in result.stderr:
                        reduced_memory = "2g"
                        logger.info(f"Trying again with reduced memory: {reduced_memory}")
                        cmd[1] = f"-Xmx{reduced_memory}"
                        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    
                    if result.returncode != 0:
                        logger.error("Database download failed after retry")
                        raise RuntimeError(f"Failed to download SnpEff database: {result.stderr}")
                
                # Verify database was downloaded
                if not database_path.exists():
                    logger.error(f"Database file still not found at {database_path} after download")
                    raise FileNotFoundError(f"SnpEff database file not found at {database_path} after download attempt")
                
                logger.info("Database downloaded successfully")
                
            except Exception as e:
                logger.error(f"Error downloading SnpEff database: {e}")
                raise RuntimeError(f"Failed to download SnpEff database: {e}")
    
    def annotate(self, variants: List[Variant]) -> List[AnnotatedVariant]:
        if not variants:
            return []
            
        logger.info(f"Annotating {len(variants)} variants using SnpEff")
        
        try:
            # Check if we need to use file-based processing for large batches
            if len(variants) > 1000:
                logger.info("Large batch detected, using file-based processing")
                return self.file_based_annotation(variants)
                
            # For smaller batches, use direct annotation
            annotated_variants = []
            for variant in variants:
                annotated_variant = self._annotate_variant(variant)
                annotated_variants.append(annotated_variant)
                
            return annotated_variants
        except Exception as e:
            logger.error(f"Error during SnpEff annotation: {e}")
            # Don't silently fall back to unannotated variants unless explicitly requested
            raise
    
    def _annotate_variant(self, variant: Variant) -> AnnotatedVariant:
        # For now, just create a basic annotated variant with gene info from the VCF
        gene_symbol = None
        if "GENE" in variant.info:
            gene_symbol = variant.info["GENE"]
            
        return AnnotatedVariant(
            chrom=variant.chrom,
            pos=variant.pos,
            ref=variant.ref,
            alt=variant.alt,
            variant_id=variant.id,
            gene_symbol=gene_symbol,
            info=variant.info
        )

    def file_based_annotation(self, variants: List[Variant]) -> List[AnnotatedVariant]:
        try:
            # Create temporary files for input and output
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vcf') as temp_in:
                temp_in_path = temp_in.name
                
                # Write variants to the temporary file
                temp_in.write("##fileformat=VCFv4.2\n")
                temp_in.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
                
                for v in variants:
                    variant_id = v.id if v.id else "."
                    qual = v.qual if hasattr(v, 'qual') and v.qual else "."
                    filter_val = v.filter if hasattr(v, 'filter') and v.filter else "."
                    info = "."
                    temp_in.write(f"{v.chrom}\t{v.pos}\t{variant_id}\t{v.ref}\t{v.alt}\t{qual}\t{filter_val}\t{info}\n")
            
            # Create output file path
            temp_out_path = temp_in_path + ".ann.vcf"
            
            # Build the SnpEff command
            cmd = [
                "java", f"-Xmx{self.memory}", 
                "-jar", str(self.snpeff_jar)
            ]
            
            # Add config file if specified
            if self.config_file:
                cmd.extend(["-c", self.config_file])
            
            # Add the rest of the command
            cmd.extend([
                "ann", self.genome,
                "-v", str(temp_in_path),
                "-o", "vcf"
            ])
            
            logger.info(f"Running SnpEff command: {' '.join(cmd)}")
            
            # Run SnpEff with output redirection
            with open(temp_out_path, 'w') as out_file:
                result = subprocess.run(cmd, stdout=out_file, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                logger.error(f"SnpEff execution failed: {result.stderr}")
                
                # If we get an out of memory error, try with reduced memory
                if "java.lang.OutOfMemoryError" in result.stderr:
                    logger.warning("SnpEff ran out of memory, retrying with reduced memory")
                    
                    # Reduce memory by half
                    reduced_memory = f"{int(int(self.memory[:-1])/2)}g"
                    cmd[1] = f"-Xmx{reduced_memory}"
                    
                    with open(temp_out_path, 'w') as out_file:
                        result = subprocess.run(cmd, stdout=out_file, stderr=subprocess.PIPE, text=True)
                    
                    if result.returncode != 0:
                        raise RuntimeError(f"SnpEff execution failed even with reduced memory: {result.stderr}")
                else:
                    raise RuntimeError(f"SnpEff execution failed: {result.stderr}")
            
            # Parse the annotated VCF and create annotated variants
            annotated_variants = []
            
            # Create a mapping of original variants by position for lookup
            variant_map = {f"{v.chrom}:{v.pos}_{v.ref}_{v.alt}": v for v in variants}
            
            # Parse the annotated VCF
            with open(temp_out_path, 'r') as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    
                    parts = line.strip().split('\t')
                    if len(parts) < 8:
                        continue
                    
                    chrom, pos, variant_id, ref, alt, qual, filter_val, info = parts[:8]
                    pos = int(pos)
                    
                    # Create a key to look up the original variant
                    key = f"{chrom}:{pos}_{ref}_{alt}"
                    
                    if key in variant_map:
                        original_variant = variant_map[key]
                        
                        # Extract gene information from the ANN field
                        gene_symbol = None
                        annotations = []
                        
                        if "ANN=" in info:
                            ann_part = info.split("ANN=")[1].split(";")[0]
                            ann_entries = ann_part.split(",")
                            
                            for entry in ann_entries:
                                fields = entry.split("|")
                                if len(fields) > 3:
                                    # Gene name is typically in the 4th field
                                    if not gene_symbol and fields[3]:
                                        gene_symbol = fields[3]
                                    
                                    # Create an annotation entry
                                    annotation = {
                                        "allele": fields[0],
                                        "effect": fields[1],
                                        "impact": fields[2],
                                        "gene": fields[3] if len(fields) > 3 else None,
                                        "gene_id": fields[4] if len(fields) > 4 else None,
                                    }
                                    annotations.append(annotation)
                        
                        # If we still don't have a gene symbol, try to get it from the original variant
                        if not gene_symbol and hasattr(original_variant, 'info') and "GENE" in original_variant.info:
                            gene_symbol = original_variant.info["GENE"]
                        
                        # Create annotated variant
                        annotated_variant = AnnotatedVariant(
                            chrom=chrom,
                            pos=pos,
                            ref=ref,
                            alt=alt,
                            variant_id=variant_id if variant_id != "." else None,
                            gene_symbol=gene_symbol,
                            annotations=annotations,
                            info=original_variant.info if hasattr(original_variant, 'info') else {}
                        )
                        
                        annotated_variants.append(annotated_variant)
            
            # Clean up temporary files
            try:
                os.unlink(temp_in_path)
                os.unlink(temp_out_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary files: {e}")
            
            # If we didn't get annotations for all variants, fill in the missing ones
            if len(annotated_variants) < len(variants):
                logger.warning(f"Only annotated {len(annotated_variants)} out of {len(variants)} variants")
                
                # Create a set of annotated variant positions
                annotated_positions = {f"{v.chrom}:{v.pos}_{v.ref}_{v.alt}" for v in annotated_variants}
                
                # Add unannotated variants
                for v in variants:
                    key = f"{v.chrom}:{v.pos}_{v.ref}_{v.alt}"
                    if key not in annotated_positions:
                        # Create a basic annotated variant
                        gene_symbol = None
                        if hasattr(v, 'info') and "GENE" in v.info:
                            gene_symbol = v.info["GENE"]
                        
                        annotated_variant = AnnotatedVariant(
                            chrom=v.chrom,
                            pos=v.pos,
                            ref=v.ref,
                            alt=v.alt,
                            variant_id=v.id,
                            gene_symbol=gene_symbol,
                            info=v.info if hasattr(v, 'info') else {}
                        )
                        
                        annotated_variants.append(annotated_variant)
            
            return annotated_variants
            
        except Exception as e:
            logger.error(f"Error during file-based SnpEff annotation: {e}")
            
            # Create basic annotated variants without annotation
            return [
                AnnotatedVariant(
                    chrom=v.chrom,
                    pos=v.pos,
                    ref=v.ref,
                    alt=v.alt,
                    variant_id=v.id,
                    gene_symbol=v.info.get("GENE") if hasattr(v, 'info') else None,
                    info=v.info if hasattr(v, 'info') else {}
                ) for v in variants
            ]

class VEPAnnotator(BaseAnnotator):
    """Annotator using Ensembl Variant Effect Predictor (VEP)."""
    
    # VEP REST API endpoint - open access, no API key required
    VEP_API_ENDPOINT = "https://rest.ensembl.org/vep/human/region"
    
    def __init__(self, use_local: bool = False, local_path: Optional[str] = None):
        self.use_local = use_local
        self.local_path = local_path
        
        if use_local and not local_path:
            # Try to find VEP in PATH
            try:
                result = subprocess.run(["which", "vep"], capture_output=True, text=True)
                if result.returncode == 0:
                    self.local_path = result.stdout.strip()
                    logger.info(f"Found local VEP installation at {self.local_path}")
                else:
                    logger.warning("Local VEP requested but not found in PATH")
            except Exception as e:
                logger.error(f"Error finding local VEP: {e}")
    
    def annotate(self, variants: List[Variant]) -> List[AnnotatedVariant]:
        logger.info(f"Annotating {len(variants)} variants using {'local' if self.use_local else 'REST API'} VEP")
        
        if self.use_local and self.local_path:
            return self._annotate_local(variants)
        else:
            return self._annotate_api(variants)
    
    def _annotate_api(self, variants: List[Variant]) -> List[AnnotatedVariant]:
        annotated_variants = []
        
        # Process variants in batches to avoid overwhelming the API
        batch_size = 10  # Smaller batch size to avoid timeouts
        for i in range(0, len(variants), batch_size):
            batch = variants[i:i+batch_size]
            logger.debug(f"Processing batch of {len(batch)} variants (batch {i//batch_size + 1})")
            
            try:
                # Process each variant individually
                for variant in batch:
                    try:
                        # Format the variant for VEP REST API
                        region, allele = self._format_variant_for_vep(variant)
                        
                        if not region or not allele:
                            logger.warning(f"Could not format variant {variant} for VEP")
                            continue
                        
                        # Set up headers
                        headers = {
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        }
                        
                        # Make the API request
                        url = f"{self.VEP_API_ENDPOINT}/{region}/{allele}"
                        logger.debug(f"Requesting VEP annotation for {url}")
                        
                        with httpx.Client(timeout=60.0) as client:
                            response = client.get(url, headers=headers)
                        
                        response.raise_for_status()
                        results = response.json()
                        
                        # VEP returns a list of results, we need the first one
                        if results and len(results) > 0:
                            result = results[0]
                            annotated = self._process_vep_result(variant, result)
                            annotated_variants.append(annotated)
                            
                    except httpx.HTTPStatusError as e:
                        logger.error(f"HTTP error during VEP annotation for {variant}: {e.response.status_code} {e.response.text}")
                        # Continue with other variants
                        continue
                        
                    except Exception as e:
                        logger.error(f"Error during VEP annotation for {variant}: {e}")
                        # Continue with other variants
                        continue
                
            except Exception as e:
                logger.error(f"Error during VEP annotation batch: {e}")
                # Continue with other batches
                continue
        
        logger.info(f"Successfully annotated {len(annotated_variants)} variants")
        return annotated_variants
    
    def _annotate_local(self, variants: List[Variant]) -> List[AnnotatedVariant]:
        annotated_variants = []
        
        try:
            # Create a temporary input file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.vcf') as temp_in:
                temp_in_path = temp_in.name
                
                # Write variants to the temporary file
                temp_in.write("##fileformat=VCFv4.2\n")
                temp_in.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
                
                for v in variants:
                    temp_in.write(f"{v.chrom}\t{v.pos}\t{v.id}\t{v.ref}\t{v.alt}\t{v.qual}\t{v.filter}\t.\n")
            
            # Create a temporary output file
            temp_out_path = temp_in_path + ".vep.json"
            
            # Run VEP
            cmd = [
                self.local_path,
                "-i", temp_in_path,
                "-o", temp_out_path,
                "--species", "homo_sapiens",
                "--format", "vcf",
                "--json",
                "--symbol",
                "--canonical",
                "--protein",
                "--hgvs",
                "--no_stats",
                "--cache"
            ]
            
            logger.debug(f"Running VEP command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"VEP execution failed: {result.stderr}")
                raise RuntimeError(f"VEP execution failed: {result.stderr}")
            
            # Parse the VEP output
            with open(temp_out_path, 'r') as f:
                vep_results = json.load(f)
            
            # Process the results
            variant_dict = {f"{v.chrom}:{v.pos}_{v.ref}_{v.alt}": v for v in variants}
            
            for result in vep_results:
                variant_key = f"{result['chr']}:{result['start']}_{result['allele_string'].split('/')[0]}_{result['allele_string'].split('/')[1]}"
                if variant_key in variant_dict:
                    variant = variant_dict[variant_key]
                    annotated = self._process_vep_result(variant, result)
                    annotated_variants.append(annotated)
            
            # Clean up temporary files
            os.unlink(temp_in_path)
            if os.path.exists(temp_out_path):
                os.unlink(temp_out_path)
                
        except Exception as e:
            logger.error(f"Error during local VEP annotation: {e}")
            raise
        
        logger.info(f"Successfully annotated {len(annotated_variants)} variants using local VEP")
        return annotated_variants
    
    def _format_variant_for_vep(self, variant: Variant) -> tuple:
        try:
            # Ensure chromosome format is correct (remove 'chr' prefix if present)
            chrom = variant.chrom
            if chrom.startswith('chr'):
                chrom = chrom[3:]
            
            # For SNVs, the format is simple
            if len(variant.ref) == 1 and len(variant.alt) == 1:
                # Format: chromosome:position:allele
                region = f"{chrom}:{variant.pos}"
                allele = variant.alt
                return region, allele
            
            # For insertions/deletions, need to use the specific format
            elif len(variant.ref) > len(variant.alt):  # Deletion
                # Format: chromosome:start-end:allele
                region = f"{chrom}:{variant.pos}-{variant.pos + len(variant.ref) - 1}"
                allele = variant.alt
                return region, allele
            
            elif len(variant.ref) < len(variant.alt):  # Insertion
                # Format: chromosome:position-position:allele
                region = f"{chrom}:{variant.pos}-{variant.pos}"
                allele = variant.alt
                return region, allele
            
            # Other structural variants
            else:
                logger.warning(f"Unsupported variant type: {variant}")
                return None, None
            
        except Exception as e:
            logger.warning(f"Could not format variant {variant} for VEP: {e}")
            return None, None
    
    def _process_vep_result(self, variant: Variant, vep_result: Dict[str, Any]) -> AnnotatedVariant:
        # Initialize with default values
        gene_id = None
        gene_symbol = None
        consequence = None
        impact = None
        amino_acid_change = None
        protein_position = None
        rsid = variant.id if variant.id.startswith("rs") else None
        
        # Extract transcript consequences
        if "transcript_consequences" in vep_result:
            # Sort by canonical status and impact severity
            transcripts = sorted(
                vep_result["transcript_consequences"],
                key=lambda x: (x.get("canonical", 0), self._impact_priority(x.get("impact", ""))),
                reverse=True
            )
            
            if transcripts:
                # Take the most severe canonical transcript
                transcript = transcripts[0]
                gene_id = transcript.get("gene_id")
                gene_symbol = transcript.get("gene_symbol")
                consequence = transcript.get("consequence_terms", [""])[0]
                impact = transcript.get("impact")
                amino_acid_change = transcript.get("amino_acids")
                protein_position = transcript.get("protein_start")
        
        # Extract rsID if available
        if "colocated_variants" in vep_result:
            for cv in vep_result["colocated_variants"]:
                if "id" in cv and cv["id"].startswith("rs"):
                    rsid = cv["id"]
                    break
        
        return AnnotatedVariant(
            chrom=variant.chrom,
            pos=variant.pos,
            ref=variant.ref,
            alt=variant.alt,
            gene_symbol=gene_symbol,
            variant_id=variant.id,
            annotations=[{"gene_id": gene_id, "gene_symbol": gene_symbol, "consequence": consequence, "impact": impact}],
            info={"amino_acid_change": amino_acid_change, "protein_position": protein_position}
        )
    
    def _impact_priority(self, impact: str) -> int:
        impact_map = {
            "HIGH": 4,
            "MODERATE": 3,
            "LOW": 2,
            "MODIFIER": 1
        }
        return impact_map.get(impact.upper(), 0) 
