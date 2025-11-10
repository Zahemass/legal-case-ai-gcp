# services/case-analysis-service/src/main.py

import os
import json
import base64
import logging
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.cloud import firestore
from case_analyzer import CaseAnalyzer
from gemini_client import GeminiClient
from dotenv import load_dotenv

# ---------------------------------------------------------
# 🔧 Load environment variables
# ---------------------------------------------------------
env_path = os.path.join(os.path.dirname(__file__), "../.env")
print(f"🔍 Loading .env from: {os.path.abspath(env_path)}")
load_dotenv(dotenv_path=env_path)

# ---------------------------------------------------------
# 🧠 Logging configuration (Cloud Run friendly)
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# 🚀 Flask app initialization
# ---------------------------------------------------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": os.getenv("ALLOWED_ORIGINS", "*")}})

# ---------------------------------------------------------
# 🔌 Initialize Firestore and Gemini clients
# ---------------------------------------------------------
try:
    firestore_client = firestore.Client()
    gemini_client = GeminiClient()
    case_analyzer = CaseAnalyzer(gemini_client, firestore_client)
    logger.info("✅ Firestore & Gemini clients initialized successfully")
except Exception as e:
    logger.error(f"❌ Client initialization failed: {e}", exc_info=True)
    raise

# ---------------------------------------------------------
# ⚙️ Config values
# ---------------------------------------------------------
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
SERVICE_NAME = os.getenv("SERVICE_NAME", "case-analysis-service")
REGION = os.getenv("REGION", "us-central1")

# ---------------------------------------------------------
# 🩺 Health & Readiness Checks
# ---------------------------------------------------------
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": SERVICE_NAME,
        "timestamp": time.time()
    }), 200


@app.route("/ready", methods=["GET"])
def readiness_check():
    try:
        firestore_client.collection("test").limit(1).get()
        gemini_client.test_connection()
        return jsonify({"status": "ready", "timestamp": time.time()}), 200
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({"status": "not_ready", "error": str(e)}), 503


# ---------------------------------------------------------
# 🧩 Manual Case Analysis Endpoint
# ---------------------------------------------------------
@app.route("/analyze", methods=["POST"])
def analyze_case():
    """Manually trigger case analysis (used by frontend UI)"""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid or empty JSON body"}), 400

        case_id = data.get("caseId")
        analysis_type = data.get("analysisType", "comprehensive")

        if not case_id:
            return jsonify({"error": "caseId required"}), 400

        # --- Get case document ---
        case_ref = firestore_client.collection("cases").document(case_id)
        case_doc = case_ref.get()
        if not case_doc.exists:
            return jsonify({"error": f"Case {case_id} not found"}), 404

        case_data = case_doc.to_dict()
        current_status = case_data.get("analysisStatus")
        existing_analysis_id = case_data.get("analysisId")

        logger.info(f"📄 [{case_id}] Current status: {current_status}")

        # --- If completed already, return cached analysis ---
        if current_status == "completed" and existing_analysis_id:
            analysis_ref = firestore_client.collection("case_analyses").document(existing_analysis_id)
            if analysis_ref.get().exists:
                logger.info(f"📦 Returning cached analysis for case {case_id}")
                return jsonify({
                    "success": True,
                    "cached": True,
                    "caseId": case_id,
                    "data": analysis_ref.get().to_dict()
                }), 200
            else:
                logger.warning(f"⚠️ Missing analysis doc {existing_analysis_id}, re-running analysis")

        # --- Otherwise, start new analysis ---
        logger.info(f"🟡 Running new analysis for case {case_id}")
        case_ref.update({
            "analysisStatus": "processing",
            "lastAnalysisStartedAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })

        # Run analysis
        result = case_analyzer.analyze_case(case_id, analysis_type)

        # Save analysis result
        analysis_ref = firestore_client.collection("case_analyses").add({
            **result,
            "caseId": case_id,
            "analysisType": analysis_type,
            "analyzedAt": firestore.SERVER_TIMESTAMP,
        })

        # Update case metadata
        case_ref.update({
            "analysisStatus": "completed",
            "lastAnalyzedAt": firestore.SERVER_TIMESTAMP,
            "analysisId": analysis_ref[1].id,
            "analysisCount": firestore.Increment(1),
            "updatedAt": firestore.SERVER_TIMESTAMP
        })
        logger.info(f"✅ Case {case_id} analysis completed successfully")

        return jsonify({
            "success": True,
            "cached": False,
            "caseId": case_id,
            "data": result
        }), 200

    except Exception as e:
        logger.error(f"❌ [Case] Analysis error: {e}", exc_info=True)
        try:
            firestore_client.collection("cases").document(case_id).update({
                "analysisStatus": "error",
                "analysisError": str(e),
                "analysisErrorAt": firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })
        except Exception as err:
            logger.error(f"⚠️ Failed to update case {case_id} with error: {err}")

        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------
# 📨 Pub/Sub Push Endpoint (for async analysis)
# ---------------------------------------------------------
@app.route("/pubsub/push", methods=["POST"])
def pubsub_push():
    """Cloud Run Pub/Sub push endpoint"""
    envelope = request.get_json(silent=True)
    if not envelope:
        return "Bad Request: No Pub/Sub message", 400

    try:
        message_data = envelope.get("message", {}).get("data")
        if not message_data:
            return "Bad Request: Missing message data", 400

        data = json.loads(base64.b64decode(message_data).decode("utf-8"))
        case_id = data.get("caseId")
        user_id = data.get("userId")
        analysis_type = data.get("analysisType", "comprehensive")

        logger.info(f"📨 Pub/Sub triggered analysis for case {case_id} by user {user_id}")

        # Firestore updates
        case_ref = firestore_client.collection("cases").document(case_id)
        case_ref.update({
            "analysisStatus": "processing",
            "lastAnalysisStartedAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })

        # Perform analysis
        result = case_analyzer.analyze_case(case_id, analysis_type)
        analysis_ref = firestore_client.collection("case_analyses").add({
            **result,
            "caseId": case_id,
            "analysisType": analysis_type,
            "analyzedAt": firestore.SERVER_TIMESTAMP,
        })

        # Update case
        case_ref.update({
            "analysisStatus": "completed",
            "lastAnalyzedAt": firestore.SERVER_TIMESTAMP,
            "analysisId": analysis_ref[1].id,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })

        logger.info(f"✅ Pub/Sub analysis completed for case {case_id}")
        return "OK", 200

    except Exception as e:
        logger.error(f"❌ Pub/Sub message processing error: {e}", exc_info=True)
        return "Internal Server Error", 500


# ---------------------------------------------------------
# 🧱 Gunicorn Entrypoint (Cloud Run entry)
# ---------------------------------------------------------
def start_service():
    """Gunicorn entrypoint for Cloud Run"""
    logger.info(f"🚀 Starting {SERVICE_NAME} on Cloud Run (region: {REGION})")
    return app


# ---------------------------------------------------------
# 👩‍💻 Local Development (Flask dev server)
# ---------------------------------------------------------
if __name__ == "__main__":
    logger.info("🧩 Running locally (development mode)")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
