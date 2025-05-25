#!/usr/bin/env python3

import json
import logging
import os
import requests
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

import cohere
from drug_mapper import DrugGeneInteraction

logger = logging.getLogger(__name__)

@dataclass
class AIExplanation:
    interaction: DrugGeneInteraction
    summary: str
    risk_assessment: str
    mechanism: Optional[str] = None
    alternative_suggestions: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.alternative_suggestions is None:
            self.alternative_suggestions = []

class CohereExplainer:
    
    DGIDB_GRAPHQL_ENDPOINT = "https://dgidb.org/api/graphql"
    
    def __init__(self, api_key: str, data_dir: Optional[Path] = None):
        self.api_key = api_key
        self.cohere_client = cohere.ClientV2(api_key=api_key) if api_key else None
        self.data_dir = data_dir or Path("data")
        
        self.data_dir.mkdir(exist_ok=True)
        
        self.pharmgkb_data = self._load_pharmgkb_data()
        self.cpic_data = self._load_cpic_data()
        
        logger.debug("Initialized Cohere explainer with dynamic data sources")
    
    def _load_pharmgkb_data(self) -> Dict:
        pharmgkb_dir = self.data_dir / "pharmgkb"
        pharmgkb_data = {}
        
        try:
            if not pharmgkb_dir.exists():
                pharmgkb_dir.mkdir(exist_ok=True)
                logger.warning(f"PharmGKB data directory created at {pharmgkb_dir}. Please download data files.")
                return pharmgkb_data
            
            drug_gene_file = pharmgkb_dir / "drug_gene_associations.tsv"
            if drug_gene_file.exists():
                pharmgkb_data["drug_gene"] = self._parse_tsv_file(drug_gene_file)
                logger.info(f"Loaded {len(pharmgkb_data['drug_gene'])} PharmGKB drug-gene associations")
            
            clinical_ann_file = pharmgkb_dir / "clinical_annotations.tsv"
            if clinical_ann_file.exists():
                pharmgkb_data["clinical_annotations"] = self._parse_tsv_file(clinical_ann_file)
                logger.info(f"Loaded {len(pharmgkb_data['clinical_annotations'])} PharmGKB clinical annotations")
            
            drug_labels_file = pharmgkb_dir / "drug_labels.tsv"
            if drug_labels_file.exists():
                pharmgkb_data["drug_labels"] = self._parse_tsv_file(drug_labels_file)
                logger.info(f"Loaded {len(pharmgkb_data['drug_labels'])} PharmGKB drug labels")
                
        except Exception as e:
            logger.error(f"Error loading PharmGKB data: {e}")
        
        return pharmgkb_data
    
    def _load_cpic_data(self) -> Dict:
        cpic_dir = self.data_dir / "cpic"
        cpic_data = {}
        
        try:
            if not cpic_dir.exists():
                cpic_dir.mkdir(exist_ok=True)
                logger.warning(f"CPIC data directory created at {cpic_dir}. Please download guideline files.")
                return cpic_data
            
            guidelines_file = cpic_dir / "cpic_guidelines.json"
            if guidelines_file.exists():
                with open(guidelines_file, 'r') as f:
                    cpic_data["guidelines"] = json.load(f)
                logger.info(f"Loaded CPIC guidelines from {guidelines_file}")
            
            gene_drug_file = cpic_dir / "gene_drug_pairs.tsv"
            if gene_drug_file.exists():
                cpic_data["gene_drug_pairs"] = self._parse_tsv_file(gene_drug_file)
                logger.info(f"Loaded {len(cpic_data['gene_drug_pairs'])} CPIC gene-drug pairs")
                
        except Exception as e:
            logger.error(f"Error loading CPIC data: {e}")
        
        return cpic_data
    
    def _parse_tsv_file(self, file_path: Path) -> List[Dict]:
        data = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                header = f.readline().strip().split('\t')
                for line in f:
                    values = line.strip().split('\t')
                    if len(values) >= len(header):
                        row_data = {header[i]: values[i] for i in range(len(header))}
                        data.append(row_data)
        except Exception as e:
            logger.error(f"Error parsing TSV file {file_path}: {e}")
            
        return data
    
    def _query_dgidb(self, gene: str, drug: str) -> Dict:
        query = """
        query($gene: String!, $drug: String!) {
          genes(name: $gene) {
            name
            interactions(drugName: $drug) {
              drugName
              interactionScore
              interactionTypes
              pmids
              sources {
                sourceName
              }
            }
          }
        }
        """
        
        variables = {
            "gene": gene,
            "drug": drug
        }
        
        try:
            response = requests.post(
                self.DGIDB_GRAPHQL_ENDPOINT,
                json={"query": query, "variables": variables}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error querying DGIdb: {e}")
            return {"data": {"genes": []}}
    
    def explain_interactions(self, interactions: List[DrugGeneInteraction]) -> List[AIExplanation]:
        if not self.api_key:
            logger.warning("No Cohere API key provided. Returning basic explanations.")
            return self._generate_basic_explanations(interactions)
        
        logger.info(f"Generating explanations for {len(interactions)} interactions using Cohere")
        explanations = []
        
        for interaction in interactions:
            try:
                context = self._gather_interaction_context(interaction)
                explanation = self._explain_interaction(interaction, context)
                explanations.append(explanation)
            except Exception as e:
                logger.error(f"Error generating explanation for {interaction}: {e}")
                explanations.append(self._generate_basic_explanation(interaction))
        
        return explanations
    
    def _gather_interaction_context(self, interaction: DrugGeneInteraction) -> Dict:
        context = {
            "pharmgkb": {},
            "cpic": {},
            "dgidb": {}
        }
        
        drug = interaction.drug.lower()
        gene = interaction.gene.lower()
        
        if "drug_gene" in self.pharmgkb_data:
            for entry in self.pharmgkb_data["drug_gene"]:
                if "Drug" in entry and "Gene" in entry:
                    if entry["Drug"].lower() == drug and entry["Gene"].lower() == gene:
                        context["pharmgkb"]["association"] = entry
        
        if "clinical_annotations" in self.pharmgkb_data:
            for entry in self.pharmgkb_data["clinical_annotations"]:
                if "Drug" in entry and "Gene" in entry:
                    if entry["Drug"].lower() == drug and entry["Gene"].lower() == gene:
                        if "annotations" not in context["pharmgkb"]:
                            context["pharmgkb"]["annotations"] = []
                        context["pharmgkb"]["annotations"].append(entry)
        
        if "gene_drug_pairs" in self.cpic_data:
            for entry in self.cpic_data["gene_drug_pairs"]:
                if "Drug" in entry and "Gene" in entry:
                    if entry["Drug"].lower() == drug and entry["Gene"].lower() == gene:
                        context["cpic"]["gene_drug_pair"] = entry
        
        if "guidelines" in self.cpic_data:
            for guideline in self.cpic_data["guidelines"]:
                if "drugs" in guideline and "genes" in guideline:
                    drug_match = any(d.lower() == drug for d in guideline["drugs"])
                    gene_match = any(g.lower() == gene for g in guideline["genes"])
                    if drug_match and gene_match:
                        context["cpic"]["guideline"] = guideline
        
        dgidb_data = self._query_dgidb(gene, drug)
        if "data" in dgidb_data and "genes" in dgidb_data["data"] and dgidb_data["data"]["genes"]:
            context["dgidb"] = dgidb_data["data"]["genes"][0]
        
        return context
    
    def _explain_interaction(self, interaction: DrugGeneInteraction, context: Dict) -> AIExplanation:
        prompt = self._construct_prompt(interaction, context)
        
        response = self.cohere_client.chat(
            model="command-r-plus-08-2024",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.2
        )
        
        try:
            text_response = response.message.content[0].text
            return self._parse_cohere_response(text_response, interaction)
        except Exception as e:
            logger.error(f"Error parsing Cohere response: {e}")
            logger.debug(f"Response: {response}")
            return self._generate_basic_explanation(interaction)
    
    def _construct_prompt(self, interaction: DrugGeneInteraction, context: Dict) -> str:
        prompt = f"""
You are a pharmacogenomics expert. Please analyze the following drug-gene interaction and provide a detailed explanation:

Drug: {interaction.drug}
Gene: {interaction.gene}
Phenotype: {interaction.phenotype or 'Unknown'}
Source: {interaction.source}
Evidence Level: {interaction.evidence_level or 'Unknown'}
"""
        
        if context["pharmgkb"]:
            prompt += "\n### PharmGKB Data:\n"
            
            if "association" in context["pharmgkb"]:
                assoc = context["pharmgkb"]["association"]
                prompt += f"Association: {assoc.get('Association', 'Unknown')}\n"
                prompt += f"PK/PD: {assoc.get('PK/PD', 'Unknown')}\n"
            
            if "annotations" in context["pharmgkb"] and context["pharmgkb"]["annotations"]:
                ann = context["pharmgkb"]["annotations"][0]
                prompt += f"Phenotype: {ann.get('Phenotype', 'Unknown')}\n"
                prompt += f"Significance: {ann.get('Significance', 'Unknown')}\n"
        
        if context["cpic"]:
            prompt += "\n### CPIC Data:\n"
            
            if "gene_drug_pair" in context["cpic"]:
                pair = context["cpic"]["gene_drug_pair"]
                prompt += f"Level: {pair.get('Level', 'Unknown')}\n"
                prompt += f"Guideline: {pair.get('Guideline', 'Unknown')}\n"
            
            if "guideline" in context["cpic"]:
                guide = context["cpic"]["guideline"]
                prompt += f"Recommendation: {guide.get('recommendation', 'Unknown')}\n"
                prompt += f"Implications: {guide.get('implications', 'Unknown')}\n"
        
        if context["dgidb"] and "interactions" in context["dgidb"]:
            prompt += "\n### DGIdb Data:\n"
            for interaction in context["dgidb"]["interactions"]:
                if "interactionTypes" in interaction:
                    prompt += f"Interaction Types: {', '.join(interaction['interactionTypes'])}\n"
                if "interactionScore" in interaction:
                    prompt += f"Score: {interaction['interactionScore']}\n"
                if "sources" in interaction:
                    sources = [s["sourceName"] for s in interaction["sources"]]
                    prompt += f"Sources: {', '.join(sources)}\n"
        
        prompt += """
Based on this information and established pharmacogenomic knowledge, please provide:

1. A brief summary of this interaction (2-3 sentences).
2. An assessment of potential risks or benefits (1-2 sentences).
3. The mechanism of interaction between the drug and gene (1-2 sentences).
4. Suggested alternative medications if this interaction poses risks (list up to 3).

Format your response as JSON with the following structure:
{
  "summary": "...",
  "risk_assessment": "...",
  "mechanism": "...",
  "alternative_suggestions": ["drug1", "drug2", "drug3"]
}

Ensure your response is evidence-based, clinically relevant, and focused on pharmacogenomic implications.
"""
        
        return prompt
    
    def _parse_cohere_response(self, response: str, interaction: DrugGeneInteraction) -> AIExplanation:
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                
                return AIExplanation(
                    interaction=interaction,
                    summary=data.get("summary", "No summary available."),
                    risk_assessment=data.get("risk_assessment", "No risk assessment available."),
                    mechanism=data.get("mechanism", "Mechanism unknown."),
                    alternative_suggestions=data.get("alternative_suggestions", [])
                )
            else:
                return self._extract_explanation_from_text(response, interaction)
                
        except json.JSONDecodeError:
            return self._extract_explanation_from_text(response, interaction)
        except Exception as e:
            logger.error(f"Error parsing Cohere response: {e}")
            return self._generate_basic_explanation(interaction)
    
    def _extract_explanation_from_text(self, text: str, interaction: DrugGeneInteraction) -> AIExplanation:
        lines = text.split("\n")
        summary = ""
        risk_assessment = ""
        mechanism = ""
        alternatives = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "summary" in line.lower():
                current_section = "summary"
                continue
            elif "risk" in line.lower() or "assessment" in line.lower():
                current_section = "risk"
                continue
            elif "mechanism" in line.lower():
                current_section = "mechanism"
                continue
            elif "alternative" in line.lower() or "suggestion" in line.lower():
                current_section = "alternatives"
                continue
                
            if current_section == "summary":
                summary += line + " "
            elif current_section == "risk":
                risk_assessment += line + " "
            elif current_section == "mechanism":
                mechanism += line + " "
            elif current_section == "alternatives":
                if ":" in line:
                    drug = line.split(":", 1)[1].strip()
                    alternatives.append(drug)
                elif "-" in line:
                    drug = line.split("-", 1)[1].strip()
                    alternatives.append(drug)
                elif line and not line.startswith(("1.", "2.", "3.", "•")):
                    alternatives.append(line)
        
        summary = summary.strip() or "No summary available."
        risk_assessment = risk_assessment.strip() or "No risk assessment available."
        mechanism = mechanism.strip() or "Mechanism unknown."
        
        return AIExplanation(
            interaction=interaction,
            summary=summary,
            risk_assessment=risk_assessment,
            mechanism=mechanism,
            alternative_suggestions=alternatives
        )
    
    def _generate_basic_explanations(self, interactions: List[DrugGeneInteraction]) -> List[AIExplanation]:
        return [self._generate_basic_explanation(interaction) for interaction in interactions]
    
    def _generate_basic_explanation(self, interaction: DrugGeneInteraction) -> AIExplanation:
        drug = interaction.drug
        gene = interaction.gene
        phenotype = interaction.phenotype or "unknown phenotype"
        
        try:
            dgidb_data = self._query_dgidb(gene, drug)
            dgidb_info = self._extract_dgidb_info(dgidb_data, drug, gene)
        except Exception as e:
            logger.warning(f"Error getting DGIdb data for {drug}-{gene}: {e}")
            dgidb_info = {}
            
        pharmgkb_info = self._get_pharmgkb_info(drug, gene)
        cpic_info = self._get_cpic_info(drug, gene)
        
        if dgidb_info.get("interaction_types") or pharmgkb_info.get("phenotype") or cpic_info.get("guideline"):
            interaction_types = dgidb_info.get("interaction_types", [])
            interaction_type_str = ", ".join(interaction_types) if interaction_types else "unknown mechanism"
            
            specific_phenotype = (
                cpic_info.get("phenotype") or 
                pharmgkb_info.get("phenotype") or 
                phenotype
            )
            
            summary = f"The {drug}-{gene} interaction affects drug response via {interaction_type_str}. {specific_phenotype.capitalize()} has been reported."
            
            if cpic_info.get("recommendation"):
                risk = cpic_info.get("recommendation")
            else:
                evidence = pharmgkb_info.get("evidence_level") or interaction.evidence_level or "unknown"
                risk = f"Patients with variants in {gene} may have altered response to {drug}. Based on {evidence} evidence, monitoring is advised."
            
            if interaction_types:
                mechanism = f"{gene} is involved in the {interaction_type_str} of {drug}, which may affect drug levels or response."
            elif pharmgkb_info.get("pk_status") == "yes":
                mechanism = f"{gene} affects the pharmacokinetics of {drug}, potentially altering drug metabolism or transport."
            else:
                mechanism = f"{gene} may influence response to {drug} through mechanisms that require further study."
            
            alternatives = cpic_info.get("alternatives", [])
            
        else:
            summary = f"The {drug}-{gene} interaction may affect drug response. {phenotype.capitalize()} has been reported."
            risk = f"Patients with variants in {gene} may have altered response to {drug}. Monitoring is advised."
            mechanism = f"{gene} is involved in the metabolism or transport of {drug}, which may affect drug levels or response."
            alternatives = []
        
        return AIExplanation(
            interaction=interaction,
            summary=summary,
            risk_assessment=risk,
            mechanism=mechanism,
            alternative_suggestions=alternatives
        )
        
    def _extract_dgidb_info(self, dgidb_data: Dict, drug: str, gene: str) -> Dict:
        info = {
            "interaction_types": [],
            "sources": [],
            "pmids": [],
            "score": None
        }
        
        try:
            if "data" in dgidb_data and "genes" in dgidb_data["data"]:
                for gene_data in dgidb_data["data"]["genes"]:
                    if gene_data and "interactions" in gene_data:
                        for interaction in gene_data["interactions"]:
                            if interaction.get("drugName", "").lower() == drug.lower():
                                if "interactionTypes" in interaction and interaction["interactionTypes"]:
                                    info["interaction_types"].extend(interaction["interactionTypes"])
                                
                                if "sources" in interaction:
                                    info["sources"].extend([s["sourceName"] for s in interaction["sources"]])
                                
                                if "pmids" in interaction and interaction["pmids"]:
                                    info["pmids"].extend(interaction["pmids"])
                                
                                if "interactionScore" in interaction:
                                    info["score"] = interaction["interactionScore"]
            
            info["interaction_types"] = list(set(info["interaction_types"]))
            info["sources"] = list(set(info["sources"]))
            info["pmids"] = list(set(info["pmids"]))
            
        except Exception as e:
            logger.error(f"Error extracting DGIdb info: {e}")
        
        return info
    
    def _get_pharmgkb_info(self, drug: str, gene: str) -> Dict:
        info = {
            "phenotype": None,
            "evidence_level": None,
            "pk_status": None,
            "pmids": []
        }
        
        try:
            if "drug_gene" in self.pharmgkb_data:
                for row in self.pharmgkb_data["drug_gene"]:
                    drug_name = row.get("Entity1_name", "").lower()
                    gene_name = row.get("Entity2_name", "")
                    
                    if drug_name == drug.lower() and gene_name == gene:
                        info["phenotype"] = row.get("Association")
                        info["evidence_level"] = row.get("Evidence")
                        info["pk_status"] = row.get("PK_Status")
                        if row.get("PMIDs"):
                            info["pmids"].extend(row.get("PMIDs").split(","))
                        break
            
            if "clinical_annotations" in self.pharmgkb_data:
                for row in self.pharmgkb_data["clinical_annotations"]:
                    if row.get("Drug", "").lower() == drug.lower() and row.get("Gene", "") == gene:
                        if not info["phenotype"] and row.get("Phenotype"):
                            info["phenotype"] = row.get("Phenotype")
                        if not info["evidence_level"] and row.get("Level of Evidence"):
                            info["evidence_level"] = row.get("Level of Evidence")
                        if row.get("PMID"):
                            info["pmids"].append(row.get("PMID"))
            
            info["pmids"] = list(set(info["pmids"]))
            
        except Exception as e:
            logger.error(f"Error getting PharmGKB info: {e}")
        
        return info
    
    def _get_cpic_info(self, drug: str, gene: str) -> Dict:
        info = {
            "level": None,
            "guideline": None,
            "recommendation": None,
            "phenotype": None,
            "alternatives": []
        }
        
        try:
            guideline_url = None
            if "gene_drug_pairs" in self.cpic_data:
                for row in self.cpic_data["gene_drug_pairs"]:
                    if row.get("Drug", "").lower() == drug.lower() and row.get("Gene", "") == gene:
                        info["level"] = row.get("Level")
                        guideline_url = row.get("Guideline")
                        break
            
            if guideline_url and "guidelines" in self.cpic_data:
                for guideline in self.cpic_data["guidelines"]:
                    if guideline.get("guidelineUrl") == guideline_url:
                        info["guideline"] = guideline.get("guidelineName")
                        info["recommendation"] = guideline.get("recommendation")
                        
                        if guideline.get("guidelineName"):
                            name = guideline.get("guidelineName")
                            if "and" in name and "for" in name:
                                parts = name.split("for")
                                if len(parts) > 1:
                                    info["phenotype"] = parts[1].strip()
                        
                        if info["recommendation"]:
                            alternatives = []
                            rec = info["recommendation"].lower()
                            if "alternative" in rec and ("drug" in rec or "medication" in rec or "agent" in rec):
                                alt_part = rec.split("alternative")[1]
                                for word in alt_part.split():
                                    word = word.strip(",.;:()")
                                    if word and len(word) > 3 and word not in ["drug", "drugs", "medication", "medications", "agent", "agents", "such", "like", "include", "including"]:
                                        alternatives.append(word)
                            info["alternatives"] = alternatives[:3]
                        
                        break
            
        except Exception as e:
            logger.error(f"Error getting CPIC info: {e}")
        
        return info

class AIExplainer:
    
    def __init__(self, api_key: Optional[str] = None, data_dir: Optional[Path] = None):
        self.api_key = api_key
        self.data_dir = data_dir or Path("data")
        
        self.explainer = CohereExplainer(api_key, self.data_dir)
    
    def explain_interactions(self, interactions) -> List[AIExplanation]:
        if isinstance(interactions, dict):
            logger.info(f"Converting dictionary of interactions to flat list")
            flat_interactions = []
            for drug, drug_interactions in interactions.items():
                flat_interactions.extend(drug_interactions)
            logger.info(f"Generating explanations for {len(flat_interactions)} interactions")
            interactions = flat_interactions
        else:
            logger.info(f"Generating explanations for {len(interactions)} interactions")
            
        return self.explainer.explain_interactions(interactions)
