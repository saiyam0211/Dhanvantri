#!/usr/bin/env python3

import argparse
import logging
import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional
import json
import time

# Use SimpleVCFParser instead of VCFParser
from simple_vcf_parser import SimpleVCFParser
from annotator import SnpEffAnnotator, AnnotatedVariant
from drug_mapper import DrugMapper
from personalized_analyzer import PersonalizedAnalyzer
from personalized_report_generator import PersonalizedReportGenerator
import batch_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def is_vcf_pre_annotated(vcf_path: str) -> bool:
    try:
        with open(vcf_path, 'r') as f:
            for line in f:
                if line.startswith('##'):
                    # Check for common annotation headers
                    if any(keyword in line.upper() for keyword in ['SNPEFF', 'VEP', 'ANN=', 'CSQ=', 'EFFECT']):
                        logger.info(f"🏷️ Detected pre-annotated VCF (found annotation header: {line.strip()[:100]}...)")
                        return True
                elif line.startswith('#CHROM'):
                    # Header line found, stop looking
                    break
                elif not line.startswith('#'):
                    # Check first few data lines for annotation fields
                    parts = line.strip().split('\t')
                    if len(parts) >= 8:
                        info_field = parts[7]
                        if any(keyword in info_field.upper() for keyword in ['ANN=', 'CSQ=', 'EFF=', 'GENE=']):
                            logger.info(f"🏷️ Detected pre-annotated VCF (found annotation in INFO field)")
                            return True
                    # Only check first few data lines
                    break
        
        # Also check filename for annotation indicators
        filename = Path(vcf_path).name.lower()
        if any(keyword in filename for keyword in ['.anno.', '.annotated.', '.vep.', '.snpeff.']):
            logger.info(f"🏷️ Detected pre-annotated VCF based on filename: {filename}")
            return True
            
        return False
    except Exception as e:
        logger.warning(f"Could not check VCF annotation status: {e}")
        return False

def convert_variants_to_annotated(variants: List, vcf_path: str) -> List[AnnotatedVariant]:
    annotated_variants = []
    
    for variant in variants:
        # Extract gene information from INFO field if available
        gene_symbol = None
        annotations = []
        
        if hasattr(variant, 'info') and variant.info:
            # Look for gene information in various annotation formats
            info = variant.info
            
            # SnpEff format
            if 'ANN' in info:
                ann_data = info['ANN']
                if isinstance(ann_data, list):
                    ann_data = ann_data[0]  # Take first annotation
                if isinstance(ann_data, str):
                    ann_parts = ann_data.split('|')
                    if len(ann_parts) > 3:
                        gene_symbol = ann_parts[3]  # Gene name is typically at index 3
                        annotations.append({
                            'source': 'SnpEff',
                            'effect': ann_parts[1] if len(ann_parts) > 1 else 'Unknown',
                            'gene': gene_symbol
                        })
            
            # VEP format
            elif 'CSQ' in info:
                csq_data = info['CSQ']
                if isinstance(csq_data, list):
                    csq_data = csq_data[0]
                if isinstance(csq_data, str):
                    csq_parts = csq_data.split('|')
                    if len(csq_parts) > 3:
                        gene_symbol = csq_parts[3]  # Gene symbol location may vary
                        annotations.append({
                            'source': 'VEP',
                            'consequence': csq_parts[1] if len(csq_parts) > 1 else 'Unknown',
                            'gene': gene_symbol
                        })
            
            # Generic gene field
            elif 'GENE' in info:
                gene_symbol = info['GENE']
                if isinstance(gene_symbol, list):
                    gene_symbol = gene_symbol[0]
                annotations.append({
                    'source': 'Generic',
                    'gene': gene_symbol
                })
        
        # Create AnnotatedVariant object
        annotated_variant = AnnotatedVariant(
            chrom=variant.chrom,
            pos=variant.pos,
            ref=variant.ref,
            alt=variant.alt,
            variant_id=getattr(variant, 'id', None),
            gene_symbol=gene_symbol,
            annotations=annotations,
            info=getattr(variant, 'info', {})
        )
        
        annotated_variants.append(annotated_variant)
    
    return annotated_variants

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="🧬 Personalized Pharmacogenomics Analysis System with AI Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --vcf patient.vcf --drugs "Warfarin,Simvastatin" --output report.html
  python main.py --vcf patient.vcf --drugs "Omeprazole" --patient-id "P001" --verbose
  python main.py --vcf patient.vcf --drugs "Tamoxifen,Haloperidol" --verbose
  python main.py --vcf patient.vcf --drugs "Metformin" --no-cohere --verbose
  python main.py --vcf patient.vcf --drugs "Paracetamol" --no-cohere

