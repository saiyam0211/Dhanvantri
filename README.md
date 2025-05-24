# Genetic Analysis Tool

A comprehensive tool for analyzing genetic variants from VCF files and identifying drug interactions based on pharmacogenomic data.

## Features

- Process VCF files to identify genetic variants
- Annotate variants using SnpEff
- Map variants to drugs using PharmGKB and CPIC data
- **NEW: PharmGKB API integration for real-time drug-gene interaction data**
- Generate interactive HTML reports for drug-gene interactions
- Support for batch processing of large VCF files
- Docker container for easy deployment

## Quick Start with Docker

The easiest way to run the tool is using the Docker container:

```bash
# Build the Docker image
docker build -t genetic-analysis .

# Run the tool with a sample VCF file and drug list
docker run -v /path/to/your/data:/app/data -v /path/to/output:/app/output genetic-analysis --vcf /app/data/sample.vcf --drugs "warfarin,clopidogrel" --output /app/output/report.html
```

On first run, the container will automatically download the required SnpEff database.

## Docker Volume Mounts

The Docker container uses two volume mounts:

1. `/app/data`: Mount your local data directory containing VCF files and reference data
2. `/app/output`: Mount a local directory to save the generated reports

Example:
```bash
docker run -v $(pwd)/samples:/app/data -v $(pwd)/results:/app/output genetic-analysis --vcf /app/data/sample.vcf --drugs "ibuprofen,omeprazole" --output /app/output/report.html
```

## Command-Line Options

```
--vcf VCF             Path to the VCF file
--drugs DRUGS         Comma-separated list of prescribed drugs
--output OUTPUT       Output file path (default: report.html)
--format {html,pdf}   Output format (default: html)
--api-keys API_KEYS   Path to JSON file containing API keys
--data-dir DATA_DIR   Path to directory containing PharmGKB and CPIC data
--verbose             Enable verbose logging
--limit LIMIT         Limit the number of variants to process
```

## API Keys

The tool supports integration with several external APIs. Create an `api_keys.json` file with your API keys:

```json
{
  "vep_api_key": "your_vep_api_key_here",
  "pharmgkb_api_key": "your_pharmgkb_api_key_here",
  "cpic_api_key": "your_cpic_api_key_here",
  "dgidb_api_key": "your_dgidb_api_key_here",
  "gemini_api_key": "your_gemini_api_key_here",
  "openai_api_key": "your_openai_api_key_here"
}
```

## PharmGKB API Integration

The tool now includes integration with the PharmGKB API to provide real-time drug-gene interaction data. This integration offers several benefits:

1. **Up-to-date information**: Access the latest drug-gene interaction data directly from PharmGKB
2. **Expanded search**: When no interactions are found in local data, the API can search for additional drug-related genes
3. **Comprehensive coverage**: Combines local data with API data for the most complete set of interactions

To use the PharmGKB API integration:

1. Obtain a PharmGKB API key from [PharmGKB](https://www.pharmgkb.org/)
2. Add your API key to the `api_keys.json` file
3. The tool will automatically use both local data and the API when mapping drugs to genes

## Data Sources

The tool integrates data from multiple pharmacogenomic databases:

- **PharmGKB**: Pharmacogenomics Knowledge Base
  - Local data files downloaded from PharmGKB
  - Real-time API integration for up-to-date drug-gene interactions
- **CPIC**: Clinical Pharmacogenetics Implementation Consortium
- **DGIdb**: Drug Gene Interaction Database
- **Custom**: User-defined interactions in `custom_interactions.json`

## Installation (Without Docker)

```bash
# Clone the repository
git clone https://github.com/yourusername/genetic-analysis.git
cd genetic-analysis

# Install dependencies
pip install -r requirements.txt

# Download required data files
python download_data.py
```

## Usage (Without Docker)

```bash
python main.py --vcf path/to/your/file.vcf --drugs "drug1,drug2,drug3" --output report.html
```

## Output

The tool generates an interactive HTML report (or PDF) containing:

- Summary of analyzed variants
- Drug-gene interactions with evidence levels
- Phenotype information and clinical recommendations
- AI-powered explanations of the interactions
- References to scientific literature

## Custom Interactions

You can define custom drug-gene interactions by creating a `custom_interactions.json` file in the data directory:

```json
[
  {
    "drug": "aspirin",
    "gene": "PTGS1",
    "phenotype": "Reduced antiplatelet effect",
    "evidence_level": "High",
    "recommendation": "Consider alternative antiplatelet therapy"
  }
]
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.