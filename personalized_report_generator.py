#!/usr/bin/env python3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from personalized_analyzer import PersonalizedDrugReport

logger = logging.getLogger(__name__)

class PersonalizedReportGenerator:
    """Generates comprehensive personalized pharmacogenomics reports."""
    
    def __init__(self):
        """Initialize the personalized report generator."""
        pass
    
    def generate_comprehensive_report(
        self,
        personalized_reports: Dict[str, PersonalizedDrugReport],
        patient_id: str,
        output_path: Path,
        format: str = "html"
    ) -> str:
        logger.info(f"Generating comprehensive personalized {format} report for {len(personalized_reports)} drugs")
        
        # Generate HTML content
        html_content = self._render_personalized_html(personalized_reports, patient_id)
        
        if format.lower() == "pdf":
            # Convert HTML to PDF (implement if needed)
            logger.warning("PDF generation not implemented yet, generating HTML instead")
        
        # Save as HTML
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"Comprehensive personalized report generated: {output_path}")
        return str(output_path)
    
    def _render_personalized_html(
        self, 
        personalized_reports: Dict[str, PersonalizedDrugReport],
        patient_id: str
    ) -> str:
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Personalized Pharmacogenomics Report - {patient_id}</title>
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
                    --border-radius: 12px;
                    --shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                    --shadow-lg: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
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
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: var(--bg-color);
                    border-radius: var(--border-radius);
                    box-shadow: var(--shadow-lg);
                    overflow: hidden;
                }}
                
                .header {{
                    background: linear-gradient(135deg, var(--primary-color) 0%, var(--accent-color) 100%);
                    color: white;
                    padding: 40px;
                    text-align: center;
                }}
                
                .header h1 {{
                    font-size: 2.5rem;
                    font-weight: 700;
                    margin-bottom: 10px;
                    color: white;
                }}
                
                .header p {{
                    font-size: 1.1rem;
                    opacity: 0.9;
                }}
                
                .content {{
                    padding: 40px;
                }}
                
                .overview {{
                    background: linear-gradient(135deg, var(--bg-light) 0%, #e0f2fe 100%);
                    border-radius: var(--border-radius);
                    padding: 30px;
                    margin-bottom: 40px;
                    border-left: 5px solid var(--primary-color);
                }}
                
                .overview h2 {{
                    color: var(--primary-color);
                    font-size: 1.8rem;
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                }}
                
                .overview-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                }}
                
                .overview-item {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: var(--shadow);
                }}
                
                .overview-item h3 {{
                    color: var(--secondary-color);
                    font-size: 0.9rem;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin-bottom: 10px;
                }}
                
                .overview-item .value {{
                    font-size: 1.5rem;
                    font-weight: 600;
                    color: var(--primary-color);
                }}
                
                .drug-section {{
                    margin-bottom: 50px;
                    background: white;
                    border-radius: var(--border-radius);
                    box-shadow: var(--shadow);
                    overflow: hidden;
                }}
                
                .drug-header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 25px 30px;
                    border-bottom: 3px solid var(--primary-color);
                }}
                
                .drug-header h2 {{
                    font-size: 1.8rem;
                    margin-bottom: 10px;
                    color: white;
                }}
                
                .confidence-badge {{
                    display: inline-block;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 0.8rem;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                
                .confidence-high {{
                    background-color: var(--success-color);
                    color: white;
                }}
                
                .confidence-medium {{
                    background-color: var(--warning-color);
                    color: white;
                }}
                
                .confidence-low {{
                    background-color: var(--danger-color);
                    color: white;
                }}
                
                .ai-badge {{
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-size: 0.7rem;
                    font-weight: 500;
                    background: linear-gradient(135deg, #8b5cf6, #ec4899);
                    color: white;
                    margin-left: 10px;
                }}
                
                .drug-content {{
                    padding: 30px;
                }}
                
                .analysis-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 25px;
                    margin-bottom: 30px;
                }}
                
                .analysis-card {{
                    background: var(--bg-light);
                    border-radius: 10px;
                    padding: 25px;
                    border-left: 4px solid var(--primary-color);
                    transition: transform 0.2s ease, box-shadow 0.2s ease;
                }}
                
                .analysis-card:hover {{
                    transform: translateY(-2px);
                    box-shadow: var(--shadow);
                }}
                
                .analysis-card h3 {{
                    color: var(--primary-color);
                    font-size: 1.2rem;
                    margin-bottom: 15px;
                    display: flex;
                    align-items: center;
                }}
                
                .analysis-card .icon {{
                    width: 24px;
                    height: 24px;
                    margin-right: 10px;
                    opacity: 0.8;
                }}
                
                .analysis-text {{
                    color: var(--text-color);
                    line-height: 1.7;
                }}
                
                .biomedlm-section {{
                    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                    border-radius: 12px;
                    padding: 25px;
                    margin: 25px 0;
                    border-left: 4px solid #f59e0b;
                    box-shadow: var(--shadow);
                }}
                
                .biomedlm-section h3 {{
                    color: #92400e;
                    margin-bottom: 20px;
                    font-size: 1.3rem;
                    display: flex;
                    align-items: center;
                }}
                
                .biomedlm-content {{
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                }}
                
                .biomedlm-summary {{
                    margin-bottom: 20px;
                    padding-bottom: 15px;
                    border-bottom: 1px solid #fbbf24;
                }}
                
                .biomedlm-summary h4 {{
                    color: #92400e;
                    margin-bottom: 10px;
                    font-size: 1.1rem;
                }}
                
                .biomedlm-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                }}
                
                .biomedlm-item {{
                    background: #fffbeb;
                    padding: 15px;
                    border-radius: 6px;
                    border-left: 3px solid #f59e0b;
                }}
                
                .biomedlm-item h5 {{
                    color: #92400e;
                    margin-bottom: 8px;
                    font-size: 0.95rem;
                    font-weight: 600;
                }}
                
                .biomedlm-item p {{
                    color: var(--text-color);
                    font-size: 0.9rem;
                    line-height: 1.6;
                }}
                
                .biomedlm-recommendations {{
                    background: #fef3c7;
                    padding: 15px;
                    border-radius: 8px;
                    border: 1px solid #fbbf24;
                }}
                
                .biomedlm-recommendations h5 {{
                    color: #92400e;
                    margin-bottom: 10px;
                    font-size: 1rem;
                    font-weight: 600;
                }}
                
                .biomedlm-recommendations ul {{
                    list-style-type: none;
                    padding: 0;
                }}
                
                .biomedlm-recommendations li {{
                    color: var(--text-color);
                    font-size: 0.9rem;
                    line-height: 1.6;
                    margin-bottom: 8px;
                    padding-left: 20px;
                    position: relative;
                }}
                
                .biomedlm-recommendations li:before {{
                    content: "🔹";
                    position: absolute;
                    left: 0;
                }}
                
                .alternatives-section {{
                    background: #f0f9ff;
                    border-radius: 10px;
                    padding: 25px;
                    margin-top: 25px;
                    border: 1px solid var(--primary-light);
                }}
                
                .alternatives-section h3 {{
                    color: var(--primary-color);
                    margin-bottom: 15px;
                }}
                
                .alternatives-list {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 10px;
                }}
                
                .alternative-item {{
                    background: white;
                    padding: 12px 16px;
                    border-radius: 6px;
                    border-left: 3px solid var(--accent-color);
                    font-weight: 500;
                }}
                
                .genetics-section {{
                    background: #fefce8;
                    border-radius: 10px;
                    padding: 25px;
                    margin-top: 25px;
                    border: 1px solid #fef08a;
                }}
                
                .genetics-section h3 {{
                    color: #a16207;
                    margin-bottom: 15px;
                }}
                
                .genetics-details {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 15px;
                }}
                
                .genetics-item {{
                    background: white;
                    padding: 15px;
                    border-radius: 6px;
                    border-left: 3px solid #eab308;
                }}
                
                .data-sources {{
                    margin-top: 30px;
                    padding: 20px;
                    background: #f1f5f9;
                    border-radius: 8px;
                    border-left: 4px solid var(--secondary-color);
                }}
                
                .data-sources h4 {{
                    color: var(--secondary-color);
                    margin-bottom: 10px;
                }}
                
                .sources-list {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                }}
                
                .source-tag {{
                    background: var(--secondary-color);
                    color: white;
                    padding: 4px 12px;
                    border-radius: 15px;
                    font-size: 0.8rem;
                    font-weight: 500;
                }}
                
                .footer {{
                    background: var(--bg-light);
                    padding: 30px;
                    text-align: center;
                    color: var(--text-light);
                    border-top: 1px solid var(--border-color);
                }}
                
                .disclaimer {{
                    background: #fef2f2;
                    border: 1px solid #fecaca;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 30px 0;
                    color: #991b1b;
                }}
                
                .disclaimer h4 {{
                    color: #991b1b;
                    margin-bottom: 10px;
                }}
                
                @media (max-width: 768px) {{
                    .analysis-grid {{
                        grid-template-columns: 1fr;
                    }}
                    
                    .overview-grid {{
                        grid-template-columns: 1fr;
                    }}
                    
                    .alternatives-list {{
                        grid-template-columns: 1fr;
                    }}
                    
                    .genetics-details {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧬 Personalized Pharmacogenomics Report</h1>
                    <p>Comprehensive Drug Analysis for Patient: {patient_id}</p>
                    <p>Generated on {current_date}</p>
                </div>
                
                <div class="content">
                    <div class="overview">
                        <h2>📊 Analysis Overview</h2>
                        <div class="overview-grid">
                            <div class="overview-item">
                                <h3>Drugs Analyzed</h3>
                                <div class="value">{len(personalized_reports)}</div>
                            </div>
                            <div class="overview-item">
                                <h3>Total Genes Considered</h3>
                                <div class="value">{self._count_total_genes(personalized_reports)}</div>
                            </div>
                            <div class="overview-item">
                                <h3>Data Sources</h3>
                                <div class="value">{len(self._get_all_sources(personalized_reports))}</div>
                            </div>
                            <div class="overview-item">
                                <h3>Analysis Quality</h3>
                                <div class="value">{self._calculate_overall_confidence(personalized_reports)}</div>
                            </div>
                        </div>
                    </div>
        """
        
        # Add individual drug sections
        for drug_name, report in personalized_reports.items():
            html += self._render_drug_section(drug_name, report)
        
        # Add disclaimer and footer
        html += f"""
                    <div class="disclaimer">
                        <h4>⚠️ Important Medical Disclaimer</h4>
                        <p>This pharmacogenomics report is for informational purposes only and should not replace professional medical advice. Always consult with your healthcare provider before making any changes to your medication regimen. Individual responses to medications can vary due to factors beyond genetics.</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Report generated using comprehensive pharmacogenomics databases (PharmGKB, CPIC) and AI-powered analysis.</p>
                    <p>For questions about this report, consult with your healthcare provider or a clinical pharmacist.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _render_drug_section(self, drug_name: str, report: PersonalizedDrugReport) -> str:
        """Render a comprehensive section for a single drug."""
        confidence_class = f"confidence-{report.confidence_level.lower()}"
        
        return f"""
        <div class="drug-section">
            <div class="drug-header">
                <h2>💊 {drug_name}</h2>
                <span class="confidence-badge {confidence_class}">
                    {report.confidence_level} Confidence
                </span>
                {' <span class="ai-badge">🤖 AI Analysis</span>' if 'AI' in str(report.data_sources) else ''}
            </div>
            
            <div class="drug-content">
                <div class="analysis-grid">
                    <div class="analysis-card">
                        <h3>🎯 Efficacy Prediction</h3>
                        <div class="analysis-text">{report.efficacy_prediction}</div>
                    </div>
                    
                    <div class="analysis-card">
                        <h3>⚠️ Risk Assessment</h3>
                        <div class="analysis-text">{report.risk_assessment}</div>
                    </div>
                    
                    <div class="analysis-card">
                        <h3>💉 Dosage Recommendation</h3>
                        <div class="analysis-text">{report.dosage_recommendation}</div>
                    </div>
                    
                    <div class="analysis-card">
                        <h3>🏥 Clinical Considerations</h3>
                        <div class="analysis-text">{report.clinical_considerations}</div>
                    </div>
                </div>
                
                <div class="genetics-section">
                    <h3>🧬 Genetic Impact Analysis</h3>
                    <div class="genetics-details">
                        <div class="genetics-item">
                            <strong>Pharmacokinetic Impact:</strong><br>
                            {report.pharmacokinetic_impact}
                        </div>
                        <div class="genetics-item">
                            <strong>Pharmacodynamic Impact:</strong><br>
                            {report.pharmacodynamic_impact}
                        </div>
                        <div class="genetics-item">
                            <strong>Monitoring Required:</strong><br>
                            {report.monitoring_recommendations}
                        </div>
                    </div>
                </div>
                
                {self._render_alternatives_section(report.alternative_medications)}
                
                {self._render_contraindications_section(report.contraindications)}
                
                <div class="data-sources">
                    <h4>📚 Data Sources</h4>
                    <div class="sources-list">
                        {' '.join([f'<span class="source-tag">{source}</span>' for source in report.data_sources])}
                    </div>
                    <p style="margin-top: 10px; font-size: 0.9rem; color: var(--text-light);">
                        Genes analyzed: {', '.join(report.genetic_variants_analyzed[:10])}
                        {' (+' + str(len(report.genetic_variants_analyzed) - 10) + ' more)' if len(report.genetic_variants_analyzed) > 10 else ''}
                    </p>
                </div>
            </div>
        </div>
        """
    
    def _render_alternatives_section(self, alternatives: List[str]) -> str:
        """Render the alternative medications section."""
        if not alternatives or (len(alternatives) == 1 and "consult" in alternatives[0].lower()):
            return ""
        
        alternatives_html = ""
        for alt in alternatives[:5]:  # Limit to 5 alternatives
            alternatives_html += f'<div class="alternative-item">{alt}</div>'
        
        return f"""
        <div class="alternatives-section">
            <h3>🔄 Alternative Medications</h3>
            <div class="alternatives-list">
                {alternatives_html}
            </div>
        </div>
        """
    
    def _render_contraindications_section(self, contraindications: List[str]) -> str:
        """Render the contraindications section."""
        if not contraindications or (len(contraindications) == 1 and "none" in contraindications[0].lower()):
            return ""
        
        contraindications_html = ""
        for contra in contraindications:
            contraindications_html += f'<div class="alternative-item" style="border-left-color: var(--danger-color);">{contra}</div>'
        
        return f"""
        <div class="alternatives-section" style="background: #fef2f2; border-color: #fecaca;">
            <h3 style="color: var(--danger-color);">🚫 Contraindications & Warnings</h3>
            <div class="alternatives-list">
                {contraindications_html}
            </div>
        </div>
        """
    
    def _count_total_genes(self, reports: Dict[str, PersonalizedDrugReport]) -> int:
        """Count total unique genes across all reports."""
        all_genes = set()
        for report in reports.values():
            all_genes.update(report.genetic_variants_analyzed)
        return len(all_genes)
    
    def _get_all_sources(self, reports: Dict[str, PersonalizedDrugReport]) -> set:
        """Get all unique data sources across reports."""
        all_sources = set()
        for report in reports.values():
            all_sources.update(report.data_sources)
        return all_sources
    
    def _calculate_overall_confidence(self, reports: Dict[str, PersonalizedDrugReport]) -> str:
        """Calculate overall confidence level."""
        confidence_scores = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        total_score = sum(confidence_scores.get(report.confidence_level, 1) for report in reports.values())
        avg_score = total_score / len(reports) if reports else 1
        
        if avg_score >= 2.5:
            return "HIGH"
        elif avg_score >= 1.5:
            return "MEDIUM"
        else:
            return "LOW" 
