from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
import os
import json
import tempfile
import subprocess
from pathlib import Path
import logging
from datetime import datetime
import uuid
import threading
import time
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'vcf', 'gz'}

# Configuration for large file uploads
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB max file size
app.config['UPLOAD_TIMEOUT'] = 600  # 10 minutes timeout

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Store analysis jobs in memory (in production, use a database)
analysis_jobs = {}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS or \
           filename.endswith('.vcf.gz')

# Serve frontend files
@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:filename>')
def serve_frontend(filename):
    return send_from_directory('frontend', filename)

# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/upload-vcf', methods=['POST'])
def upload_vcf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # Basic VCF validation
            try:
                with open(filepath, 'r') as f:
                    first_line = f.readline()
                    if not first_line.startswith('##fileformat=VCF'):
                        return jsonify({'error': 'Invalid VCF file format'}), 400
            except Exception as e:
                return jsonify({'error': f'Error reading VCF file: {str(e)}'}), 400
            
            return jsonify({
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'size': os.path.getsize(filepath)
            })
        else:
            return jsonify({'error': 'Invalid file type. Please upload a VCF file.'}), 400
    
    except Exception as e:
        logger.error(f"Error uploading VCF file: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/drugs', methods=['GET'])
def get_drugs():
    """Get available drugs for analysis"""
    # This could be loaded from a database or configuration file
    drugs = [
        {
            'id': 'warfarin',
            'name': 'Warfarin',
            'generic': 'warfarin sodium',
            'category': 'cardiovascular',
            'description': 'Anticoagulant medication used to prevent blood clots',
            'genes': ['CYP2C9', 'VKORC1', 'CYP4F2'],
            'evidenceLevel': 'high'
        },
        {
            'id': 'simvastatin',
            'name': 'Simvastatin',
            'generic': 'simvastatin',
            'category': 'cardiovascular',
            'description': 'Statin medication used to lower cholesterol',
            'genes': ['SLCO1B1', 'CYP3A4'],
            'evidenceLevel': 'high'
        },
        {
            'id': 'clopidogrel',
            'name': 'Clopidogrel',
            'generic': 'clopidogrel bisulfate',
            'category': 'cardiovascular',
            'description': 'Antiplatelet medication to prevent blood clots',
            'genes': ['CYP2C19'],
            'evidenceLevel': 'high'
        },
        {
            'id': 'tamoxifen',
            'name': 'Tamoxifen',
            'generic': 'tamoxifen citrate',
            'category': 'oncology',
            'description': 'Selective estrogen receptor modulator for breast cancer',
            'genes': ['CYP2D6'],
            'evidenceLevel': 'high'
        },
        {
            'id': 'codeine',
            'name': 'Codeine',
            'generic': 'codeine phosphate',
            'category': 'pain',
            'description': 'Opioid pain medication and cough suppressant',
            'genes': ['CYP2D6'],
            'evidenceLevel': 'high'
        },
        {
            'id': 'omeprazole',
            'name': 'Omeprazole',
            'generic': 'omeprazole',
            'category': 'other',
            'description': 'Proton pump inhibitor for acid reflux',
            'genes': ['CYP2C19'],
            'evidenceLevel': 'medium'
        },
        {
            'id': 'fluoxetine',
            'name': 'Fluoxetine',
            'generic': 'fluoxetine hydrochloride',
            'category': 'psychiatric',
            'description': 'SSRI antidepressant medication',
            'genes': ['CYP2D6', 'CYP2C9'],
            'evidenceLevel': 'medium'
        },
        {
            'id': 'haloperidol',
            'name': 'Haloperidol',
            'generic': 'haloperidol',
            'category': 'psychiatric',
            'description': 'Typical antipsychotic medication',
            'genes': ['CYP2D6'],
            'evidenceLevel': 'medium'
        },
        {
            'id': 'metformin',
            'name': 'Metformin',
            'generic': 'metformin hydrochloride',
            'category': 'other',
            'description': 'Diabetes medication to control blood sugar',
            'genes': ['SLC22A1', 'SLC22A2'],
            'evidenceLevel': 'low'
        },
        {
            'id': 'ibuprofen',
            'name': 'Ibuprofen',
            'generic': 'ibuprofen',
            'category': 'pain',
            'description': 'NSAID for pain and inflammation',
            'genes': ['CYP2C9'],
            'evidenceLevel': 'low'
        }
    ]
    
    return jsonify({'drugs': drugs})

@app.route('/api/start-analysis', methods=['POST'])
def start_analysis():
    """Start a new pharmacogenomics analysis"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['vcf_file', 'drugs', 'patient_info']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create job record
        job = {
            'id': job_id,
            'status': 'queued',
            'progress': 0,
            'created_at': datetime.now().isoformat(),
            'vcf_file': data['vcf_file'],
            'drugs': data['drugs'],
            'drug_details': data.get('drug_details', []),
            'patient_info': data['patient_info'],
            'config': data.get('config', {}),
            'result': None,
            'error': None
        }
        
        analysis_jobs[job_id] = job
        
        # Start analysis in background thread
        thread = threading.Thread(target=run_analysis_job, args=(job_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': 'queued'
        })
    
    except Exception as e:
        logger.error(f"Error starting analysis: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/analysis-status/<job_id>', methods=['GET'])
def get_analysis_status(job_id):
    """Get the status of an analysis job"""
    if job_id not in analysis_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = analysis_jobs[job_id]
    return jsonify({
        'id': job['id'],
        'status': job['status'],
        'progress': job['progress'],
        'created_at': job['created_at'],
        'result': job['result'],
        'error': job['error']
    })

@app.route('/api/reports', methods=['GET'])
def get_reports():
    """Get all completed analysis reports"""
    completed_jobs = [
        {
            'id': job['id'],
            'patient_info': job['patient_info'],
            'drugs': job['drugs'],
            'created_at': job['created_at'],
            'status': job['status'],
            'result': job['result']
        }
        for job in analysis_jobs.values()
        if job['status'] == 'completed'
    ]
    
    return jsonify({'reports': completed_jobs})

@app.route('/api/report/<job_id>', methods=['GET'])
def get_report(job_id):
    """Get a specific report"""
    if job_id not in analysis_jobs:
        return jsonify({'error': 'Report not found'}), 404
    
    job = analysis_jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Analysis not completed'}), 400
    
    return jsonify(job)

@app.route('/api/report/<job_id>/download', methods=['GET'])
def download_report(job_id):
    """Download report as HTML file"""
    if job_id not in analysis_jobs:
        return jsonify({'error': 'Report not found'}), 404
    
    job = analysis_jobs[job_id]
    if job['status'] != 'completed' or not job['result']:
        return jsonify({'error': 'Report not available'}), 400
    
    # Check if HTML file exists
    html_file = job['result'].get('html_file')
    if html_file and os.path.exists(html_file):
        return send_from_directory(
            os.path.dirname(html_file),
            os.path.basename(html_file),
            as_attachment=True,
            download_name=f"pharmacogenomics_report_{job_id}.html"
        )
    else:
        return jsonify({'error': 'Report file not found'}), 404

@app.route('/api/report/<job_id>/view', methods=['GET'])
def view_report(job_id):
    """View report HTML content directly"""
    if job_id not in analysis_jobs:
        return jsonify({'error': 'Report not found'}), 404
    
    job = analysis_jobs[job_id]
    if job['status'] != 'completed' or not job['result']:
        return jsonify({'error': 'Report not available'}), 400
    
    # Check if HTML file exists
    html_file = job['result'].get('html_file')
    if html_file and os.path.exists(html_file):
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        except Exception as e:
            return jsonify({'error': f'Error reading report file: {str(e)}'}), 500
    else:
        return jsonify({'error': 'Report file not found'}), 404

def run_analysis_job(job_id):
    """Run the pharmacogenomics analysis in background"""
    try:
        job = analysis_jobs[job_id]
        job['status'] = 'running'
        job['progress'] = 10
        
        # Prepare command arguments
        vcf_file = job['vcf_file']
        
        # Use drug names from drug_details if available, otherwise fall back to drug IDs
        drug_details = job.get('drug_details', [])
        logger.info(f"DEBUG: drug_details for job {job_id}: {drug_details}")
        
        if drug_details:
            # Create a mapping of drug IDs to names
            drug_id_to_name = {detail['id']: detail['name'] for detail in drug_details}
            logger.info(f"DEBUG: drug_id_to_name mapping: {drug_id_to_name}")
            # Use drug names for the command
            drug_names = [drug_id_to_name.get(drug_id, drug_id) for drug_id in job['drugs']]
            drugs = ','.join(drug_names)
            logger.info(f"DEBUG: Using drug names: {drug_names}")
        else:
            # Fallback to using drug IDs directly
            drugs = ','.join(job['drugs'])
            logger.info(f"DEBUG: No drug_details found, using drug IDs: {job['drugs']}")
        
        patient_id = job['patient_info'].get('id', 'unknown')
        
        # Create output filename
        output_file = os.path.join(OUTPUT_FOLDER, f"report_{job_id}.html")
        
        # Build command
        cmd = [
            'python3', 'main.py',
            '--vcf', vcf_file,
            '--drugs', drugs,
            '--output', output_file,
            '--patient-id', patient_id
        ]
        
        # Add optional parameters
        config = job.get('config', {})
        # Always use Cohere AI - remove the --no-cohere flag logic
        # if not config.get('useCohere', True):
        #     cmd.append('--no-cohere')
        
        if config.get('detailedAnalysis', True):
            cmd.append('--verbose')
        
        job['progress'] = 30
        
        # Run the analysis
        logger.info(f"Starting analysis for job {job_id}: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        job['progress'] = 80
        
        if result.returncode == 0:
            # Analysis completed successfully
            job['status'] = 'completed'
            job['progress'] = 100
            job['result'] = {
                'html_file': output_file,
                'stdout': result.stdout,
                'analysis_summary': parse_analysis_output(result.stdout)
            }
            logger.info(f"Analysis completed successfully for job {job_id}")
        else:
            # Analysis failed
            job['status'] = 'failed'
            job['error'] = result.stderr or 'Analysis failed with unknown error'
            logger.error(f"Analysis failed for job {job_id}: {job['error']}")
            
    except subprocess.TimeoutExpired:
        job['status'] = 'failed'
        job['error'] = 'Analysis timed out after 5 minutes'
        logger.error(f"Analysis timed out for job {job_id}")
    except Exception as e:
        job['status'] = 'failed'
        job['error'] = str(e)
        logger.error(f"Error in analysis job {job_id}: {str(e)}")

def parse_analysis_output(stdout):
    """Parse analysis output to extract summary information"""
    summary = {
        'variants_processed': 0,
        'drugs_analyzed': 0,
        'interactions_found': 0,
        'high_risk_interactions': 0
    }
    
    # Simple parsing - in production, this would be more sophisticated
    lines = stdout.split('\n')
    for line in lines:
        if 'variants processed' in line.lower():
            try:
                summary['variants_processed'] = int(line.split()[-1])
            except:
                pass
        elif 'drugs analyzed' in line.lower():
            try:
                summary['drugs_analyzed'] = int(line.split()[-1])
            except:
                pass
    
    return summary

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )
    
    # Get configuration from environment
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting PharmGenome application on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Upload folder: {UPLOAD_FOLDER}")
    logger.info(f"Output folder: {OUTPUT_FOLDER}")
    
    # Run the application
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    ) 
