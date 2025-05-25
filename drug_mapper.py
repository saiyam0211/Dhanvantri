#!/usr/bin/env python3

import logging
import json
import csv
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field

from annotator import AnnotatedVariant

logger = logging.getLogger(__name__)

@dataclass
class DrugGeneInteraction:
    """Represents a drug-gene interaction with comprehensive metadata."""
    drug: str
    gene: str
    phenotype: str
    source: str
    evidence_level: str
    recommendation: str
    literature_refs: List[str] = field(default_factory=list)
    cpic_level: Optional[str] = None
    pharmgkb_level: Optional[str] = None
    last_updated: Optional[str] = None
    guideline_url: Optional[str] = None
    efficacy: Optional[str] = None
    toxicity: Optional[str] = None
    dosing: Optional[str] = None
    confidence: Optional[str] = None
    clinical_annotation_id: Optional[str] = None
    pgx_testing: Optional[str] = None
    flowchart_url: Optional[str] = None
    guideline_id: Optional[str] = None

class DrugMapper:
    """Enhanced drug mapper with comprehensive PharmGKB, CPIC, and additional data integration."""
    
    def __init__(self, data_dir: str = "data", data_dir_2: str = "data_2"):
        self.data_dir = Path(data_dir)
        self.data_dir_2 = Path(data_dir_2)
        
        # Data storage
        self.pharmgkb_data = {}
        self.cpic_data = {}
        self.additional_data = {}
        
        # Optimized lookup tables
        self.drug_gene_lookup = {}
        self.gene_drug_lookup = {}
        self.drug_name_variations = {}
        self.gene_aliases = {}
        
        # API keys
        self.api_keys = self._load_api_keys()
        
        # Initialize data
        self._load_all_data()
        self._build_lookup_tables()
        self._log_data_statistics()
        
        logger.info("Enhanced DrugMapper initialized successfully")

    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from JSON file if available."""
        api_file = Path("api_keys.json")
        if api_file.exists():
            try:
                with open(api_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load API keys: {e}")
        return {}

    def _load_all_data(self) -> None:
        """Load all data sources."""
        logger.info("Loading comprehensive pharmacogenomics datasets...")
        self._load_pharmgkb_data()
        self._load_cpic_data()
        self._load_additional_data()

    def _load_pharmgkb_data(self) -> None:
        """Load comprehensive PharmGKB data with enhanced integration."""
        pharmgkb_dir = self.data_dir / "pharmgkb"
        
        # Define PharmGKB TSV files to load
        pharmgkb_files = {
            'clinical_annotations': 'clinical_annotations.tsv',
            'drug_labels': 'drugLabels.tsv',
            'drug_labels_by_gene': 'drugLabels.byGene.tsv',
            'var_drug_ann': 'var_drug_ann.tsv',
            'var_pheno_ann': 'var_pheno_ann.tsv',
            'clinical_variants': 'clinicalVariants.tsv',
            'relationships': 'relationships.tsv',
            'clinical_allele_definitions': 'clinical_allele_definitions.tsv',
            'clinical_allele_gene_variant_mappings': 'clinical_allele_gene_variant_mappings.tsv',
            'clinical_allele_haplotypes': 'clinical_allele_haplotypes.tsv',
            'clinical_evidence': 'clinical_evidence.tsv',
            'study_parameters': 'study_parameters.tsv',
            'genes': 'genes.tsv',
            'drugs': 'drugs.tsv',
            'variants': 'variants.tsv',
            'var_fa_ann': 'var_fa_ann.tsv',
            'drug_gene_associations': 'drug_gene_associations.tsv',
            'clinical_ann': 'clinical_ann.tsv'
        }
        
        # Load TSV files
        for key, filename in pharmgkb_files.items():
            filepath = pharmgkb_dir / filename
            if filepath.exists():
                try:
                    with open(filepath, 'r', newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f, delimiter='\t')
                        data = list(reader)
                        self.pharmgkb_data[key] = data
                        logger.info(f"Loaded {len(data)} records from {filename}")
                except Exception as e:
                    logger.error(f"Error loading {filename}: {e}")
        
        # Load PharmGKB guideline JSON files
        guideline_files = list(pharmgkb_dir.glob("PA*.json"))
        guidelines = []
        for guideline_file in guideline_files:
            try:
                with open(guideline_file, 'r', encoding='utf-8') as f:
                    guideline_data = json.load(f)
                    guideline_data['file_name'] = guideline_file.name
                    guidelines.append(guideline_data)
            except Exception as e:
                logger.error(f"Error loading guideline {guideline_file.name}: {e}")
        
        if guidelines:
            self.pharmgkb_data['guidelines'] = guidelines
            logger.info(f"Loaded {len(guidelines)} PharmGKB guideline documents")

    def _load_cpic_data(self) -> None:
        """Load comprehensive CPIC data with enhanced integration."""
        cpic_dir = self.data_dir / "cpic"
        
        # Define CPIC JSON files to load
        cpic_files = {
            'drugs': 'cpic_drugs.json',
            'genes': 'cpic_genes.json',
            'pairs': 'cpic_pairs.json',
            'guidelines': 'cpic_guidelines.json',
            'recommendations': 'cpic_recommendations.json',
            'recommendation_view': 'cpic_recommendation_view.json',
            'gene_result_lookup': 'cpic_gene_result_lookup.json'
        }
        
        # Load JSON files
        for key, filename in cpic_files.items():
            filepath = cpic_dir / filename
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.cpic_data[key] = data
                        
                        # Handle different data structures
                        if isinstance(data, list):
                            logger.info(f"Loaded {len(data)} CPIC {key} records")
                        elif isinstance(data, dict):
                            logger.info(f"Loaded CPIC {key} data structure")
                        else:
                            logger.info(f"Loaded CPIC {key} data")
                except Exception as e:
                    logger.error(f"Error loading CPIC {filename}: {e}")

    def _load_additional_data(self) -> None:
        """Load additional data sources from data_2 directory."""
        if not self.data_dir_2.exists():
            logger.info("data_2 directory not found, skipping additional data sources")
            return
            
        additional_files = [
            "drug_gene_relationships.json",
            "gene_definitions.json", 
            "drug_classes.json"
        ]
        
        for filename in additional_files:
            filepath = self.data_dir_2 / filename
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        key = filename.replace('.json', '')
                        self.additional_data[key] = data
                        logger.info(f"Loaded additional data: {filename}")
                except Exception as e:
                    logger.error(f"Error loading {filename}: {e}")

    def _build_lookup_tables(self) -> None:
        """Build optimized lookup tables for fast drug-gene queries."""
        logger.info("Building optimized lookup tables...")
        
        # Build drug name variations lookup
        self._build_drug_variations_lookup()
        
        # Build gene aliases lookup
        self._build_gene_aliases_lookup()
        
        # Build drug-gene interaction lookup from CPIC pairs
        self._build_cpic_drug_gene_lookup()
        
        # Build PharmGKB interaction lookup
        self._build_pharmgkb_lookup()
        
        logger.info(f"Built lookup tables: {len(self.drug_gene_lookup)} drug-gene pairs")

    def _build_drug_variations_lookup(self) -> None:
        """Build comprehensive drug name variations lookup."""
        # Load CPIC drug data
        if 'drugs' in self.cpic_data:
            for drug in self.cpic_data['drugs']:
                drug_name = drug.get('name', '').lower()
                if drug_name:
                    variations = [drug_name]
                    
                    # Add RxNorm name
                    if drug.get('rxnormid'):
                        variations.append(f"rxnorm:{drug['rxnormid']}")
                    
                    # Add DrugBank ID
                    if drug.get('drugbankid'):
                        variations.append(f"drugbank:{drug['drugbankid']}")
                    
                    # Add ATC codes
                    if drug.get('atcid'):
                        for atc in drug['atcid']:
                            variations.append(f"atc:{atc}")
                    
                    # Store all variations pointing to canonical name
                    for var in variations:
                        self.drug_name_variations[var.lower()] = drug_name
        
        # Add common brand/generic mappings
        brand_generic_mappings = {
            'omeprazole': ['prilosec', 'losec'],
            'tamoxifen': ['nolvadex'],
            'warfarin': ['coumadin', 'jantoven'],
            'clopidogrel': ['plavix'],
            'atorvastatin': ['lipitor'],
            'simvastatin': ['zocor'],
            'metoprolol': ['lopressor', 'toprol'],
            'sertraline': ['zoloft'],
            'fluoxetine': ['prozac'],
            'paroxetine': ['paxil'],
            'escitalopram': ['lexapro'],
            'venlafaxine': ['effexor'],
            'duloxetine': ['cymbalta'],
            'amitriptyline': ['elavil'],
            'codeine': ['tylenol #3', 'tylenol with codeine'],
            'tramadol': ['ultram'],
            'oxycodone': ['oxycontin', 'percocet'],
            'hydrocodone': ['vicodin', 'norco'],
            'morphine': ['ms contin'],
            'fentanyl': ['duragesic'],
            'carbamazepine': ['tegretol'],
            'phenytoin': ['dilantin'],
            'valproic acid': ['depakote'],
            'lamotrigine': ['lamictal'],
            'paracetamol': ['acetaminophen', 'tylenol'],
            'metformin': ['glucophage', 'fortamet'],
            'sildenafil': ['viagra', 'revatio']
        }
        
        for generic, brands in brand_generic_mappings.items():
            self.drug_name_variations[generic] = generic
            for brand in brands:
                self.drug_name_variations[brand.lower()] = generic

    def _build_gene_aliases_lookup(self) -> None:
        """Build gene aliases lookup from CPIC and PharmGKB gene data."""
        # Load CPIC gene data
        if 'genes' in self.cpic_data:
            for gene in self.cpic_data['genes']:
                gene_symbol = gene.get('symbol', '').upper()
                if gene_symbol:
                    aliases = [gene_symbol]
                    
                    # Add alternative names
                    if gene.get('name'):
                        aliases.append(gene['name'].upper())
                    
                    # Store all aliases pointing to canonical symbol
                    for alias in aliases:
                        self.gene_aliases[alias] = gene_symbol
        
        # Load PharmGKB gene data
        if 'genes' in self.pharmgkb_data:
            for gene_row in self.pharmgkb_data['genes']:
                symbol = gene_row.get('Symbol', '').upper()
                if symbol:
                    self.gene_aliases[symbol] = symbol
                    
                    # Add alternative names if available
                    alt_names = gene_row.get('Alternate Names', '')
                    if alt_names:
                        for alt_name in alt_names.split(','):
                            self.gene_aliases[alt_name.strip().upper()] = symbol

    def _build_cpic_drug_gene_lookup(self) -> None:
        """Build drug-gene lookup from CPIC pairs with comprehensive metadata."""
        if 'pairs' not in self.cpic_data:
            return
            
        # Create drug ID to name mapping
        drug_id_map = {}
        if 'drugs' in self.cpic_data:
            for drug in self.cpic_data['drugs']:
                drug_id = drug.get('drugid')
                drug_name = drug.get('name', '').lower()
                if drug_id and drug_name:
                    drug_id_map[drug_id] = drug_name
        
        # Process CPIC pairs
        for pair in self.cpic_data['pairs']:
            gene_symbol = pair.get('genesymbol', '').upper()
            drug_id = pair.get('drugid')
            
            if gene_symbol and drug_id:
                drug_name = drug_id_map.get(drug_id, drug_id).lower()
                
                # Create lookup key
                lookup_key = f"{drug_name}|{gene_symbol}"
                
                # Store interaction data
                interaction_data = {
                    'source': 'CPIC',
                    'cpic_level': pair.get('cpiclevel'),
                    'pgkb_ca_level': pair.get('pgkbcalevel'),
                    'pgx_testing': pair.get('pgxtesting'),
                    'guideline_id': pair.get('guidelineid'),
                    'used_for_recommendation': pair.get('usedforrecommendation'),
                    'citations': pair.get('citations', []),
                    'pair_id': pair.get('pairid')
                }
                
                if lookup_key not in self.drug_gene_lookup:
                    self.drug_gene_lookup[lookup_key] = []
                self.drug_gene_lookup[lookup_key].append(interaction_data)
                
                # Also build reverse lookup
                reverse_key = f"{gene_symbol}|{drug_name}"
                if reverse_key not in self.gene_drug_lookup:
                    self.gene_drug_lookup[reverse_key] = []
                self.gene_drug_lookup[reverse_key].append(interaction_data)

    def _build_pharmgkb_lookup(self) -> None:
        """Build PharmGKB interaction lookup tables."""
        # Process clinical annotations
        if 'clinical_annotations' in self.pharmgkb_data:
            for annotation in self.pharmgkb_data['clinical_annotations']:
                drug_list = annotation.get('Drug(s)', '').lower()
                gene = annotation.get('Gene', '').upper()
                
                if drug_list and gene:
                    # Handle multiple drugs in annotation
                    drugs = [d.strip() for d in drug_list.split(',')]
                    
                    for drug in drugs:
                        lookup_key = f"{drug}|{gene}"
                        
                        interaction_data = {
                            'source': 'PharmGKB Clinical Annotations',
                            'pharmgkb_level': annotation.get('Level of Evidence'),
                            'phenotype': annotation.get('Phenotype(s)'),
                            'phenotype_category': annotation.get('Phenotype Category'),
                            'clinical_annotation_id': annotation.get('Clinical Annotation ID'),
                            'pmid_count': annotation.get('PMID Count'),
                            'last_updated': annotation.get('Latest History Date (YYYY-MM-DD)')
                        }
                        
                        if lookup_key not in self.drug_gene_lookup:
                            self.drug_gene_lookup[lookup_key] = []
                        self.drug_gene_lookup[lookup_key].append(interaction_data)

    def _log_data_statistics(self) -> None:
        """Log comprehensive data loading statistics."""
        logger.info("=== Data Loading Statistics ===")
        
        # PharmGKB statistics
        pharmgkb_total = sum(len(data) if isinstance(data, list) else 1 
                           for data in self.pharmgkb_data.values())
        logger.info(f"PharmGKB Data: {pharmgkb_total} total records across {len(self.pharmgkb_data)} file types")
        
        # CPIC statistics
        cpic_total = sum(len(data) if isinstance(data, list) else 1 
                        for data in self.cpic_data.values())
        logger.info(f"CPIC Data: {cpic_total} total records across {len(self.cpic_data)} data types")
        
        # Additional data statistics
        if self.additional_data:
            additional_total = sum(len(data) if isinstance(data, list) else 1 
                                 for data in self.additional_data.values())
            logger.info(f"Additional Data: {additional_total} records from {len(self.additional_data)} sources")
        
        # Lookup table statistics
        logger.info(f"Lookup Tables: {len(self.drug_gene_lookup)} drug-gene pairs, "
                   f"{len(self.drug_name_variations)} drug variations, "
                   f"{len(self.gene_aliases)} gene aliases")
        
        logger.info("=== End Statistics ===")

    def map_drugs_to_genes(self, drugs: List[str], annotated_variants: List[AnnotatedVariant]) -> Dict[str, List[DrugGeneInteraction]]:
        logger.info(f"Mapping {len(drugs)} drugs to genes from {len(annotated_variants)} variants")
        
        # Extract genes from variants
        genes = self._extract_genes(annotated_variants)
        logger.info(f"Extracted {len(genes)} unique genes from variants")
        
        # Map each drug to relevant interactions
        drug_interactions = {}
        for drug in drugs:
            normalized_drug = self._normalize_drug_name(drug)
            interactions = self._get_comprehensive_interactions(normalized_drug, genes)
            
            if interactions:
                drug_interactions[drug] = self._deduplicate_and_sort_interactions(interactions)
                logger.info(f"Found {len(drug_interactions[drug])} interactions for {drug}")
            else:
                # Fallback to AI analysis if no database interactions found
                ai_interactions = self._get_ai_analysis(normalized_drug, genes, annotated_variants)
                if ai_interactions:
                    drug_interactions[drug] = ai_interactions
                    logger.info(f"Generated {len(ai_interactions)} AI interactions for {drug}")
                else:
                    drug_interactions[drug] = []
                    logger.warning(f"No interactions found for {drug}")
        
        return drug_interactions

    def _normalize_drug_name(self, drug_name: str) -> str:
        """Normalize drug name using variations lookup."""
        normalized = drug_name.strip().lower()
        
        # Check if we have a known variation
        if normalized in self.drug_name_variations:
            return self.drug_name_variations[normalized]
        
        # Return as-is if no mapping found
        return normalized

    def _normalize_gene_symbol(self, gene_symbol: str) -> str:
        """Normalize gene symbol using aliases lookup."""
        normalized = gene_symbol.strip().upper()
        
        # Check if we have a known alias
        if normalized in self.gene_aliases:
            return self.gene_aliases[normalized]
        
        # Return as-is if no mapping found
        return normalized

    def _get_comprehensive_interactions(self, drug: str, genes: Set[str]) -> List[DrugGeneInteraction]:
        """Get comprehensive interactions from all database sources."""
        interactions = []
        
        # Search for direct drug-gene matches in lookup tables
        for gene in genes:
            normalized_gene = self._normalize_gene_symbol(gene)
            lookup_key = f"{drug}|{normalized_gene}"
            
            if lookup_key in self.drug_gene_lookup:
                for interaction_data in self.drug_gene_lookup[lookup_key]:
                    if interaction_data['source'] == 'CPIC':
                        interaction = self._create_cpic_interaction(drug, normalized_gene, interaction_data)
                    else:
                        interaction = self._create_pharmgkb_interaction(drug, normalized_gene, interaction_data)
                    
                    if interaction:
                        interactions.append(interaction)
        
        # If no specific interactions found, get all interactions for the drug
        if not interactions:
            interactions = self._get_all_drug_interactions(drug)
        
        return interactions

    def _get_all_drug_interactions(self, drug: str) -> List[DrugGeneInteraction]:
        """Get all available interactions for a drug from all sources."""
        interactions = []
        
        # Search CPIC data
        if 'pairs' in self.cpic_data:
            drug_id_map = {}
            if 'drugs' in self.cpic_data:
                for drug_data in self.cpic_data['drugs']:
                    drug_name = drug_data.get('name', '').lower()
                    if drug_name == drug:
                        drug_id = drug_data.get('drugid')
                        if drug_id:
                            drug_id_map[drug_id] = drug_name
            
            for pair in self.cpic_data['pairs']:
                drug_id = pair.get('drugid')
                if drug_id in drug_id_map:
                    gene_symbol = pair.get('genesymbol', '').upper()
                    if gene_symbol:
                        interaction_data = {
                            'source': 'CPIC',
                            'cpic_level': pair.get('cpiclevel'),
                            'pgkb_ca_level': pair.get('pgkbcalevel'),
                            'pgx_testing': pair.get('pgxtesting'),
                            'guideline_id': pair.get('guidelineid'),
                            'pair_id': pair.get('pairid')
                        }
                        interaction = self._create_cpic_interaction(drug, gene_symbol, interaction_data)
                        if interaction:
                            interactions.append(interaction)
        
        # Search PharmGKB clinical annotations
        if 'clinical_annotations' in self.pharmgkb_data:
            for annotation in self.pharmgkb_data['clinical_annotations']:
                drug_list = annotation.get('Drug(s)', '').lower()
                if drug in drug_list.split(','):
                    gene = annotation.get('Gene', '').upper()
                    if gene:
                        interaction_data = {
                            'source': 'PharmGKB Clinical Annotations',
                            'pharmgkb_level': annotation.get('Level of Evidence'),
                            'phenotype': annotation.get('Phenotype(s)'),
                            'clinical_annotation_id': annotation.get('Clinical Annotation ID')
                        }
                        interaction = self._create_pharmgkb_interaction(drug, gene, interaction_data)
                        if interaction:
                            interactions.append(interaction)
        
        return interactions

    def _create_cpic_interaction(self, drug: str, gene: str, data: Dict[str, Any]) -> DrugGeneInteraction:
        """Create a DrugGeneInteraction from CPIC data."""
        # Get additional drug and gene info
        drug_info = self._get_cpic_drug_info(drug)
        gene_info = self._get_cpic_gene_info(gene)
        
        # Get recommendations
        recommendations = self._get_cpic_recommendations(drug, gene, data.get('guideline_id'))
        
        return DrugGeneInteraction(
            drug=drug.title(),
            gene=gene,
            phenotype=recommendations.get('phenotype', 'Unknown'),
            source='CPIC',
            evidence_level=data.get('cpic_level', 'Unknown'),
            recommendation=recommendations.get('recommendation', 'No specific recommendation available'),
            cpic_level=data.get('cpic_level'),
            pharmgkb_level=data.get('pgkb_ca_level'),
            pgx_testing=data.get('pgx_testing'),
            guideline_id=data.get('guideline_id'),
            guideline_url=f"https://cpicpgx.org/guidelines/guideline-for-{drug.lower()}-and-{gene.lower()}/"
        )

    def _create_pharmgkb_interaction(self, drug: str, gene: str, data: Dict[str, Any]) -> DrugGeneInteraction:
        """Create a DrugGeneInteraction from PharmGKB data."""
        return DrugGeneInteraction(
            drug=drug.title(),
            gene=gene,
            phenotype=data.get('phenotype', 'Unknown'),
            source='PharmGKB',
            evidence_level=data.get('pharmgkb_level', 'Unknown'),
            recommendation=f"Clinical annotation available. See PharmGKB for details.",
            pharmgkb_level=data.get('pharmgkb_level'),
            clinical_annotation_id=data.get('clinical_annotation_id'),
            last_updated=data.get('last_updated')
        )

    def _get_cpic_drug_info(self, drug_name: str) -> Dict[str, Any]:
        """Get CPIC drug information."""
        if 'drugs' in self.cpic_data:
            for drug in self.cpic_data['drugs']:
                if drug.get('name', '').lower() == drug_name.lower():
                    return drug
        return {}

    def _get_cpic_gene_info(self, gene_symbol: str) -> Dict[str, Any]:
        """Get CPIC gene information."""
        if 'genes' in self.cpic_data:
            for gene in self.cpic_data['genes']:
                if gene.get('symbol', '').upper() == gene_symbol.upper():
                    return gene
        return {}

    def _get_cpic_recommendations(self, drug: str, gene: str, guideline_id: Optional[str]) -> Dict[str, str]:
        """Get CPIC recommendations for drug-gene pair."""
        recommendations = {
            'phenotype': 'Unknown',
            'recommendation': 'No specific recommendation available'
        }
        
        if 'recommendations' in self.cpic_data and guideline_id:
            for rec in self.cpic_data['recommendations']:
                if rec.get('guidelineid') == guideline_id:
                    recommendations['phenotype'] = rec.get('phenotype', 'Unknown')
                    recommendations['recommendation'] = rec.get('recommendation', 'No specific recommendation available')
                    break
        
        return recommendations

    def _extract_genes(self, annotated_variants: List[AnnotatedVariant]) -> Set[str]:
        genes = set()
        for variant in annotated_variants:
            if variant.gene_symbol:
                # Normalize gene symbol
                normalized_gene = self._normalize_gene_symbol(variant.gene_symbol)
                genes.add(normalized_gene)
        
        logger.info(f"Extracted {len(genes)} unique genes: {', '.join(sorted(genes))}")
        return genes

    def _get_ai_analysis(self, drug: str, genes: Set[str], variants: List[AnnotatedVariant]) -> List[DrugGeneInteraction]:
        """Get AI-powered analysis when database sources are insufficient."""
        try:
            return self._get_cohere_analysis(drug, genes, variants)
        except Exception as e:
            logger.error(f"AI analysis failed for {drug}: {e}")
            return []

    def _estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens in a text string."""
        # Rough estimation: 1 token ≈ 4 characters for English text
        return len(text) // 4

    def _get_cohere_analysis(self, drug: str, genes: Set[str], variants: List[AnnotatedVariant]) -> List[DrugGeneInteraction]:
        """Generate interactions using Cohere AI."""
        if 'cohere_api_key' not in self.api_keys:
            logger.warning("Cohere API key not available for AI analysis")
            return []
        
        try:
            import cohere
            
            co = cohere.ClientV2(self.api_keys['cohere_api_key'])
            
            # Prepare variant information (limit to prevent token overflow)
            variant_info = []
            max_variants = 50  # Limit total variants processed
            
            for variant in variants[:max_variants]:
                if variant.gene_symbol in genes:
                    variant_info.append({
                        'gene': variant.gene_symbol,
                        'rsid': getattr(variant, 'variant_id', f'{variant.chrom}:{variant.pos}'),
                        'consequence': getattr(variant, 'consequence', 'Unknown'),
                        'impact': getattr(variant, 'impact', 'Unknown'),
                        'amino_acid_change': getattr(variant, 'amino_acid_change', 'Unknown')
                    })
            
            # Create prompt with token limiting
            prompt = self._create_pharmacogenomic_prompt(drug, genes, variant_info)
            
            # Estimate tokens and warn if approaching limit
            estimated_tokens = self._estimate_tokens(prompt)
            max_safe_tokens = 100000  # Stay well below the 132,096 limit
            
            if estimated_tokens > max_safe_tokens:
                logger.warning(f"Prompt too large ({estimated_tokens} estimated tokens), truncating...")
                # Further reduce the prompt size
                limited_genes = list(genes)[:5]
                limited_variants = variant_info[:10]
                prompt = self._create_pharmacogenomic_prompt(drug, set(limited_genes), limited_variants)
                estimated_tokens = self._estimate_tokens(prompt)
                logger.info(f"Reduced prompt to {estimated_tokens} estimated tokens")
            
            # Get AI response with reduced max_tokens to leave room for input
            response = co.chat(
                model='command-r-plus-08-2024',
                messages=[{"role": "user", "content": prompt}],
                max_tokens=min(1000, max_safe_tokens - estimated_tokens),
                temperature=0.3
            )
            
            # Parse response
            return self._parse_ai_response(drug, response.message.content[0].text, genes, "Cohere AI")
            
        except Exception as e:
            logger.error(f"Cohere analysis failed: {e}")
            return []

    def _create_pharmacogenomic_prompt(self, drug: str, genes: Set[str], variant_info: List[Dict]) -> str:
        """Create a comprehensive pharmacogenomic analysis prompt with token limiting."""
        
        # Limit the number of genes and variants to prevent token overflow
        max_genes = 10
        max_variants_per_gene = 3
        
        # Limit genes to most relevant ones
        limited_genes = list(genes)[:max_genes]
        
        # Group variants by gene and limit per gene
        gene_variants = {}
        for variant in variant_info:
            gene = variant['gene']
            if gene in limited_genes:
                if gene not in gene_variants:
                    gene_variants[gene] = []
                if len(gene_variants[gene]) < max_variants_per_gene:
                    gene_variants[gene].append(variant)
        
        prompt = f"""Analyze pharmacogenomic interactions between {drug} and these genes: {', '.join(limited_genes[:5])}.

Key genetic variants:"""
        
        # Add only the most important variants
        variant_count = 0
        max_total_variants = 15  # Limit total variants to control prompt size
        
        for gene in limited_genes:
            if gene in gene_variants and variant_count < max_total_variants:
                for variant in gene_variants[gene]:
                    if variant_count >= max_total_variants:
                        break
                    prompt += f"\n- {variant['gene']}: {variant['rsid']} ({variant['consequence']})"
                    variant_count += 1
        
        prompt += f"""

Provide concise analysis for each relevant gene:
1. Gene name and predicted phenotype
2. Clinical recommendation for {drug}
3. Risk level (High/Medium/Low)

Focus on actionable clinical guidance."""
        
        return prompt

    def _parse_ai_response(self, drug: str, response: str, genes: Set[str], ai_source: str) -> List[DrugGeneInteraction]:
        """Parse AI response into DrugGeneInteraction objects."""
        interactions = []
        
        # Simple parsing logic - can be enhanced
        lines = response.strip().split('\n')
        current_gene = None
        current_phenotype = None
        current_recommendation = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for gene mentions
            for gene in genes:
                if gene.upper() in line.upper():
                    current_gene = gene
                    break
            
            # Look for phenotype indicators
            phenotype_indicators = ['metabolizer', 'responder', 'sensitivity', 'resistance']
            for indicator in phenotype_indicators:
                if indicator.lower() in line.lower():
                    current_phenotype = line
                    break
            
            # Look for recommendations
            if any(word in line.lower() for word in ['recommend', 'suggest', 'consider', 'avoid', 'reduce', 'increase']):
                current_recommendation = line
        
        # Create interaction if we have sufficient information
        if current_gene:
            interaction = DrugGeneInteraction(
                drug=drug.title(),
                gene=current_gene,
                phenotype=current_phenotype or "Unknown phenotype",
                source=ai_source,
                evidence_level="AI-generated",
                recommendation=current_recommendation or f"Consider genetic testing for {current_gene} variants before {drug} therapy.",
                confidence="Medium"
            )
            interactions.append(interaction)
        
        return interactions

    def _deduplicate_and_sort_interactions(self, interactions: List[DrugGeneInteraction]) -> List[DrugGeneInteraction]:
        """Remove duplicates and sort interactions by evidence quality."""
        # Remove exact duplicates
        unique_interactions = []
        seen = set()
        
        for interaction in interactions:
            key = (interaction.drug, interaction.gene, interaction.source)
            if key not in seen:
                unique_interactions.append(interaction)
                seen.add(key)
        
        # Sort by evidence quality
        def evidence_priority(interaction):
            # CPIC A-level evidence gets highest priority
            if interaction.cpic_level == 'A':
                return 1
            # PharmGKB 1A/1B evidence
            elif interaction.pharmgkb_level in ['1A', '1B']:
                return 2
            # CPIC B-level evidence
            elif interaction.cpic_level == 'B':
                return 3
            # PharmGKB 2A/2B evidence
            elif interaction.pharmgkb_level in ['2A', '2B']:
                return 4
            # CPIC C-level evidence
            elif interaction.cpic_level == 'C':
                return 5
            # PharmGKB 3/4 evidence
            elif interaction.pharmgkb_level in ['3', '4']:
                return 6
            # AI-generated evidence
            elif interaction.source == 'Cohere AI':
                return 7
            else:
                return 8
        
        return sorted(unique_interactions, key=evidence_priority)

    def get_enhanced_drug_interactions(self, drug_name: str) -> List[DrugGeneInteraction]:
        """Get enhanced drug interactions using comprehensive lookup."""
        return self._get_all_drug_interactions(self._normalize_drug_name(drug_name))

    def get_drug_statistics(self) -> Dict[str, int]:
        """Get statistics about loaded drug data."""
        stats = {
            'pharmgkb_files': len(self.pharmgkb_data),
            'cpic_files': len(self.cpic_data),
            'additional_files': len(self.additional_data),
            'drug_gene_pairs': len(self.drug_gene_lookup),
            'drug_variations': len(self.drug_name_variations),
            'gene_aliases': len(self.gene_aliases)
        }
        
        # Count total records
        total_pharmgkb = sum(len(data) if isinstance(data, list) else 1 
                           for data in self.pharmgkb_data.values())
        total_cpic = sum(len(data) if isinstance(data, list) else 1 
                        for data in self.cpic_data.values())
        
        stats['total_pharmgkb_records'] = total_pharmgkb
        stats['total_cpic_records'] = total_cpic
        
        return stats 
