# services/extraction-service/src/main.py
#from dotenv import load_dotenv
#load_dotenv()

import os
import json
import logging
import threading
import time
from flask import Flask, request, jsonify
from google.cloud import pubsub_v1, storage, firestore
from extractor import DocumentExtractor
from firestore_client import FirestoreClient
from types import SimpleNamespace

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize clients
try:
    firestore_client = FirestoreClient()
    storage_client = storage.Client()
    subscriber = pubsub_v1.SubscriberClient()
    extractor = DocumentExtractor()
    logger.info("✅ All clients initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize clients: {e}")
    raise

# Configuration
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
SUBSCRIPTION_NAME = os.environ.get('EXTRACTION_SUBSCRIPTION', 'document-extraction-trigger-sub')
STORAGE_BUCKET = os.environ.get('STORAGE_BUCKET', 'legal-case-documents')
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '5'))

# Global variables for graceful shutdown
shutdown_event = threading.Event()
active_jobs = set()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'extraction-service',
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
        firestore_client.test_connection()
        
        # Test Storage connection
        bucket = storage_client.bucket(STORAGE_BUCKET)
        bucket.exists()
        
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

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get extraction service statistics"""
    return jsonify({
        'active_jobs': len(active_jobs),
        'max_workers': MAX_WORKERS,
        'supported_formats': [
            'PDF', 'DOCX', 'DOC', 'PPTX', 'PPT', 
            'XLSX', 'XLS', 'TXT', 'RTF', 'CSV',
            'JPEG', 'PNG', 'GIF', 'WEBP', 'TIFF'
        ],
        'features': [
            'Text Extraction',
            'OCR Processing',
            'Multi-format Support',
            'Metadata Extraction',
            'Language Detection'
        ],
        'timestamp': time.time()
    })

def process_extraction_message(message):
    """Process document extraction message from Pub/Sub"""
    job_id = None
    try:
        raw_data = message.data
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode('utf-8')
        data = json.loads(raw_data)
        document_id = data.get('documentId')
        storage_key = data.get('storageKey')
        case_id = data.get('caseId')
        content_type = data.get('contentType')
        filename = data.get('filename', 'unknown')
        user_id = data.get('userId')
        
        if not all([document_id, storage_key, case_id, content_type]):
            logger.error(f"Missing required fields in message: {data}")
            message.nack()
            return
        
        job_id = f"extract_{document_id}_{int(time.time())}"
        active_jobs.add(job_id)
        
        logger.info(f"📄 Starting extraction job {job_id} for document {document_id} ({filename})")
        
        # Update document status to processing
        firestore_client.update_document_status(
            document_id, 
            'processing',
            extraction_started_at=firestore.SERVER_TIMESTAMP
        )
        
        # Download file from storage
        bucket = storage_client.bucket(STORAGE_BUCKET)
        blob = bucket.blob(storage_key)
        
        if not blob.exists():
            raise Exception(f"File not found in storage: {storage_key}")
        
        # Create temp file path
        temp_file_path = f"/tmp/{job_id}_{filename}"
        
        try:
            # Download file
            logger.info(f"⬇️ Downloading file: {storage_key}")
            blob.download_to_filename(temp_file_path)
            
            # Verify file size
            file_size = os.path.getsize(temp_file_path)
            if file_size == 0:
                raise Exception("Downloaded file is empty")
            
            logger.info(f"📁 File downloaded: {file_size} bytes")
            
            # Extract text based on content type
            logger.info(f"🔍 Starting text extraction for {content_type}")
            extracted_data = extractor.extract_text(temp_file_path, content_type, filename)
            
            if not extracted_data or 'text' not in extracted_data:
                raise Exception("No text could be extracted from the document")
            
            # Prepare extraction result
            extraction_result = {
                'documentId': document_id,
                'caseId': case_id,
                'storageKey': storage_key,
                'filename': filename,
                'contentType': content_type,
                'text': extracted_data['text'],
                'pageCount': extracted_data.get('page_count', 0),
                'wordCount': len(extracted_data['text'].split()) if extracted_data['text'] else 0,
                'characterCount': len(extracted_data['text']) if extracted_data['text'] else 0,
                'title': extracted_data.get('title', filename),
                'language': extracted_data.get('language', 'unknown'),
                'confidence': extracted_data.get('confidence', 0.0),
                'method': extracted_data.get('method', 'unknown'),
                'metadata': extracted_data.get('metadata', {}),
                'extractedBy': user_id,
                'createdAt': firestore.SERVER_TIMESTAMP,
                'processingTime': extracted_data.get('processing_time', 0)
            }
            
            # Save extracted data to Firestore
            logger.info(f"💾 Saving extraction results to Firestore")
            extraction_doc_id = firestore_client.save_extracted_document(extraction_result)
            
            # Update document status to completed
            firestore_client.update_document_status(
                document_id, 
                'completed',
                extraction_completed_at=firestore.SERVER_TIMESTAMP,
                extraction_doc_id=extraction_doc_id,
                text_length=len(extracted_data['text']) if extracted_data['text'] else 0,
                page_count=extracted_data.get('page_count', 0)
            )
            
            logger.info(f"✅ Extraction completed successfully for document {document_id}")
            logger.info(f"📊 Extracted {len(extracted_data['text'])} characters from {extracted_data.get('page_count', 0)} pages")

            try:
                publisher = pubsub_v1.PublisherClient()
                topic_path = publisher.topic_path(PROJECT_ID, "document-analysis-trigger")
    
                analysis_message = {
                    "documentId": document_id,
                    "caseId": case_id,
                    "analysisType": "full",
                    "userId": user_id
                }
    
                future = publisher.publish(topic_path, json.dumps(analysis_message).encode("utf-8"))
                logger.info(f"📤 Published analysis trigger for document {document_id}: {future.result()}")
            except Exception as publish_error:
                logger.error(f"❌ Failed to publish analysis trigger: {publish_error}")                       

            message.ack()
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    logger.info(f"🗑️ Cleaned up temp file: {temp_file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Failed to clean up temp file: {cleanup_error}")
        
    except Exception as e:
        logger.error(f"❌ Error processing extraction job {job_id}: {str(e)}")
        
        if 'document_id' in locals():
            try:
                # Update document status to error
                firestore_client.update_document_status(
                    document_id, 
                    'error',
                    error_message=str(e),
                    error_timestamp=firestore.SERVER_TIMESTAMP
                )
            except Exception as status_error:
                logger.error(f"❌ Failed to update error status: {status_error}")
        
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
    
    # Configure flow control
    flow_control = pubsub_v1.types.FlowControl(max_messages=MAX_WORKERS)
    
    logger.info(f"🔄 Starting subscriber for: {subscription_path}")
    logger.info(f"⚙️ Max workers: {MAX_WORKERS}")
    
    try:
        # Start subscriber with callback
        subscriber.subscribe(
            subscription_path, 
            callback=process_extraction_message,
            flow_control=flow_control
        )
        
        logger.info("✅ Subscriber started successfully")
        
        # Keep the subscriber running
        while not shutdown_event.is_set():
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"❌ Subscriber error: {e}")
        raise

def shutdown_handler():
    """Handle graceful shutdown"""
    logger.info("🛑 Shutting down extraction service...")
    shutdown_event.set()
    
    # Wait for active jobs to complete (max 30 seconds)
    wait_time = 0
    while active_jobs and wait_time < 30:
        logger.info(f"⏳ Waiting for {len(active_jobs)} active jobs to complete...")
        time.sleep(2)
        wait_time += 2
    
    if active_jobs:
        logger.warning(f"⚠️ Forcing shutdown with {len(active_jobs)} active jobs")
    else:
        logger.info("✅ All jobs completed, shutdown successful")

import signal

# Register graceful shutdown handlers
signal.signal(signal.SIGTERM, lambda s, f: shutdown_handler())
signal.signal(signal.SIGINT, lambda s, f: shutdown_handler())

# Start subscriber thread automatically when app loads (for Gunicorn)
#subscriber_thread = threading.Thread(target=start_subscriber, daemon=True)
#subscriber_thread.start()

logger.info("🚀 Extraction Service initialized for production mode")
logger.info(f"📅 Started at: {time.ctime()}")
logger.info(f"🌐 Project ID: {PROJECT_ID}")
logger.info(f"💾 Storage Bucket: {STORAGE_BUCKET}")
logger.info(f"⚙️ Max Workers: {MAX_WORKERS}")

    
@app.route('/process-message', methods=['POST'])
def process_message():
    """Pub/Sub push endpoint to handle document extraction jobs"""
    try:
        envelope = request.get_json()
        if not envelope or 'message' not in envelope:
            logger.error("❌ Invalid Pub/Sub message format")
            return ('Bad Request', 400)

        message = envelope['message']
        data = message.get('data')

        if data:
            import base64
            decoded = json.loads(base64.b64decode(data).decode('utf-8'))
            logger.info(f"📨 Received Pub/Sub message for document: {decoded.get('documentId')}")
            
            process_extraction_message(SimpleNamespace(
                data=json.dumps(decoded),
                ack=lambda: None,
                nack=lambda: None
            ))

        return ('OK', 200)

    except Exception as e:
        logger.error(f"❌ Failed to process Pub/Sub message: {e}")
        return ('Internal Server Error', 500)