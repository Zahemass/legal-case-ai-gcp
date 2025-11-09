#services/case-analysis-service/src/main.py
import os
import json
import logging
import threading
import time
from flask import Flask, request, jsonify
from google.cloud import pubsub_v1, firestore
from case_analyzer import CaseAnalyzer
from gemini_client import GeminiClient
from dotenv import load_dotenv  # ✅ NEW

env_path = os.path.join(os.path.dirname(__file__), "../.env")
print(f"🔍 Loading .env from: {os.path.abspath(env_path)}")
load_dotenv(dotenv_path=env_path)
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize clients
try:
    firestore_client = firestore.Client()
    subscriber = pubsub_v1.SubscriberClient()
    gemini_client = GeminiClient()
    case_analyzer = CaseAnalyzer(gemini_client, firestore_client)
    logger.info("✅ All clients initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize clients: {e}")
    raise

# Configuration
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
SUBSCRIPTION_NAME = 'case-analysis-subscription'
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '2'))

# Global variables
shutdown_event = threading.Event()
active_jobs = set()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'case-analysis-service',
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
def analyze_case():
    """Direct API endpoint for case analysis"""
    try:
        data = request.json
        case_id = data.get('caseId')
        analysis_type = data.get('analysisType', 'comprehensive')
        
        if not case_id:
            return jsonify({'error': 'caseId is required'}), 400
        
        # Process analysis
        result = case_analyzer.analyze_case(case_id, analysis_type)
        
        return jsonify({
            'success': True,
            'data': result,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Direct case analysis error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }), 500

def process_case_analysis_message(message):
    """Process case analysis message from Pub/Sub"""
    job_id = None
    try:
        data = json.loads(message.data.decode('utf-8'))
        case_id = data.get('caseId')
        user_id = data.get('userId')
        analysis_type = data.get('analysisType', 'comprehensive')
        document_count = data.get('documentCount', 0)
        
        if not case_id:
            logger.error("Missing caseId in message")
            message.nack()
            return
        
        job_id = f"case_analyze_{case_id}_{int(time.time())}"
        active_jobs.add(job_id)
        
        logger.info(f"🔍 Starting case analysis job {job_id} for case {case_id} ({document_count} documents)")
        
        # Update case status
        case_ref = firestore_client.collection('cases').document(case_id)
        case_ref.update({
            'analysisStatus': 'processing',
            'lastAnalysisStartedAt': firestore.SERVER_TIMESTAMP,
            'updatedAt': firestore.SERVER_TIMESTAMP
        })
        
        # Perform comprehensive case analysis
        result = case_analyzer.analyze_case(case_id, analysis_type)
        
        # Save analysis results
        analysis_data = {
            'caseId': case_id,
            'analysisType': analysis_type,
            'analyzedBy': user_id,
            'analyzedAt': firestore.SERVER_TIMESTAMP,
            'executiveSummary': result.get('executiveSummary', ''),
            'keyFindings': result.get('keyFindings', []),
            'strengthsWeaknesses': result.get('strengthsWeaknesses', {}),
            'legalIssues': result.get('legalIssues', []),
            'recommendations': result.get('recommendations', []),
            'documentAnalysis': result.get('documentAnalysis', {}),
            'timeline': result.get('timeline', []),
            'riskAssessment': result.get('riskAssessment', {}),
            'strategicAdvice': result.get('strategicAdvice', ''),
            'confidence': result.get('confidence', 0.0),
            'processingTime': result.get('processingTime', 0.0),
            'metadata': result.get('metadata', {}),
            'version': '1.0'
        }
        
        # Save to case_analysis collection
        analysis_ref = firestore_client.collection('case_analysis').add(analysis_data)
        
        # Update case with analysis results
        case_ref.update({
            'analysisStatus': 'completed',
            'lastAnalyzedAt': firestore.SERVER_TIMESTAMP,
            'analysisId': analysis_ref[1].id,
            'analysisCount': firestore.Increment(1),
            'updatedAt': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"✅ Case analysis completed for case {case_id}")
        message.ack()
        
    except Exception as e:
        logger.error(f"❌ Case analysis error for job {job_id}: {str(e)}")
        
        if 'case_id' in locals():
            try:
                case_ref = firestore_client.collection('cases').document(case_id)
                case_ref.update({
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
            callback=process_case_analysis_message,
            flow_control=flow_control
        )
        
        while not shutdown_event.is_set():
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"❌ Subscriber error: {e}")
        raise

def start_service():
    """Start background subscriber thread when Gunicorn loads"""
    logger.info("🚀 Starting Case Analysis Service (Gunicorn Mode)")
    subscriber_thread = threading.Thread(target=start_subscriber, daemon=True)
    subscriber_thread.start()
    return app


# Only for local testing (Flask dev server)
if __name__ == '__main__':
    app = start_service()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
