#services/document-analysis-service/src/main.py
import os
import json
import logging
import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS 
from google.cloud import pubsub_v1, firestore
from analyzer import DocumentAnalyzer
from gemini_client import GeminiClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000"]}}, supports_credentials=True)  # ✅ add this
# Initialize clients
try:
    firestore_client = firestore.Client()
    subscriber = pubsub_v1.SubscriberClient()
    gemini_client = GeminiClient()
    analyzer = DocumentAnalyzer(gemini_client, firestore_client)
    logger.info("✅ All clients initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize clients: {e}")
    raise

# Configuration
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
SUBSCRIPTION_NAME = os.environ.get('SUBSCRIPTION_NAME')
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '3'))

# Global variables
shutdown_event = threading.Event()
active_jobs = set()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'document-analysis-service',
        'version': '1.0.0',
        'timestamp': time.time(),
        'active_jobs': len(active_jobs),
        'max_workers': MAX_WORKERS
    }), 200

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint"""
    try:
        # Test Firestore connection
        firestore_client.collection('test').limit(1).get()
        
        # Test Gemini connection
        gemini_client.test_connection()
        
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

@app.route('/analyze', methods=['POST'])
def analyze_document():
    """Direct API endpoint for document analysis"""
    try:
        data = request.json
        document_id = data.get('documentId')
        analysis_type = data.get('analysisType', 'full')
        
        if not document_id:
            return jsonify({'error': 'documentId is required'}), 400
        
        # Process analysis
        result = analyzer.analyze_document(document_id, analysis_type)
        
        return jsonify({
            'success': True,
            'data': result,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Direct analysis error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }), 500

def process_analysis_message(message):
    """Process document analysis message from Pub/Sub"""
    job_id = None
    try:
        data = json.loads(message.data.decode('utf-8'))
        document_id = data.get('documentId')
        case_id = data.get('caseId')
        analysis_type = data.get('analysisType', 'full')
        user_id = data.get('userId')
        
        if not document_id:
            logger.error("Missing documentId in message")
            message.nack()
            return
        
        job_id = f"analyze_{document_id}_{int(time.time())}"
        active_jobs.add(job_id)
        
        logger.info(f"🤖 Starting analysis job {job_id} for document {document_id}")
        
        # Update document status
        doc_ref = firestore_client.collection('documents').document(document_id)
        doc_ref.update({
            'analysisStatus': 'processing',
            'analysisStartedAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        })
        
        # Perform analysis
        result = analyzer.analyze_document(document_id, analysis_type)
        
        # Save analysis results
        analysis_data = {
            'documentId': document_id,
            'caseId': case_id,
            'analysisType': analysis_type,
            'analyzedBy': user_id,
            'analyzedAt': firestore.SERVER_TIMESTAMP,
            'summary': result.get('summary', ''),
            'keyPoints': result.get('keyPoints', []),
            'legalRelevance': result.get('legalRelevance', ''),
            'entities': result.get('entities', []),
            'sentiment': result.get('sentiment', {}),
            'readability': result.get('readability', {}),
            'recommendations': result.get('recommendations', []),
            'confidence': result.get('confidence', 0.0),
            'processingTime': result.get('processingTime', 0.0),
            'metadata': result.get('metadata', {})
        }
        
        analysis_ref = firestore_client.collection('document_analysis').add(analysis_data)
        
        # Update document status
        doc_ref.update({
            'analysisStatus': 'completed',
            'analysisCompletedAt': firestore.SERVER_TIMESTAMP,
            'analysisId': analysis_ref[1].id,
            'updatedAt': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"✅ Analysis completed for document {document_id}")
        message.ack()
        
    except Exception as e:
        logger.error(f"❌ Analysis error for job {job_id}: {str(e)}")
        
        if 'document_id' in locals():
            try:
                doc_ref = firestore_client.collection('documents').document(document_id)
                doc_ref.update({
                    'analysisStatus': 'error',
                    'analysisError': str(e),
                    'analysisErrorAt': firestore.SERVER_TIMESTAMP,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                })
            except Exception as status_error:
                logger.error(f"Failed to update error status: {status_error}")
        
        message.nack()
    
    finally:
        if job_id:
            active_jobs.discard(job_id)

def start_subscriber():
    """Start Pub/Sub subscriber"""
    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)
    flow_control = pubsub_v1.types.FlowControl(max_messages=MAX_WORKERS)
    
    logger.info(f"🔄 Starting subscriber: {subscription_path}")
    
    try:
        subscriber.subscribe(
            subscription_path,
            callback=process_analysis_message,
            flow_control=flow_control
        )
        
        while not shutdown_event.is_set():
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"❌ Subscriber error: {e}")
        raise

if __name__ == '__main__':
    logger.info("🚀 Starting Document Analysis Service")
    
    # Start subscriber in background
    subscriber_thread = threading.Thread(target=start_subscriber, daemon=True)
    subscriber_thread.start()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)