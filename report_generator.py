#!/usr/bin/env python3
"""
Report Generator Module

This module provides functionality to generate personalized pharmacogenomics reports
in HTML or PDF format. It summarizes drug-gene interactions, risk assessments,
and recommendations based on a patient's genetic profile.
"""

import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import jinja2
from annotator import AnnotatedVariant
from drug_mapper import DrugGeneInteraction
from ai_explainer import AIExplanation

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generates personalized pharmacogenomics reports."""
    
    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize the report generator.
        
        Args:
            template_dir: Directory containing report templates.
        """
        # Set up Jinja2 environment
        if template_dir is None:
            # Use default templates in the package
            template_dir = Path(__file__).parent / "templates"
        
        # Create templates directory if it doesn't exist
        template_dir.mkdir(exist_ok=True)
        
        self.template_dir = template_dir
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(["html", "xml"])
        )
        
        # Create default template if it doesn't exist
        self._ensure_default_template()
    
    def generate_report(
        self,
        explained_interactions: List[AIExplanation],
        output_path: Path,
        format: str = "html"
    ) -> str:
        """
        Generate a personalized pharmacogenomics report.
        
        Args:
            explained_interactions: List of drug-gene interactions with explanations.
            output_path: Output file path.
            format: Output format ("html" or "pdf").
            
        Returns:
            Path to the generated report.
        """
        logger.info(f"Generating {format} report")
        
        # Extract unique drugs from interactions
        drugs = list(set(explanation.interaction.drug for explanation in explained_interactions))
        
        # Prepare data for the template
        report_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "drugs": drugs,
            "interactions_by_drug": {}
        }
        
        # Group interactions by drug
        for drug in drugs:
            drug_interactions = [
                explanation for explanation in explained_interactions 
                if explanation.interaction.drug.lower() == drug.lower()
            ]
            
            report_data["interactions_by_drug"][drug] = []
            
            for explanation in drug_interactions:
                interaction_data = {
                    "gene": explanation.interaction.gene,
                    "phenotype": explanation.interaction.phenotype or "Unknown phenotype",
                    "summary": explanation.summary,
                    "risk_assessment": explanation.risk_assessment,
                    "mechanism": explanation.mechanism,
                    "alternatives": explanation.alternative_suggestions,
                    "evidence_level": explanation.interaction.evidence_level or "Not specified",
                    "source": explanation.interaction.source or "Multiple sources"
                }
                
                report_data["interactions_by_drug"][drug].append(interaction_data)
        
        # Generate HTML
        html_content = self._render_html(report_data)
        
        if format.lower() == "pdf":
            # Convert HTML to PDF
            pdf_path = self._html_to_pdf(html_content, output_path)
            logger.info(f"PDF report generated: {pdf_path}")
            return str(pdf_path)
        else:
            # Save as HTML
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            logger.info(f"HTML report generated: {output_path}")
            return str(output_path)
    
    def _render_html(self, report_data: Dict[str, Any]) -> str:
        """
        Render the report as HTML.
        
        Args:
            report_data: Dictionary of data for the template.
            
        Returns:
            HTML string.
        """
        # Modern HTML template with improved styling
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Pharmacogenomics Report</title>
            <style>
                :root {{
                    --primary-color: #2563eb;
                    --primary-light: #dbeafe;
                    --secondary-color: #475569;
                    --accent-color: #8b5cf6;
                    --success-color: #10b981;
                    --warning-color: #f59e0b;
                    --danger-color: #ef4444;
                    --text-color: #1e293b;
                    --text-light: #64748b;
                    --bg-color: #ffffff;
                    --bg-light: #f8fafc;
                    --border-color: #e2e8f0;
                    --border-radius: 8px;
                    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                }}
                
                * {{
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                }}
                
                body {{
                    font-family: 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: var(--text-color);
                    background-color: var(--bg-light);
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                
                .container {{
                    background-color: var(--bg-color);
                    border-radius: var(--border-radius);
                    box-shadow: var(--shadow);
                    padding: 30px;
                    margin-bottom: 30px;
                }}
                
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    border-bottom: 2px solid var(--primary-light);
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                
                .header-left {{
                    flex: 1;
                }}
                
                .header-right {{
                    text-align: right;
                    color: var(--text-light);
                }}
                
                h1, h2, h3, h4 {{
                    color: var(--primary-color);
                    margin-bottom: 15px;
                }}
                
                h1 {{
                    font-size: 2.2rem;
                    font-weight: 700;
                }}
                
                h2 {{
                    font-size: 1.8rem;
                    font-weight: 600;
                    border-bottom: 1px solid var(--border-color);
                    padding-bottom: 10px;
                    margin-top: 30px;
                }}
                
                h3 {{
                    font-size: 1.4rem;
                    font-weight: 600;
                }}
                
                h4 {{
                    font-size: 1.1rem;
                    font-weight: 600;
                    color: var(--secondary-color);
                }}
                
                p {{
                    margin-bottom: 15px;
                }}
                
                .overview {{
                    background-color: var(--primary-light);
                    border-radius: var(--border-radius);
                    padding: 20px;
                    margin-bottom: 30px;
                }}
                
                .overview ul {{
                    list-style-type: none;
                    display: flex;
                    flex-wrap: wrap;
                    gap: 15px;
                    margin-top: 15px;
                }}
                
                .overview li {{
                    background-color: var(--bg-color);
                    border-radius: var(--border-radius);
                    padding: 10px 15px;
                    box-shadow: var(--shadow);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}
                
                .drug-badge {{
                    background-color: var(--primary-color);
                    color: white;
                    border-radius: 20px;
                    padding: 5px 12px;
                    font-weight: 600;
                    font-size: 0.9rem;
                }}
                
                .drug-section {{
                    margin-bottom: 40px;
                    border: 1px solid var(--border-color);
                    border-radius: var(--border-radius);
                    overflow: hidden;
                }}
                
                .drug-header {{
                    background-color: var(--primary-color);
                    color: white;
                    padding: 15px 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                
                .drug-header h2 {{
                    color: white;
                    margin: 0;
                    border: none;
                    padding: 0;
                }}
                
                .drug-content {{
                    padding: 20px;
                }}
                
                .interaction {{
                    margin: 20px 0;
                    padding: 20px;
                    background-color: var(--bg-light);
                    border-radius: var(--border-radius);
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                    border-left: 4px solid var(--accent-color);
                }}
                
                .risk-high {{
                    border-left-color: var(--danger-color);
                }}
                
                .risk-medium {{
                    border-left-color: var(--warning-color);
                }}
                
                .risk-low {{
                    border-left-color: var(--success-color);
                }}
                
                .gene-name {{
                    color: var(--accent-color);
                    font-weight: 600;
                }}
                
                .summary {{
                    background-color: var(--primary-light);
                    padding: 15px;
                    border-radius: var(--border-radius);
                    margin: 15px 0;
                    font-weight: 500;
                }}
                
                .section-title {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-top: 20px;
                    margin-bottom: 10px;
                    color: var(--secondary-color);
                }}
                
                .section-title::before {{
                    content: "";
                    display: block;
                    width: 6px;
                    height: 20px;
                    background-color: var(--accent-color);
                    border-radius: 3px;
                }}
                
                .alternatives {{
                    background-color: #f0f7ff;
                    padding: 15px;
                    border-radius: var(--border-radius);
                    margin-top: 15px;
                }}
                
                .alternatives ul {{
                    list-style-type: none;
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    margin-top: 10px;
                }}
                
                .alternatives li {{
                    background-color: white;
                    border: 1px solid var(--border-color);
                    border-radius: 20px;
                    padding: 5px 12px;
                }}
                
                .evidence {{
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-size: 0.8rem;
                    font-weight: 600;
                    background-color: var(--primary-light);
                    color: var(--primary-color);
                }}
                
                .source {{
                    font-size: 0.9rem;
                    color: var(--text-light);
                    margin-top: 5px;
                }}
                
                footer {{
                    margin-top: 40px;
                    border-top: 1px solid var(--border-color);
                    padding-top: 20px;
                    font-size: 0.9rem;
                    color: var(--text-light);
                    text-align: center;
                }}
                
                @media (max-width: 768px) {{
                    .container {{
                        padding: 15px;
                    }}
                    
                    .header {{
                        flex-direction: column;
                        align-items: flex-start;
                    }}
                    
                    .header-right {{
                        text-align: left;
                        margin-top: 10px;
                    }}
                    
                    .overview ul {{
                        flex-direction: column;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="header-left">
                        <h1>Pharmacogenomics Report</h1>
                        <p>Personalized genetic analysis for medication response</p>
                    </div>
                    <div class="header-right">
                        <p>Generated on: {report_data["date"]}</p>
                    </div>
                </div>
                
                <div class="overview">
                    <h2>Overview</h2>
                    <p>This report provides information about potential drug-gene interactions for the following medications:</p>
                    <ul>
        """
        
        # Add drugs to overview
        for drug in report_data["drugs"]:
            interactions = report_data["interactions_by_drug"].get(drug, [])
            html += f'<li><span class="drug-badge">{drug}</span> {len(interactions)} interactions found</li>'
        
        html += """
                    </ul>
                </div>
        """
        
        # Add drug sections
        for drug in report_data["drugs"]:
            interactions = report_data["interactions_by_drug"].get(drug, [])
            
            html += f"""
                <div class="drug-section">
                    <div class="drug-header">
                        <h2>{drug}</h2>
                    </div>
                    <div class="drug-content">
            """
            
            if not interactions:
                html += "<p>No known pharmacogenomic interactions found for this drug.</p>"
            else:
                html += f"<p>Found {len(interactions)} pharmacogenomic interactions that may affect treatment response.</p>"
                
                for interaction in interactions:
                    # Determine risk level based on evidence level
                    risk_class = "risk-medium"
                    if interaction["evidence_level"] and interaction["evidence_level"].lower() in ["1a", "1b", "a", "b", "1"]:
                        risk_class = "risk-high"
                    elif interaction["evidence_level"] and interaction["evidence_level"].lower() in ["3", "4", "c", "d"]:
                        risk_class = "risk-low"
                    
                    html += f"""
                    <div class="interaction {risk_class}">
                        <h3>{drug} - <span class="gene-name">{interaction["gene"]}</span> Interaction</h3>
                        
                        <div class="summary">
                            {interaction["summary"]}
                        </div>
                        
                        <div class="details">
                            <p><strong>Phenotype:</strong> {interaction["phenotype"]}</p>
                            <p><strong>Evidence Level:</strong> <span class="evidence">{interaction["evidence_level"]}</span></p>
                            <p class="source"><strong>Source:</strong> {interaction["source"]}</p>
                        </div>
                        
                        <div class="section-title">Risk Assessment</div>
                        <p>{interaction["risk_assessment"]}</p>
                        
                        <div class="section-title">Mechanism</div>
                        <p>{interaction["mechanism"]}</p>
                    """
                    
                    if interaction["alternatives"]:
                        html += """
                        <div class="alternatives">
                            <h4>Alternative Medications</h4>
                            <ul>
                        """
                        
                        for alternative in interaction["alternatives"]:
                            html += f"<li>{alternative}</li>"
                        
                        html += """
                            </ul>
                        </div>
                        """
                    
                    html += """
                    </div>
                    """
            
            html += """
                    </div>
                </div>
            """
        
        html += """
                <footer>
                    <p>This report is for informational purposes only and should be reviewed by a healthcare professional.</p>
                    <p>Generated by the Pharmacogenomics Engine &copy; 2025</p>
                </footer>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _html_to_pdf(self, html_content: str, output_path: Path) -> str:
        """
        Convert HTML content to PDF.
        
        Args:
            html_content: HTML content as a string.
            output_path: Output file path.
            
        Returns:
            Path to the generated PDF.
        """
        try:
            # Try to import weasyprint
            import weasyprint
            
            # Ensure output path has .pdf extension
            pdf_path = output_path.with_suffix(".pdf")
            
            # Convert HTML to PDF
            weasyprint.HTML(string=html_content).write_pdf(pdf_path)
            
            return str(pdf_path)
            
        except ImportError:
            # Fall back to pdfkit if weasyprint is not available
            try:
                import pdfkit
                
                # Ensure output path has .pdf extension
                pdf_path = output_path.with_suffix(".pdf")
                
                # Convert HTML to PDF
                pdfkit.from_string(html_content, pdf_path)
                
                return str(pdf_path)
                
            except ImportError:
                logger.error("Neither weasyprint nor pdfkit is available. Falling back to HTML output.")
                
                # Save as HTML instead
                html_path = output_path.with_suffix(".html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                return str(html_path)
    
    def _ensure_default_template(self):
        """Ensure that the default HTML template exists."""
        template_path = self.template_dir / "report_template.html"
        
        if not template_path.exists():
            logger.info("Creating default HTML template")
            
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(self._get_default_template())
    
    def _get_default_template(self) -> str:
        """
        Get the default HTML template.
        
        Returns:
            Default template as a string.
        """
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pharmacogenomics Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }
        
        .report-date {
            color: #666;
            font-style: italic;
        }
        
        .summary-box {
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        
        .drug-card {
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 20px;
            overflow: hidden;
        }
        
        .drug-header {
            padding: 10px 15px;
            background-color: #f5f5f5;
            border-bottom: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .drug-name {
            font-size: 1.2em;
            font-weight: bold;
        }
        
        .risk-badge {
            padding: 5px 10px;
            border-radius: 15px;
            font-weight: bold;
            font-size: 0.8em;
            color: white;
        }
        
        .risk-high {
            background-color: #d9534f;
        }
        
        .risk-medium {
            background-color: #f0ad4e;
        }
        
        .risk-low {
            background-color: #5cb85c;
        }
        
        .drug-body {
            padding: 15px;
        }
        
        .interaction {
            border-left: 3px solid #007bff;
            padding-left: 15px;
            margin-bottom: 20px;
        }
        
        .gene-name {
            font-weight: bold;
            color: #007bff;
        }
        
        .section-title {
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
            margin-top: 20px;
        }
        
        .alternatives {
            background-color: #f0f7ff;
            padding: 10px;
            border-radius: 5px;
        }
        
        .references {
            font-size: 0.9em;
            color: #666;
        }
        
        .reference-link {
            color: #007bff;
            text-decoration: none;
        }
        
        .reference-link:hover {
            text-decoration: underline;
        }
        
        .footer {
            margin-top: 40px;
            text-align: center;
            font-size: 0.9em;
            color: #666;
            border-top: 1px solid #eee;
            padding-top: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Personalized Pharmacogenomics Report</h1>
        <p class="report-date">Generated on: {{ report_date }}</p>
    </div>
    
    <div class="summary-box">
        <h2>Report Summary</h2>
        <p>This report analyzes {{ total_variants }} genetic variants across {{ drugs|length }} pharmacogenes and their interactions with {{ drugs|length }} prescribed medications.</p>
        <p>A total of {{ total_interactions }} drug-gene interactions were identified that may affect medication response.</p>
    </div>
    
    <h2>Drug Interaction Analysis</h2>
    
    {% for drug_summary in drug_summaries %}
    <div class="drug-card">
        <div class="drug-header">
            <span class="drug-name">{{ drug_summary.drug }}</span>
            <span class="risk-badge risk-{{ drug_summary.risk_level|lower }}">{{ drug_summary.risk_level }} Risk</span>
        </div>
        <div class="drug-body">
            <p>{{ drug_summary.summary }}</p>
            
            {% if drug_summary.interactions %}
                {% for interaction in drug_summary.interactions %}
                <div class="interaction">
                    <h3><span class="gene-name">{{ interaction.gene }}</span> Interaction</h3>
                    
                    {% if interaction.phenotype %}
                    <p><strong>Phenotype:</strong> {{ interaction.phenotype }}</p>
                    {% endif %}
                    
                    {% if interaction.source %}
                    <h4 class="section-title">Source</h4>
                    <p>{{ interaction.source }}</p>
                    {% endif %}
                    
                    {% if interaction.evidence_level %}
                    <h4 class="section-title">Evidence Level</h4>
                    <p>{{ interaction.evidence_level }}</p>
                    {% endif %}
                    
                    {% if interaction.recommendation %}
                    <h4 class="section-title">Recommendation</h4>
                    <p>{{ interaction.recommendation }}</p>
                    {% endif %}
                    
                    {% if interaction.literature_refs %}
                    <h4 class="section-title">References</h4>
                    <div class="references">
                        <ul>
                            {% for ref in interaction.literature_refs %}
                            <li>
                                {% if ref.startswith('http') %}
                                <a href="{{ ref }}" class="reference-link" target="_blank">{{ ref }}</a>
                                {% else %}
                                {{ ref }}
                                {% endif %}
                            </li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                </div>
                {% endfor %}
            {% else %}
                <p>No specific gene interactions found for this medication.</p>
            {% endif %}
        </div>
    </div>
    {% endfor %}
    
    <div class="footer">
        <p>This report is based on current pharmacogenomic knowledge and should be interpreted by a healthcare professional.</p>
        <p>Data sources: PharmGKB, CPIC, DGIdb, and other public pharmacogenomic databases.</p>
    </div>
</body>
</html>
""" 
