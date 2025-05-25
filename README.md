# Dhanvantri - Personalized Pharmacogenomics Analysis Platform

> **Hackathon Project** - A comprehensive web-based platform for pharmacogenomics analysis that processes genetic data and provides personalized drug recommendations.

## 🌟 Live Demo

**Try it now:** [Deployed on GCP](http://34.131.137.107:8000/)

Experience our platform with real genetic data! No setup required - just visit the link above and start exploring.

## 🧬 Test Data

We've provided a real DNA VCF file for testing purposes:

**Download Test VCF File:** [Sample DNA Data (50K variants)](https://drive.google.com/file/d/1YEvQqWT3brWGAOO6OG46VwdjVk295-AS/view?usp=sharing)

> **Note:** This is a real DNA file from an individual containing 50,000 genetic variants - a subset of a complete genomic profile. Perfect for testing our analysis capabilities!

## 🎯 What is Dhanvantri?

Dhanvantri is a cutting-edge pharmacogenomics platform that analyzes your genetic makeup to provide personalized medication recommendations. By examining genetic variants in your DNA, we can predict how you might respond to different medications, helping healthcare providers make more informed treatment decisions.

### Key Features

- **🧬 Genetic Analysis**: Upload VCF files containing genetic variant data
- **💊 Drug Database**: Comprehensive database of 100+ medications across multiple categories
- **🤖 AI-Powered Insights**: Advanced AI analysis using multiple language models
- **📊 Interactive Dashboard**: Real-time progress tracking and beautiful visualizations
- **📋 Detailed Reports**: Comprehensive, patient-friendly analysis reports

## 🚀 How to Use

### Step 1: Access the Platform
Visit our live demo at [Deployed on GCP](http://34.131.137.107:8000/)

### Step 2: Download Test Data
Get our sample VCF file from [this Google Drive link](https://drive.google.com/file/d/1YEvQqWT3brWGAOO6OG46VwdjVk295-AS/view?usp=sharing)

### Step 3: Start New Analysis
1. Click "New Analysis" on the dashboard
2. Enter patient information (you can use test data)
3. Upload the downloaded VCF file
4. Select medications from our drug database or manually enter your own!
5. Configure analysis options ( Don't Change any! )
6. Start the analysis and watch real-time progress
7. You will be redirected to Reports Page.
8. Click on "View Full Report" on your analysis.

### Step 4: View Results
- Monitor analysis progress in real-time
- Access detailed pharmacogenomics reports
- Download comprehensive analysis summaries

## 🏗️ Technical Architecture

```
Frontend (HTML/CSS/JS) → Flask API → Python Analysis Engine
                                  ↓
                              AI Services (Cohere)
                                  ↓
                              Report Generation
```

### Core Components

- **Frontend**: Modern, responsive web interface
- **Backend**: Flask-based REST API
- **Analysis Engine**: Python-based genetic variant processor
- **AI Integration**: AI models for enhanced analysis
- **Report Generator**: Automated HTML report creation

## 🧪 Supported Drug Categories

- **Any**

## 📊 Sample Analysis Results

Our platform provides:

- **Risk Assessment**: High/Medium/Low risk classifications
- **Dosing Recommendations**: Personalized dosing guidelines
- **Alternative Medications**: Safer drug alternatives when needed
- **Scientific References**: Evidence-based recommendations
- **Patient-Friendly Summaries**: Easy-to-understand explanations

## 🔗 API Endpoints

Our platform exposes several REST API endpoints:

- `GET /api/health` - System health check
- `POST /api/upload-vcf` - Upload genetic data files
- `GET /api/drugs` - Retrieve drug database
- `POST /api/start-analysis` - Initiate analysis
- `GET /api/analysis-status/<job_id>` - Check progress
- `GET /api/reports` - List all reports
- `GET /api/report/<job_id>/download` - Download results

## 🌐 Browser Compatibility

- Chrome (recommended)
- Firefox
- Safari 
- Edge

## 🤝 Team

Saiyam Kumar: [Vibe coder](http://github.com/saiyam0211)
Janvi Yadav: [Silent coder](http://github.com/janvi1205)
Ronak Jain: [Owl coder](http://github.com/reachronakofficial756)
Abhinav Jain: [Buisness boy](http://github.com/rikii08)

## 🔮 Future Enhancements

- Integration with more genetic databases
- Enhanced AI analysis capabilities
- Use of BioMedLM for more accurate reports
- Mobile application development
- Clinical decision support tools
- Clinical & Govt. Approval
- 
---

**Ready to explore personalized medicine?** 
Visit [Deployed on GCP](http://34.131.137.107:8000/) and start your genetic analysis journey today!