Pipeline Configurations:
  Full AI:          Database → Cohere → Report (default)
  Database Only:    Database → Report (--no-cohere)
        """
    )
    
    parser.add_argument(
        '--vcf', 
        required=True, 
        help='Path to the annotated VCF file'
    )
    
    parser.add_argument(
        '--drugs', 
        required=True, 
        help='Comma-separated list of drugs to analyze (e.g., "Warfarin,Simvastatin")'
    )
    
    parser.add_argument(
        '--output', 
        default='personalized_report.html',
        help='Output HTML report filename (default: personalized_report.html)'
    )
    
    parser.add_argument(
        '--patient-id', 
        help='Patient identifier for the report'
    )
    
    parser.add_argument(
        '--data-dir-2', 
        default='data_2',
        help='Path to additional data directory (default: data_2)'
    )
    
    parser.add_argument(
        '--no-cohere', 
        action='store_true',
        help='Disable Cohere AI analysis and use database only'
    )
    
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()

def load_api_keys(api_keys_file: Optional[str]) -> dict:
    """Load API keys from JSON file."""
    if not api_keys_file:
        # Try to load from default location
        default_path = Path("api_keys.json")
        if default_path.exists():
            api_keys_file = str(default_path)
        else:
            logger.warning("No API keys file provided. Some features may be limited.")
            return {}
    
    try:
        with open(api_keys_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load API keys: {e}")
        return {}

def main():
    """Main function to run the personalized pharmacogenomics analysis."""
    args = parse_arguments()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('pharmacogenomics.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Handle Cohere settings
    use_cohere = not args.no_cohere
    if args.no_cohere:
        logger.info("🚫 Cohere AI disabled via --no-cohere flag")
    else:
        logger.info("🎯 Cohere AI enabled for final analysis")
    
    # Validate pipeline configuration
    if args.no_cohere:
        logger.warning("⚠️ Cohere AI disabled - analysis will use database sources only")
    else:
        logger.info("🔄 Pipeline: Database → Cohere → Report (full AI)")
    
    start_time = time.time()
    
    try:
        logger.info("🚀 Starting AI Pharmacogenomics Analysis Pipeline")
        logger.info("="*70)
        
        # Step 1: Parse and validate VCF file
        logger.info("📋 Step 1: Parsing VCF file...")
        vcf_path = Path(args.vcf)
        if not vcf_path.exists():
            logger.error(f"❌ VCF file not found: {vcf_path}")
            return
        
        # Step 2: Parse and annotate variants
        logger.info("🏷️ Step 2: Parsing and annotating genetic variants...")
        
        # Parse VCF file first
        vcf_parser = SimpleVCFParser()
        variants = vcf_parser.parse_vcf(str(vcf_path))
        logger.info(f"📊 Parsed {len(variants)} variants from VCF")
        
        # Check if VCF is already annotated
        is_pre_annotated = is_vcf_pre_annotated(str(vcf_path))
        
        if is_pre_annotated:
            logger.info("✅ VCF is pre-annotated, skipping SnpEff annotation step")
            annotated_variants = convert_variants_to_annotated(variants, str(vcf_path))
        else:
            logger.info("🔧 VCF is not annotated, running SnpEff annotation...")
            # Annotate variants using SnpEff
            annotator = SnpEffAnnotator()
            annotated_variants = annotator.annotate(variants)
        
        if not annotated_variants:
            logger.error("❌ No variants found or annotation failed")
            return
        
        logger.info(f"✅ Successfully processed {len(annotated_variants)} variants")
        
        # Step 3: Initialize drug mapper with data directories
        logger.info("🗃️ Step 3: Initializing drug database mapper...")
        drug_mapper = DrugMapper(
            data_dir="data",
            data_dir_2=args.data_dir_2
        )
        
        # Step 4: Parse drug list
        drugs = [drug.strip() for drug in args.drugs.split(',') if drug.strip()]
        logger.info(f"💊 Analyzing drugs: {', '.join(drugs)}")
        
        # Step 5: Initialize personalized analyzer with AI pipeline
        logger.info("🧠 Step 5: Initializing AI Analysis Pipeline...")
        logger.info(f"   📚 Database sources: PharmGKB, CPIC, Additional Data")
        if use_cohere:
            logger.info(f"   🎯 Final AI: Cohere")
        else:
            logger.info(f"   🚫 Cohere AI: Disabled")
        
        analyzer = PersonalizedAnalyzer(
            drug_mapper, 
            use_cohere=use_cohere
        )
        
        # Step 6: Generate personalized reports
        logger.info("🔬 Step 6: Generating personalized drug reports...")
        reports = analyzer.generate_personalized_reports(drugs, annotated_variants)
        
        if not reports:
            logger.error("❌ No reports generated")
            return
        
        # Step 7: Generate HTML report
        logger.info("📄 Step 7: Creating comprehensive HTML report...")
        report_generator = PersonalizedReportGenerator()
        
        output_path = Path(args.output)
        html_path = report_generator.generate_comprehensive_report(
            reports, 
            patient_id=args.patient_id or "Unknown",
            output_path=output_path
        )
        
        # Step 8: Report saved automatically by generate_comprehensive_report
        
        # Final summary
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info("="*70)
        logger.info("🎉 AI ANALYSIS COMPLETED SUCCESSFULLY!")
        logger.info("="*70)
        logger.info(f"📊 Report saved: {output_path.absolute()}")
        logger.info(f"📈 File size: {output_path.stat().st_size / 1024:.1f} KB")
        logger.info(f"⏱️ Processing time: {processing_time:.1f} seconds")
        logger.info(f"💊 Drugs analyzed: {len(reports)}")
        logger.info(f"🧬 Variants processed: {len(annotated_variants)}")
        
        # Pipeline summary
        logger.info("\n🔄 AI Pipeline Summary:")
        for drug_name, report in reports.items():
            ai_sources = len([s for s in report.data_sources if 'AI' in s])
            db_sources = len([s for s in report.data_sources if s not in ['Cohere AI']])
            confidence = report.confidence_level
            
            logger.info(f"   💊 {drug_name}:")
            logger.info(f"      📚 Database sources: {db_sources}")
            logger.info(f"      🤖 AI analysis layers: {ai_sources}")
            logger.info(f"      🎯 Confidence: {confidence}")
        
        # Key findings summary
        high_confidence_drugs = [name for name, report in reports.items() if report.confidence_level == 'HIGH']
        if high_confidence_drugs:
            logger.info(f"\n⭐ High confidence analysis: {', '.join(high_confidence_drugs)}")
        
        logger.info("\n📋 Key Recommendations:")
        logger.info("   • Review genetic impact assessments for each drug")
        logger.info("   • Follow monitoring recommendations closely")
        logger.info("   • Consider alternative medications where suggested")
        
        logger.info("\n⚠️ Medical Disclaimer:")
        logger.info("   This analysis is for research purposes only.")
        logger.info("   Always consult healthcare professionals for medical decisions.")
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Analysis interrupted by user")
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        if args.verbose:
            logger.exception("Full error traceback:")
        raise

if __name__ == "__main__":
    main() 
