import os
import json
import base64
import logging
import threading
import time
from typing import Optional, Dict, Any
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import pubsub_v1, firestore
from dotenv import load_dotenv
from analyzer import DocumentAnalyzer
from gemini_client import GeminiClient

# -------------------------
# Load environment (local dev fallback)
# -------------------------
env_path = os.path.join(os.path.dirname(__file__), "../.env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)

# -------------------------
# Logging config (Cloud Run friendly)
# -------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("document-analysis-service")

# -------------------------
# Flask app
# -------------------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": os.getenv("ALLOWED_ORIGINS", "*")}}, supports_credentials=True)

# -------------------------
# Firestore / PubSub / Analyzer initialization
# -------------------------
try:
    firestore_client = firestore.Client()
    subscriber = pubsub_v1.SubscriberClient()
    gemini_client = GeminiClient()
    analyzer = DocumentAnalyzer(gemini_client, firestore_client)
    logger.info("✅ All clients initialized successfully")
except Exception as e:
    logger.exception("❌ Failed to initialize clients")
    raise

# Config
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
SUBSCRIPTION_NAME = os.getenv("SUBSCRIPTION_NAME", "")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "3"))
SERVICE_NAME = os.getenv("SERVICE_NAME", "document-analysis-service")

# Globals
shutdown_event = threading.Event()
active_jobs = set()

# -------------------------
# Helper: atomically mark document as processing (transaction)
# -------------------------
def try_mark_processing(doc_ref: firestore.DocumentReference, txn: firestore.Transaction) -> Dict[str, Any]:
    """If not processing, set processing and return current data. Raises RuntimeError if already processing."""
    snapshot = doc_ref.get(transaction=txn)
    if not snapshot.exists:
        raise RuntimeError("Document not found")

    data = snapshot.to_dict() or {}
    if data.get("analysisStatus") == "processing":
        raise RuntimeError("already_processing")

    txn.update(doc_ref, {
        "analysisStatus": "processing",
        "analysisStartedAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP
    })
    return data

# -------------------------
# Core: perform document analysis (transactional + safe)
# -------------------------
def perform_document_analysis(document_id: str, case_id: Optional[str], user_id: Optional[str], analysis_type: str = "full") -> Dict[str, Any]:
    """Runs analyzer safely with Firestore transaction + updates."""
    doc_ref = firestore_client.collection("documents").document(document_id)
    transaction = firestore_client.transaction()

    @firestore.transactional
    def mark_processing(txn):
        return try_mark_processing(doc_ref, txn)

    try:
        # ✅ Correct Firestore v2.x transaction syntax
        mark_processing(transaction)

        job_id = f"analyze_{document_id}_{int(time.time())}"
        active_jobs.add(job_id)
        logger.info("🤖 Starting analysis job %s (document=%s case=%s)", job_id, document_id, case_id)

        start_ts = time.time()
        result = analyzer.analyze_document(document_id, analysis_type)
        processing_time = time.time() - start_ts

        analysis_data = {
       "documentId": document_id,
       "caseId": case_id,
       "analysisType": analysis_type,
       "analyzedBy": user_id,
       "analyzedAt": firestore.SERVER_TIMESTAMP,
    
       # AI-generated insights
       "summary": result.get("summary", ""),
       "keyPoints": result.get("keyPoints", []),

       # Legal relevance (string summary)
       "legalRelevance": result.get("legalRelevance", ""),

       # Full structured legal analysis block
       "legalAnalysis": result.get("legalAnalysis", {
           "summary": "",
           "issues": [],
           "arguments": {"plaintiff": [], "defendant": []},
           "lawsOrSectionsCited": [],
           "verdictOrOutcome": "",
           "risks": [],
           "recommendations": [],
           "confidenceScore": 0
       }),

       # Entities, sentiment, and readability
       "entities": result.get("entities", {}),
       "sentiment": result.get("sentiment", {}),
       "readability": result.get("readability", {}),

       # Recommendations and confidence
       "recommendations": result.get("recommendations", []),
       "confidence": result.get("confidence", 0.0),

       # System metadata
       "processingTime": processing_time,
       "metadata": result.get("metadata", {})
   }


        # Save analysis
        analysis_ref = firestore_client.collection("document_analysis").add(analysis_data)
        analysis_id = analysis_ref[1].id
        logger.info("💾 Saved analysis %s for document %s", analysis_id, document_id)

        # Mark document completed
        doc_ref.update({
            "analysisStatus": "completed",
            "analysisCompletedAt": firestore.SERVER_TIMESTAMP,
            "analysisId": analysis_id,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })

        logger.info("✅ Analysis completed for document %s (analysis=%s)", document_id, analysis_id)
        return {**analysis_data, "analysisId": analysis_id}

    except RuntimeError as re:
        raise
    except Exception as e:
        logger.exception("❌ Analysis error for document %s: %s", document_id, e)
        try:
            doc_ref.update({
                "analysisStatus": "error",
                "analysisError": str(e),
                "analysisErrorAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
        except Exception:
            logger.exception("⚠️ Failed to update document error status for %s", document_id)
        raise
    finally:
        try:
            active_jobs.discard(job_id)
        except Exception:
            pass

# -------------------------
# Health / readiness endpoints
# -------------------------
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": SERVICE_NAME,
        "timestamp": time.time(),
        "active_jobs": len(active_jobs)
    }), 200

