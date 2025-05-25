#!/usr/bin/env python3

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Variant:
    """Class representing a genetic variant."""
    chrom: str
    pos: int
    id: str
    ref: str
    alt: str
    qual: float
    filter: str
    info: Dict[str, Any]
    genotype: Optional[str] = None
    
    def __str__(self) -> str:
        return f"{self.chrom}:{self.pos} {self.ref}>{self.alt} ({self.id})"

class SimpleVCFParser:
    """Simple parser for VCF files using Python's standard library."""
    
    def __init__(self, vcf_path: Optional[Path] = None):
        self.vcf_path = vcf_path
        if vcf_path:
            logger.debug(f"Initialized Simple VCF parser for {vcf_path}")
    
    def parse_vcf(self, vcf_path: str, limit: Optional[int] = None) -> List[Variant]:
        self.vcf_path = Path(vcf_path)
        return self.parse(limit=limit)
    
    def parse(self, limit: Optional[int] = None) -> List[Variant]:
        if not self.vcf_path:
            raise ValueError("VCF path not specified")
            
        logger.info(f"Parsing VCF file: {self.vcf_path}")
        variants = []
        
        try:
            with open(self.vcf_path, 'r') as vcf_file:
                # Skip header lines
                sample_ids = []
                for line in vcf_file:
                    if line.startswith('##'):
                        continue
                    elif line.startswith('#CHROM'):
                        # Extract sample IDs from header line
                        header_fields = line.strip().split('\t')
                        if len(header_fields) > 9:
                            sample_ids = header_fields[9:]
                        break
                
                # Parse variant lines
                count = 0
                for line in vcf_file:
                    if limit is not None and count >= limit:
                        break
                    
                    if line.strip():
                        variant = self._parse_variant_line(line, sample_ids)
                        if variant:
                            variants.append(variant)
                            count += 1
                            if count % 10000 == 0:
                                logger.debug(f"Processed {count} variants so far")
        
        except Exception as e:
            logger.error(f"Error parsing VCF file: {e}")
            raise
        
        if limit is not None:
            logger.info(f"Extracted {len(variants)} variants from VCF file (limited to {limit})")
        else:
            logger.info(f"Extracted {len(variants)} variants from VCF file")
        return variants
    
    def _parse_variant_line(self, line: str, sample_ids: List[str]) -> Optional[Variant]:
        try:
            fields = line.strip().split('\t')
            
            if len(fields) < 8:
                logger.warning(f"Skipping malformed line: {line.strip()}")
                return None
            
            # Parse basic fields
            chrom = fields[0]
            pos = int(fields[1])
            id_field = fields[2]
            ref = fields[3]
            alt = fields[4]
            qual = float(fields[5]) if fields[5] != '.' else 0.0
            filter_field = fields[6]
            
            # Parse INFO field
            info = {}
            if fields[7] != '.':
                for item in fields[7].split(';'):
                    if '=' in item:
                        key, value = item.split('=', 1)
                        info[key] = value
                    else:
                        info[item] = True
            
            # Generate ID if missing
            if id_field == '.':
                id_field = f"{chrom}:{pos}"
            
            # Parse genotype if available
            genotype = None
            if len(fields) > 9 and len(sample_ids) > 0:
                # Simplified genotype parsing - just for demonstration
                format_fields = fields[8].split(':')
                sample_fields = fields[9].split(':')
                
                if 'GT' in format_fields:
                    gt_index = format_fields.index('GT')
                    if gt_index < len(sample_fields):
                        gt = sample_fields[gt_index]
                        
                        # Convert genotype to human-readable format
                        if gt == '0/0':
                            genotype = f"{ref}/{ref}"
                        elif gt == '0/1':
                            genotype = f"{ref}/{alt}"
                        elif gt == '1/1':
                            genotype = f"{alt}/{alt}"
            
            return Variant(
                chrom=chrom,
                pos=pos,
                id=id_field,
                ref=ref,
                alt=alt,
                qual=qual,
                filter=filter_field,
                info=info,
                genotype=genotype
            )
            
        except Exception as e:
            logger.warning(f"Error parsing variant line: {e}")
            return None
    
    def get_sample_ids(self) -> List[str]:
        sample_ids = []
        
        try:
            with open(self.vcf_path, 'r') as vcf_file:
                for line in vcf_file:
                    if line.startswith('#CHROM'):
                        fields = line.strip().split('\t')
                        if len(fields) > 9:
                            sample_ids = fields[9:]
                        break
        except Exception as e:
            logger.error(f"Error getting sample IDs: {e}")
        
        return sample_ids
    
    def parse_line(self, line: str) -> Optional[Variant]:
        # Skip header lines
        if line.startswith('#'):
            return None
        
        # Parse the variant line
        return self._parse_variant_line(line, []) 
