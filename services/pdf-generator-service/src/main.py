import os
import json
import logging
import threading
import time
from flask import Flask, request, jsonify, send_file
from google.cloud import firestore, storage, pubsub_v1
from pdf_generator import PDFGenerator
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize services
try:
    firestore_client = firestore.Client()
    storage_client = storage.Client()
    subscriber = pubsub_v1.SubscriberClient()
    pdf_generator = PDFGenerator(firestore_client, storage_client)
    logger.info("✅ All services initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize services: {e}")
    raise

# Configuration
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
SUBSCRIPTION_NAME = 'pdf-generation-subscription'
STORAGE_BUCKET = os.environ.get('STORAGE_BUCKET', 'legal-case-documents')
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '3'))

# Global variables
shutdown_event = threading.Event()
active_jobs = set()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'pdf-generator-service',
        'version': '1.0.0',
        'timestamp': time.time(),
        'active_jobs': len(active_jobs),
        'max_workers': MAX_WORKERS
    }), 200

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint"""
    try:
        # Test connections
        firestore_client.collection('test').limit(1).get()
        storage_client.bucket(STORAGE_BUCKET).exists()
        
        return jsonify({
            'status': 'ready',
            'timestamp': time.time()
        }), 200
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': time.time()
        }), 503

@app.route('/generate', methods=['POST'])
def generate_pdf():
    """Direct API endpoint for PDF generation"""
    try:
        data = request.json
        case_id = data.get('caseId')
        report_type = data.get('type', 'case_analysis')
        user_id = data.get('userId')
        
        if not case_id or not user_id:
            return jsonify({'error': 'caseId and userId are required'}), 400
        
        # Generate PDF
        result = pdf_generator.generate_report(case_id, report_type, user_id)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'data': result,
                'timestamp': time.time()
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'PDF generation failed'),
                'timestamp': time.time()
            }), 500
        
    except Exception as e:
        logger.error(f"Direct PDF generation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/download/<report_id>', methods=['GET'])
def download_pdf(report_id):
    """Download generated PDF report"""
    try:
        # Get report info from Firestore
        report_ref = firestore_client.collection('pdf_reports').document(report_id)
        report_doc = report_ref.get()
        
        if not report_doc.exists:
            return jsonify({'error': 'Report not found'}), 404
        
        report_data = report_doc.to_dict()
        storage_key = report_data.get('storageKey')
        filename = report_data.get('filename', 'report.pdf')
        
        if not storage_key:
            return jsonify({'error': 'Report file not available'}), 404
        
        # Download from Cloud Storage
        bucket = storage_client.bucket(STORAGE_BUCKET)
        blob = bucket.blob(storage_key)
        
        if not blob.exists():
            return jsonify({'error': 'Report file not found in storage'}), 404
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            blob.download_to_filename(temp_file.name)
            
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        
    except Exception as e:
        logger.error(f"PDF download error: {e}")
        return jsonify({'error': 'Failed to download PDF'}), 500

def process_pdf_generation_message(message):
    """Process PDF generation message from Pub/Sub"""
    job_id = None
    try:
        data = json.loads(message.data.decode('utf-8'))
        case_id = data.get('caseId')
        user_id = data.get('userId')
        report_type = data.get('reportType', 'case_analysis')
        
        if not case_id or not user_id:
            logger.error("Missing required fields in PDF generation message")
            message.nack()
            return
        
        job_id = f"pdf_{case_id}_{report_type}_{int(time.time())}"
        active_jobs.add(job_id)
        
        logger.info(f"📄 Starting PDF generation job {job_id}")
        
        # Generate PDF
        result = pdf_generator.generate_report(case_id, report_type, user_id)
        
        if result.get('success'):
            logger.info(f"✅ PDF generation completed: {job_id}")
            message.ack()
        else:
            logger.error(f"❌ PDF generation failed: {job_id} - {result.get('error')}")
            message.nack()
        
    except Exception as e:
        logger.error(f"❌ PDF generation error for job {job_id}: {str(e)}")
        message.nack()
    
    finally:
        if job_id:
            active_jobs.discard(job_id)

def start_subscriber():
    """Start Pub/Sub subscriber"""
    if not PROJECT_ID:
        logger.error("❌ GOOGLE_CLOUD_PROJECT environment variable not set")
        return
    
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)
    flow_control = pubsub_v1.types.FlowControl(max_messages=MAX_WORKERS)
    
    logger.info(f"🔄 Starting subscriber: {subscription_path}")
    
    try:
        subscriber.subscribe(
            subscription_path,
            callback=process_pdf_generation_message,
            flow_control=flow_control
        )
        
        while not shutdown_event.is_set():
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"❌ Subscriber error: {e}")
        raise

if __name__ == '__main__':
    logger.info("🚀 Starting PDF Generator Service")
    logger.info(f"📅 Started at: {time.ctime()}")
    logger.info(f"🌐 Project ID: {PROJECT_ID}")
    logger.info(f"💾 Storage Bucket: {STORAGE_BUCKET}")
    
    # Start subscriber in background
    subscriber_thread = threading.Thread(target=start_subscriber, daemon=True)
    subscriber_thread.start()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)