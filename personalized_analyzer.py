#!/usr/bin/env python3

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
import cohere

from annotator import AnnotatedVariant
from drug_mapper import DrugMapper, DrugGeneInteraction

logger = logging.getLogger(__name__)

@dataclass
class PersonalizedDrugReport:
    """Comprehensive personalized drug analysis report."""
    drug_name: str
    patient_genetic_profile: Dict[str, Any]
    efficacy_prediction: str
    risk_assessment: str
    dosage_recommendation: str
    alternative_medications: List[str]
    clinical_considerations: str
    confidence_level: str
    data_sources: List[str]
    genetic_variants_analyzed: List[str]
    pharmacokinetic_impact: str
    pharmacodynamic_impact: str
    contraindications: List[str]
    monitoring_recommendations: str

class PersonalizedAnalyzer:
    
    def __init__(self, drug_mapper: DrugMapper, use_cohere: bool = True):
        self.drug_mapper = drug_mapper
        self.use_cohere = use_cohere
        
        # Initialize Cohere client from API keys only if enabled
        if self.use_cohere:
            try:
                import cohere
                api_keys = drug_mapper.api_keys
                if 'cohere_api_key' in api_keys:
                    self.cohere_client = cohere.ClientV2(api_keys['cohere_api_key'])
                    logger.info("✅ Cohere client initialized successfully")
                else:
                    logger.warning("Cohere API key not found, Cohere analysis will be disabled")
                    self.cohere_client = None
                    self.use_cohere = False
            except ImportError:
                logger.warning("Cohere package not installed, Cohere analysis will be disabled")
                self.cohere_client = None
                self.use_cohere = False
            except Exception as e:
                logger.warning(f"Failed to initialize Cohere client: {e}")
                self.cohere_client = None
                self.use_cohere = False
        else:
            logger.info("🚫 Cohere AI disabled by user")
            self.cohere_client = None
        
    def generate_personalized_reports(
        self, 
        drugs: List[str], 
        annotated_variants: List[AnnotatedVariant]
    ) -> Dict[str, PersonalizedDrugReport]:
        reports = {}
        
        try:
            for drug in drugs:
                logger.info(f"🚀 Starting multi-AI pipeline analysis for {drug}")
                report = self._generate_single_drug_report(drug, annotated_variants)
                reports[drug] = report
                
        except Exception as e:
            logger.error(f"Error in personalized analysis: {e}")
            raise
            
        return reports
    
    def _generate_single_drug_report(
        self, 
        drug: str, 
        annotated_variants: List[AnnotatedVariant]
    ) -> PersonalizedDrugReport:
        logger.info(f"📊 Step 1: Extracting relevant genes for {drug}")
        # Extract relevant genes from variants
        relevant_genes = self._extract_relevant_genes(annotated_variants)
        
        logger.info(f"📚 Step 2: Querying databases for {drug}")
        # Get all available data from PharmGKB and CPIC using the available methods
        database_interactions = self.drug_mapper.map_drugs_to_genes([drug], annotated_variants)
        
        # Extract interactions for this specific drug
        drug_interactions = database_interactions.get(drug, [])
        
        logger.info(f"🧬 Step 3: Creating genetic profile for {drug}")
        # Prepare comprehensive genetic profile
        genetic_profile = self._create_genetic_profile(annotated_variants, relevant_genes)
        
        # Step 4: Final Cohere analysis incorporating all previous steps
        logger.info(f"🎯 Step 4: Running final analysis for {drug}")
        if self.use_cohere and drug_interactions:
            # Enhanced analysis with database data using Cohere
            logger.info(f"🎯 Using Cohere for enhanced analysis of {drug}")
            report = self._generate_enhanced_cohere_report(
                drug, genetic_profile, drug_interactions, annotated_variants
            )
        elif self.use_cohere:
            # AI-only analysis using Cohere if no database data
            logger.info(f"🎯 Using Cohere for AI-only analysis of {drug}")
            report = self._generate_ai_only_report(
                drug, genetic_profile, annotated_variants
            )
        elif drug_interactions:
            # Database-only analysis when AI is disabled
            logger.info(f"📚 Using database-only analysis for {drug} (AI disabled)")
            report = self._generate_database_only_report(
                drug, genetic_profile, drug_interactions
            )
        else:
            # Fallback report when no data sources are available
            logger.warning(f"⚠️ Creating fallback report for {drug} (no data sources available)")
            report = self._create_fallback_report(drug, genetic_profile, [])
        
        logger.info(f"✅ Analysis completed for {drug}")
        return report
    
    def _extract_relevant_genes(self, annotated_variants: List[AnnotatedVariant]) -> Set[str]:
        """Extract all relevant genes from annotated variants."""
        genes = set()
        for variant in annotated_variants:
            if hasattr(variant, 'gene_symbol') and variant.gene_symbol:
                genes.add(variant.gene_symbol)
            if hasattr(variant, 'consequence') and variant.consequence:
                # Extract gene from consequence if available
                for gene in variant.consequence.split(','):
                    if gene.strip():
                        genes.add(gene.strip())
        return genes
    
    def _create_genetic_profile(
        self, 
        annotated_variants: List[AnnotatedVariant], 
        relevant_genes: Set[str]
    ) -> Dict[str, Any]:
        """Create a comprehensive genetic profile for the patient."""
        profile = {
            'total_variants': len(annotated_variants),
            'relevant_genes': list(relevant_genes),
            'gene_variants': {},
            'pharmacokinetic_genes': [],
            'pharmacodynamic_genes': [],
            'variant_frequencies': {},
            'predicted_phenotypes': {}
        }
        
        # Known pharmacokinetic and pharmacodynamic genes
        pk_genes = {'CYP2D6', 'CYP2C19', 'CYP2C9', 'CYP3A4', 'CYP3A5', 'UGT1A1', 'DPYD', 'TPMT'}
        pd_genes = {'HTR2A', 'DRD2', 'COMT', 'BDNF', 'CACNA1C', 'OPRM1'}
        
        for gene in relevant_genes:
            if gene in pk_genes:
                profile['pharmacokinetic_genes'].append(gene)
            if gene in pd_genes:
                profile['pharmacodynamic_genes'].append(gene)
        
        # Group variants by gene
        for variant in annotated_variants:
            if hasattr(variant, 'gene_symbol') and variant.gene_symbol in relevant_genes:
                gene = variant.gene_symbol
                if gene not in profile['gene_variants']:
                    profile['gene_variants'][gene] = []
                
                variant_info = {
                    'position': f"{variant.chrom}:{variant.pos}",
                    'ref': variant.ref,
                    'alt': variant.alt,
                    'consequence': getattr(variant, 'consequence', 'Unknown'),
                    'clinical_significance': getattr(variant, 'clinical_significance', 'Unknown')
                }
                profile['gene_variants'][gene].append(variant_info)
        
        return profile
    
    def _generate_enhanced_cohere_report(
        self,
        drug: str,
        genetic_profile: Dict[str, Any],
        database_interactions: List[DrugGeneInteraction],
        annotated_variants: List[AnnotatedVariant]
    ) -> PersonalizedDrugReport:
        """Generate enhanced report combining database data and Cohere analysis."""
        
        # Extract data sources
        data_sources = list(set([interaction.source for interaction in database_interactions]))
        data_sources.append("Cohere AI")
        
        # Create comprehensive prompt for Cohere analysis
        prompt = self._create_enhanced_cohere_prompt(
            drug, genetic_profile, database_interactions
        )
        
        try:
            # Get final Cohere analysis
            if self.cohere_client:
                response = self.cohere_client.chat(
                    model="command-r-plus-08-2024",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.1,  # Lower temperature for more consistent responses
                    frequency_penalty=0.1,  # Reduce repetition
                    presence_penalty=0.1   # Encourage diverse content
                )
                
                ai_analysis = response.message.content[0].text.strip()
                
                # Parse Cohere response into structured report
                report = self._parse_enhanced_response(
                    drug, ai_analysis, genetic_profile, data_sources
                )
            else:
                logger.warning("Cohere client not available, creating report from database data only")
                report = self._create_fallback_report(drug, genetic_profile, database_interactions)
            
        except Exception as e:
            logger.error(f"Error generating enhanced Cohere report for {drug}: {e}")
            report = self._create_fallback_report(drug, genetic_profile, database_interactions)
        
        return report
    
    def _create_enhanced_cohere_prompt(
        self,
        drug: str,
        genetic_profile: Dict[str, Any],
        database_interactions: List[DrugGeneInteraction]
    ) -> str:
        """Create enhanced prompt incorporating database data."""
        
        prompt = f"""You are a clinical pharmacogenomics expert. Analyze the genetic profile and provide a comprehensive, structured report for {drug}.

PATIENT GENETIC PROFILE:
- Total variants analyzed: {genetic_profile['total_variants']}
- Relevant genes: {', '.join(genetic_profile['relevant_genes'][:10])}
- Pharmacokinetic genes: {', '.join(genetic_profile['pharmacokinetic_genes'])}
- Pharmacodynamic genes: {', '.join(genetic_profile['pharmacodynamic_genes'])}

DATABASE INTERACTIONS (PharmGKB/CPIC):"""
        
        if database_interactions:
            for interaction in database_interactions[:3]:  # Limit to prevent overflow
                prompt += f"\n- {interaction.gene}: {interaction.evidence_level} evidence, {interaction.recommendation}"
        else:
            prompt += "\n- No specific database interactions found"
        
        prompt += f"""

INSTRUCTIONS:
Provide a structured analysis for {drug} using the following EXACT format. Keep each section concise (2-3 sentences max) and clinically relevant:

**EFFICACY_PREDICTION:**
[Provide specific efficacy prediction for {drug} based on genetic profile - 2-3 sentences]

**RISK_ASSESSMENT:**
[Assess specific risks for {drug} based on genetic variants - 2-3 sentences]

**DOSAGE_RECOMMENDATION:**
[Provide specific dosing guidance for {drug} - 2-3 sentences]

**ALTERNATIVE_MEDICATIONS:**
[List 3-4 specific alternative drugs with brief rationale - bullet points]

**CLINICAL_CONSIDERATIONS:**
[Key monitoring points specific to {drug} and this genetic profile - 2-3 sentences]

**CONFIDENCE_LEVEL:**
[HIGH/MEDIUM/LOW with brief justification]

**PHARMACOKINETIC_IMPACT:**
[How genetics affect {drug} absorption, metabolism, elimination - 2-3 sentences]

**PHARMACODYNAMIC_IMPACT:**
[How genetics affect {drug} target interactions and response - 2-3 sentences]

**CONTRAINDICATIONS:**
[Any genetic contraindications for {drug} - bullet points or "None identified"]

**MONITORING_RECOMMENDATIONS:**
[Specific monitoring protocols for {drug} with this genetic profile - 2-3 sentences]

IMPORTANT: 
- Use the exact section headers with ** formatting
- Keep responses concise and drug-specific
- Avoid generic statements
- Focus on actionable clinical insights
- Base recommendations on the specific genetic profile provided"""
        
        return prompt
    
    def _parse_enhanced_response(
        self,
        drug: str,
        ai_response: str,
        genetic_profile: Dict[str, Any],
        data_sources: List[str]
    ) -> PersonalizedDrugReport:
        """Parse enhanced Cohere response incorporating database data."""
        
        # Log the AI response for debugging
        logger.debug(f"AI Response for {drug}: {ai_response[:500]}...")
        
        # Parse sections from AI response using ** headers
        sections = {}
        current_section = None
        current_content = []
        
        for line in ai_response.split('\n'):
            line = line.strip()
            
            # Check for section headers with ** formatting
            if line.startswith('**') and line.endswith('**'):
                # Save previous section
                if current_section and current_content:
                    sections[current_section] = ' '.join(current_content).strip()
                
                # Start new section
                current_section = line.replace('**', '').replace(':', '').strip()
                current_content = []
                
            elif line.startswith('**') and ':' in line:
                # Handle headers like **SECTION:** without closing **
                if current_section and current_content:
                    sections[current_section] = ' '.join(current_content).strip()
                
                current_section = line.replace('**', '').replace(':', '').strip()
                current_content = []
                
            elif current_section and line:
                # Add content to current section, skip empty lines and instructions
                if not line.startswith('[') and not line.startswith('IMPORTANT:') and not line.startswith('INSTRUCTIONS:'):
                    current_content.append(line)
        
        # Add the last section
        if current_section and current_content:
            sections[current_section] = ' '.join(current_content).strip()
        
        # Log parsed sections for debugging
        logger.debug(f"Parsed sections for {drug}: {list(sections.keys())}")
        
        # If no structured sections found, try alternative parsing
        if not sections:
            logger.warning(f"No structured sections found for {drug}, attempting alternative parsing")
            # Try to parse without ** formatting
            for line in ai_response.split('\n'):
                line = line.strip()
                if line.endswith(':') and any(keyword in line.upper() for keyword in 
                    ['EFFICACY', 'RISK', 'DOSAGE', 'ALTERNATIVE', 'CLINICAL', 'CONFIDENCE', 
                     'PHARMACOKINETIC', 'PHARMACODYNAMIC', 'CONTRAINDICATIONS', 'MONITORING']):
                    if current_section:
                        sections[current_section] = ' '.join(current_content).strip()
                    current_section = line.replace(':', '').strip()
                    current_content = []
                elif line and current_section:
                    current_content.append(line)
            
            if current_section and current_content:
                sections[current_section] = ' '.join(current_content).strip()
        
        # If still no sections, use the full response but truncate for readability
        if not sections:
            logger.warning(f"No sections parsed from AI response for {drug}, using truncated full response")
            truncated_response = ai_response[:300] + "..." if len(ai_response) > 300 else ai_response
            sections['EFFICACY_PREDICTION'] = truncated_response
        
        # Clean and validate sections
        cleaned_sections = {}
        for key, value in sections.items():
            # Remove instruction text and clean up
            cleaned_value = value.replace('[', '').replace(']', '')
            # Truncate very long responses for readability
            if len(cleaned_value) > 500:
                cleaned_value = cleaned_value[:500] + "..."
            cleaned_sections[key] = cleaned_value
        
        # Create structured report with drug-specific defaults
        report = PersonalizedDrugReport(
            drug_name=drug,
            patient_genetic_profile=genetic_profile,
            efficacy_prediction=cleaned_sections.get('EFFICACY_PREDICTION', f'Based on genetic analysis, {drug} efficacy may be influenced by individual genetic factors. Clinical assessment and monitoring recommended.'),
            risk_assessment=cleaned_sections.get('RISK_ASSESSMENT', f'Standard risk profile for {drug}. Monitor for common adverse effects and consider genetic variations that may affect drug response.'),
            dosage_recommendation=cleaned_sections.get('DOSAGE_RECOMMENDATION', f'Follow standard dosing guidelines for {drug} with careful clinical monitoring. Consider dose adjustments based on genetic factors and patient response.'),
            alternative_medications=self._parse_alternatives(cleaned_sections.get('ALTERNATIVE_MEDICATIONS', '')),
            clinical_considerations=cleaned_sections.get('CLINICAL_CONSIDERATIONS', f'Standard clinical monitoring recommended for {drug} therapy with attention to genetic factors that may influence response.'),
            confidence_level=self._normalize_confidence_level(cleaned_sections.get('CONFIDENCE_LEVEL', 'MEDIUM')),
            data_sources=data_sources,
            genetic_variants_analyzed=genetic_profile['relevant_genes'],
            pharmacokinetic_impact=cleaned_sections.get('PHARMACOKINETIC_IMPACT', f'Genetic variants may affect {drug} absorption, distribution, metabolism, and elimination. Clinical assessment recommended.'),
            pharmacodynamic_impact=cleaned_sections.get('PHARMACODYNAMIC_IMPACT', f'Genetic variants may influence {drug} target interactions and therapeutic response. Monitor for efficacy and adverse effects.'),
            contraindications=self._parse_contraindications(cleaned_sections.get('CONTRAINDICATIONS', '')),
            monitoring_recommendations=cleaned_sections.get('MONITORING_RECOMMENDATIONS', f'Follow standard monitoring protocols for {drug} therapy with consideration of genetic factors.')
        )
        
        return report
    
    def _generate_ai_only_report(
        self,
        drug: str,
        genetic_profile: Dict[str, Any],
        annotated_variants: List[AnnotatedVariant]
    ) -> PersonalizedDrugReport:
        """Generate pure AI analysis when no database data is available."""
        
        # Create AI-only prompt
        prompt = self._create_comprehensive_prompt(
            drug, genetic_profile, [], include_database_data=False
        )
        
        try:
            # Get AI analysis
            if self.cohere_client:
                response = self.cohere_client.chat(
                    model="command-r-plus-08-2024",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.1,  # Lower temperature for more consistent responses
                    frequency_penalty=0.1,  # Reduce repetition
                    presence_penalty=0.1   # Encourage diverse content
                )
                
                ai_analysis = response.message.content[0].text.strip()
                
                # Parse AI response into structured report
                report = self._parse_comprehensive_response(
                    drug, ai_analysis, genetic_profile, ["Cohere AI Analysis"]
                )
            else:
                logger.warning("Cohere client not available, creating basic report")
                report = self._create_fallback_report(drug, genetic_profile, [])
            
        except Exception as e:
            logger.error(f"Error generating AI-only report for {drug}: {e}")
            report = self._create_fallback_report(drug, genetic_profile, [])
        
        return report
    
    def _create_comprehensive_prompt(
        self,
        drug: str,
        genetic_profile: Dict[str, Any],
        database_interactions: List[DrugGeneInteraction],
        include_database_data: bool = True
    ) -> str:
        """Create a comprehensive prompt for AI analysis."""
        
        prompt = f"""As a clinical pharmacogenomics expert, analyze this patient's genetic profile and provide a comprehensive personalized drug report for {drug}.

PATIENT GENETIC PROFILE:
- Total variants analyzed: {genetic_profile['total_variants']}
- Relevant genes: {', '.join(genetic_profile['relevant_genes'][:10])}
- Pharmacokinetic genes found: {', '.join(genetic_profile['pharmacokinetic_genes'])}
- Pharmacodynamic genes found: {', '.join(genetic_profile['pharmacodynamic_genes'])}

GENE-SPECIFIC VARIANTS:"""
        
        # Add gene variant information (limit to prevent token overflow)
        for gene, variants in list(genetic_profile['gene_variants'].items())[:5]:
            prompt += f"\n{gene}: {len(variants)} variants found"
        
        if include_database_data and database_interactions:
            prompt += f"\n\nEXISTING PHARMACOGENOMIC DATA:"
            for interaction in database_interactions[:3]:  # Limit to prevent overflow
                prompt += f"\n- {interaction.gene}: {interaction.evidence_level} evidence, {interaction.recommendation}"
        
        prompt += f"""

Please provide a comprehensive personalized analysis in the following format:

EFFICACY_PREDICTION: [How effective will {drug} be for this patient based on their genetic profile]

RISK_ASSESSMENT: [Specific risks, adverse reactions, or concerns for this patient]

DOSAGE_RECOMMENDATION: [Specific dosing recommendations based on genetic variants]

ALTERNATIVE_MEDICATIONS: [List 3-5 alternative drugs that might be better suited]

CLINICAL_CONSIDERATIONS: [Important clinical factors to monitor]

CONFIDENCE_LEVEL: [HIGH/MEDIUM/LOW based on available genetic evidence]

PHARMACOKINETIC_IMPACT: [How genetics affects drug absorption, metabolism, distribution, excretion]

PHARMACODYNAMIC_IMPACT: [How genetics affects drug target response and efficacy]

CONTRAINDICATIONS: [Any genetic contraindications or warnings]

MONITORING_RECOMMENDATIONS: [Specific monitoring guidelines for this patient]

Provide specific, actionable recommendations based on the genetic evidence available."""
        
        return prompt
    
    def _parse_comprehensive_response(
        self,
        drug: str,
        ai_response: str,
        genetic_profile: Dict[str, Any],
        data_sources: List[str]
    ) -> PersonalizedDrugReport:
        """Parse AI response into a structured PersonalizedDrugReport."""
        
        # Log the AI response for debugging
        logger.debug(f"AI Response for {drug}: {ai_response[:500]}...")
        
        # Parse sections from AI response
        sections = {}
        current_section = None
        current_content = []
        
        for line in ai_response.split('\n'):
            line = line.strip()
            if line.endswith(':') and any(keyword in line.upper() for keyword in 
                ['EFFICACY', 'RISK', 'DOSAGE', 'ALTERNATIVE', 'CLINICAL', 'CONFIDENCE', 
                 'PHARMACOKINETIC', 'PHARMACODYNAMIC', 'CONTRAINDICATIONS', 'MONITORING']):
                if current_section:
                    sections[current_section] = ' '.join(current_content).strip()
                current_section = line.replace(':', '').strip()
                current_content = []
            elif line and current_section:
                current_content.append(line)
        
        # Add the last section
        if current_section and current_content:
            sections[current_section] = ' '.join(current_content).strip()
        
        # Log parsed sections for debugging
        logger.debug(f"Parsed sections for {drug}: {list(sections.keys())}")
        
        # If sections are empty, try alternative parsing
        if not sections:
            logger.warning(f"No sections parsed from AI response for {drug}, using full response")
            # Use the full response as efficacy prediction
            sections['EFFICACY_PREDICTION'] = ai_response
        
        # Normalize confidence level
        confidence_text = sections.get('CONFIDENCE_LEVEL', 'MEDIUM')
        confidence_level = self._normalize_confidence_level(confidence_text)
        
        # Create structured report with meaningful defaults
        report = PersonalizedDrugReport(
            drug_name=drug,
            patient_genetic_profile=genetic_profile,
            efficacy_prediction=sections.get('EFFICACY_PREDICTION', f'Based on genetic analysis of {len(genetic_profile["relevant_genes"])} genes, standard efficacy expected for {drug}. Individual genetic factors require clinical assessment.'),
            risk_assessment=sections.get('RISK_ASSESSMENT', f'Standard risk monitoring recommended for {drug}. Consider individual genetic variations that may affect drug response.'),
            dosage_recommendation=sections.get('DOSAGE_RECOMMENDATION', f'Follow standard dosing guidelines for {drug} with clinical monitoring. Genetic testing may help optimize dosing.'),
            alternative_medications=self._parse_alternatives(sections.get('ALTERNATIVE_MEDICATIONS', '')),
            clinical_considerations=sections.get('CLINICAL_CONSIDERATIONS', f'Standard clinical monitoring recommended for {drug} therapy with attention to individual genetic factors.'),
            confidence_level=confidence_level,
            data_sources=data_sources,
            genetic_variants_analyzed=genetic_profile['relevant_genes'],
            pharmacokinetic_impact=sections.get('PHARMACOKINETIC_IMPACT', f'Genetic impact on {drug} metabolism and clearance requires clinical assessment based on individual variants.'),
            pharmacodynamic_impact=sections.get('PHARMACODYNAMIC_IMPACT', f'Genetic impact on {drug} target response requires clinical assessment based on individual variants.'),
            contraindications=self._parse_contraindications(sections.get('CONTRAINDICATIONS', '')),
            monitoring_recommendations=sections.get('MONITORING_RECOMMENDATIONS', f'Follow standard monitoring protocols for {drug} therapy with consideration of genetic factors.')
        )
        
        return report
    
    def _parse_alternatives(self, alternatives_text: str) -> List[str]:
        """Parse alternative medications from text."""
        alternatives = []
        for line in alternatives_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('[') and not line.endswith(']'):
                # Remove bullet points and numbers
                clean_line = line.lstrip('- •1234567890. ')
                if clean_line:
                    alternatives.append(clean_line)
        return alternatives[:5]  # Limit to 5 alternatives
    
    def _parse_contraindications(self, contraindications_text: str) -> List[str]:
        """Parse contraindications from text."""
        contraindications = []
        for line in contraindications_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('[') and not line.endswith(']'):
                clean_line = line.lstrip('- •1234567890. ')
                if clean_line:
                    contraindications.append(clean_line)
        return contraindications[:3]  # Limit to 3 contraindications
    
    def _create_fallback_report(
        self,
        drug: str,
        genetic_profile: Dict[str, Any],
        database_interactions: List[DrugGeneInteraction]
    ) -> PersonalizedDrugReport:
        """Create a fallback report when AI analysis fails."""
        
        data_sources = ["Manual Analysis"] if not database_interactions else list(set([i.source for i in database_interactions]))
        
        # Create drug-specific fallback content
        drug_lower = drug.lower()
        
        # Drug-specific efficacy predictions
        if 'paracetamol' in drug_lower or 'acetaminophen' in drug_lower:
            efficacy_pred = f"{drug} efficacy may be influenced by genetic variants affecting hepatic metabolism. Individual response assessment recommended."
            risk_assess = f"Monitor for hepatotoxicity risk with {drug}, especially with genetic variants affecting CYP enzymes and glutathione pathways."
            dosage_rec = f"Standard {drug} dosing with hepatic function monitoring. Consider genetic factors affecting metabolism."
        elif 'metformin' in drug_lower:
            efficacy_pred = f"{drug} efficacy may be affected by genetic variants in glucose metabolism and drug transport. Monitor glycemic response."
            risk_assess = f"Assess risk of lactic acidosis and gastrointestinal effects with {drug}. Consider genetic factors affecting drug transport."
            dosage_rec = f"Initiate {drug} at standard dose with gradual titration based on tolerance and glycemic response."
        elif 'sildenafil' in drug_lower:
            efficacy_pred = f"{drug} efficacy may vary based on genetic factors affecting cardiovascular response and drug metabolism."
            risk_assess = f"Monitor cardiovascular effects and drug interactions with {drug}. Consider genetic variants affecting CYP3A4 metabolism."
            dosage_rec = f"Standard {drug} dosing with cardiovascular assessment. Adjust based on response and genetic factors."
        elif 'warfarin' in drug_lower:
            efficacy_pred = f"{drug} response highly dependent on genetic variants in CYP2C9 and VKORC1. Genetic testing strongly recommended."
            risk_assess = f"High bleeding risk with {drug}. Genetic variants significantly affect dosing requirements and safety."
            dosage_rec = f"Genetic-guided dosing essential for {drug}. Start with reduced dose and frequent INR monitoring."
        else:
            efficacy_pred = f"{drug} efficacy may be influenced by individual genetic factors. Clinical assessment and monitoring recommended."
            risk_assess = f"Standard risk profile for {drug}. Monitor for adverse effects and consider genetic variations affecting drug response."
            dosage_rec = f"Follow standard dosing guidelines for {drug} with clinical monitoring. Consider genetic factors if available."
        
        return PersonalizedDrugReport(
            drug_name=drug,
            patient_genetic_profile=genetic_profile,
            efficacy_prediction=efficacy_pred,
            risk_assessment=risk_assess,
            dosage_recommendation=dosage_rec,
            alternative_medications=[f"Consult physician for {drug} alternatives based on genetic profile"],
            clinical_considerations=f"Standard clinical monitoring recommended for {drug} therapy with attention to genetic factors.",
            confidence_level="LOW",
            data_sources=data_sources,
            genetic_variants_analyzed=genetic_profile['relevant_genes'],
            pharmacokinetic_impact=f"Genetic variants may affect {drug} absorption, distribution, metabolism, and elimination.",
            pharmacodynamic_impact=f"Genetic variants may influence {drug} target interactions and therapeutic response.",
            contraindications=["None specifically identified"],
            monitoring_recommendations=f"Follow standard monitoring protocols for {drug} therapy with genetic considerations."
        )

    def _normalize_confidence_level(self, confidence_text: str) -> str:
        """Normalize confidence level text to HIGH/MEDIUM/LOW."""
        if 'HIGH' in confidence_text:
            return 'HIGH'
        elif 'MEDIUM' in confidence_text:
            return 'MEDIUM'
        elif 'LOW' in confidence_text:
            return 'LOW'
        else:
            return 'MEDIUM'

    def _generate_database_only_report(
        self,
        drug: str,
        genetic_profile: Dict[str, Any],
        database_interactions: List[DrugGeneInteraction]
    ) -> PersonalizedDrugReport:
        """Generate report using only database interactions when AI is disabled."""
        
        # Extract data sources
        data_sources = list(set([interaction.source for interaction in database_interactions]))
        
        # Aggregate database recommendations
        high_evidence_interactions = [i for i in database_interactions if i.cpic_level == 'A' or i.pharmgkb_level in ['1A', '1B']]
        
        # Create evidence-based recommendations
        if high_evidence_interactions:
            confidence_level = "HIGH"
            efficacy_pred = f'High-quality evidence available for {drug} from {", ".join(data_sources)}. ' + \
                          f'Based on {len(high_evidence_interactions)} high-evidence interactions.'
            risk_assessment = f'Risk assessment based on {len(database_interactions)} database interactions. ' + \
                            'Monitor for known pharmacogenomic effects.'
        else:
            confidence_level = "MEDIUM"
            efficacy_pred = f'Moderate evidence available for {drug} from database sources. Clinical assessment recommended.'
            risk_assessment = f'Standard risk monitoring recommended based on available database evidence.'
        
        # Extract key recommendations from database interactions
        recommendations = []
        for interaction in database_interactions[:3]:  # Top 3 interactions
            if interaction.recommendation:
                recommendations.append(interaction.recommendation)
        
        dosage_rec = '. '.join(recommendations[:2]) if recommendations else f'Follow standard dosing guidelines for {drug}.'
        
        report = PersonalizedDrugReport(
            drug_name=drug,
            patient_genetic_profile=genetic_profile,
            efficacy_prediction=efficacy_pred,
            risk_assessment=risk_assessment,
            dosage_recommendation=dosage_rec,
            alternative_medications=[f'Consult {source} guidelines for alternatives' for source in data_sources[:3]],
            clinical_considerations=f'Evidence from {", ".join(data_sources)} provides clinical guidance for {drug} therapy.',
            confidence_level=confidence_level,
            data_sources=data_sources,
            genetic_variants_analyzed=genetic_profile['relevant_genes'],
            pharmacokinetic_impact=f'Database evidence suggests genetic factors may affect {drug} metabolism.',
            pharmacodynamic_impact=f'Database evidence suggests genetic factors may affect {drug} response.',
            contraindications=self._extract_database_contraindications(database_interactions),
            monitoring_recommendations=f'Follow monitoring guidelines from {", ".join(data_sources[:2])} for {drug} therapy.'
        )
        
        return report
    
    def _extract_database_contraindications(self, database_interactions: List[DrugGeneInteraction]) -> List[str]:
        """Extract contraindications from database interactions."""
        contraindications = []
        for interaction in database_interactions:
            if hasattr(interaction, 'contraindications') and interaction.contraindications:
                contraindications.append(f"{interaction.gene}: {interaction.contraindications}")
            elif 'avoid' in interaction.recommendation.lower() or 'contraindicated' in interaction.recommendation.lower():
                contraindications.append(f"{interaction.gene}: {interaction.recommendation}")
        
        return contraindications[:3] if contraindications else ["None specifically identified in database"] 