@app.route("/ready", methods=["GET"])
def readiness_check():
    try:
        firestore_client.collection("test").limit(1).get()
        gemini_client.test_connection()
        return jsonify({"status": "ready", "timestamp": time.time()}), 200
    except Exception as e:
        logger.exception("Readiness check failed")
        return jsonify({"status": "not_ready", "error": str(e)}), 503

# -------------------------
# Manual trigger endpoint
# -------------------------
@app.route("/analyze", methods=["POST"])
def analyze_document_endpoint():
    try:
        body = request.get_json(force=True)
        document_id = body.get("documentId")
        case_id = body.get("caseId")
        analysis_type = body.get("analysisType", "full")
        user_id = body.get("userId")

        if not document_id:
            return jsonify({"error": "documentId is required"}), 400

        doc_ref = firestore_client.collection("documents").document(document_id)
        doc_snapshot = doc_ref.get()
        if not doc_snapshot.exists:
            return jsonify({"error": f"Document {document_id} not found"}), 404

        doc_data = doc_snapshot.to_dict()
        if doc_data.get("analysisStatus") == "completed" and doc_data.get("analysisId"):
            analysis_ref = firestore_client.collection("document_analysis").document(doc_data["analysisId"])
            if analysis_ref.get().exists:
                return jsonify({
                    "success": True,
                    "cached": True,
                    "documentId": document_id,
                    "data": analysis_ref.get().to_dict()
                }), 200

        try:
            analysis_result = perform_document_analysis(document_id, case_id, user_id, analysis_type)
            return jsonify({"success": True, "cached": False, "documentId": document_id, "data": analysis_result}), 200
        except RuntimeError as e:
            if str(e) == "already_processing":
                return jsonify({"success": False, "error": "analysis already in progress"}), 409
            raise

    except Exception as e:
        logger.exception("❌ Direct analysis endpoint error")
        return jsonify({"success": False, "error": str(e)}), 500

# -------------------------
# Pub/Sub push endpoint (Cloud Run)
# -------------------------
@app.route("/pubsub/push", methods=["POST"])
def pubsub_push():
    """Receives Pub/Sub push messages in Cloud Run."""
    try:
        envelope = request.get_json(silent=True)
        if not envelope:
            return "Bad Request: no envelope", 400

        message = envelope.get("message", {})
        data_b64 = message.get("data")
        if not data_b64:
            return "Bad Request: missing message data", 400

        payload = json.loads(base64.b64decode(data_b64).decode("utf-8"))
        document_id = payload.get("documentId")
        case_id = payload.get("caseId")
        user_id = payload.get("userId")
        analysis_type = payload.get("analysisType", "full")

        if not document_id:
            return "Bad Request: missing documentId", 400

        try:
            perform_document_analysis(document_id, case_id, user_id, analysis_type)
            return "OK", 200
        except RuntimeError as re:
            if str(re) == "already_processing":
                logger.warning("Received duplicate Pub/Sub message for document %s", document_id)
                return "Already processing", 200
            raise

    except Exception as e:
        logger.exception("❌ Pub/Sub push handling error")
        return "Internal Server Error", 500

# -------------------------
# Local subscriber (dev only)
# -------------------------
def start_subscriber_local():
    if not SUBSCRIPTION_NAME:
        logger.info("No SUBSCRIPTION_NAME configured; skipping local subscriber")
        return

    subscription_path = subscriber.subscription_path(PROJECT_ID, SUBSCRIPTION_NAME)
    flow_control = pubsub_v1.types.FlowControl(max_messages=MAX_WORKERS)

    def callback(msg):
        try:
            payload = json.loads(msg.data.decode("utf-8"))
            perform_document_analysis(
                document_id=payload.get("documentId"),
                case_id=payload.get("caseId"),
                user_id=payload.get("userId"),
                analysis_type=payload.get("analysisType", "full")
            )
            msg.ack()
        except Exception:
            logger.exception("Failed to process local pubsub message")
            msg.nack()

    logger.info("🔄 Starting local subscriber on %s", subscription_path)
    subscriber.subscribe(subscription_path, callback=callback, flow_control=flow_control)

# -------------------------
# Gunicorn entrypoint
# -------------------------
def start_service():
    """Used by Gunicorn in production."""
    logger.info("🚀 Starting document-analysis-service (production mode)")
    return app

# -------------------------
# Local dev mode
# -------------------------
if __name__ == "__main__":
    logger.info("🧪 Running local dev server (Flask).")
    if SUBSCRIPTION_NAME:
        threading.Thread(target=start_subscriber_local, daemon=True).start()
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
