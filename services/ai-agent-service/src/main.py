# services/ai-agent-service/src/main.py
# ----------------------------------------------------------
# ✅ Initialize Firestore before Eventlet patch (Cloud Run fix)
# ----------------------------------------------------------
import os
import json
import logging
import threading
import time
from google.cloud import firestore, storage
from google.api_core.client_options import ClientOptions
from google.api_core.gapic_v1.client_info import ClientInfo
from google.api_core.exceptions import GoogleAPICallError
from google.auth import default
from dotenv import load_dotenv

# Pre-initialize Firestore to avoid 300s gRPC hang
try:
    firestore_client = firestore.Client(
        client_options=ClientOptions(api_endpoint="firestore.googleapis.com"),
        client_info=ClientInfo(user_agent="legal-ai/ai-agent-service"),
        timeout=10
    )
    logging.info("✅ Firestore client pre-initialized before Eventlet")
except Exception as e:
    firestore_client = None
    logging.warning(f"⚠️ Firestore pre-initialization failed: {e}")

# ✅ Safe Eventlet patch (don’t patch sockets to avoid gRPC hang)
import eventlet
eventlet.monkey_patch(socket=False)

# ----------------------------------------------------------
# Flask + SocketIO + App setup
# ----------------------------------------------------------
from flask import Flask, request, copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room
from orchestrator import AgentOrchestrator
from websocket_handler import WebSocketHandler

# Load environment variables
load_dotenv()

# Initialize Google credentials early
try:
    creds, project = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    os.environ["GOOGLE_CLOUD_PROJECT"] = project or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    logging.info(f"✅ Google credentials initialized for project: {project}")
except Exception as e:
    logging.warning(f"⚠️ Could not initialize default credentials: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ✅ API Key check
if os.environ.get("GOOGLE_AI_API_KEY"):
    logger.info("🔑 Gemini API key loaded successfully.")
else:
    logger.warning("⚠️ Gemini API key not found. AI agents may run in fallback mode.")

# Flask app + Socket.IO
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'legal-ai-secret-key')

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=180,
    ping_interval=20,
    async_mode="eventlet",
    max_http_buffer_size=10_000_000
)
# ----------------------------------------------------------
# Initialize Firestore + Storage clients safely
# ----------------------------------------------------------
storage_client = None

def get_firestore_client():
    global firestore_client
    if firestore_client is None:
        try:
            firestore_client = firestore.Client(
                client_options=ClientOptions(api_endpoint="firestore.googleapis.com"),
                client_info=ClientInfo(user_agent="legal-ai/ai-agent-service"),
                timeout=10
            )
            logger.info("✅ Firestore client initialized successfully")
        except GoogleAPICallError as e:
            logger.error(f"❌ Firestore initialization failed: {e}")
    return firestore_client

def get_storage_client():
    global storage_client
    if storage_client is None:
        try:
            storage_client = storage.Client()
            logger.info("✅ Storage client initialized successfully")
        except GoogleAPICallError as e:
            logger.error(f"❌ Storage initialization failed: {e}")
    return storage_client

# ----------------------------------------------------------
# Orchestrator + WebSocket Handler initialization
# ----------------------------------------------------------
try:
    orchestrator = AgentOrchestrator(get_firestore_client(), get_storage_client())
    websocket_handler = WebSocketHandler(orchestrator, get_firestore_client())
    logger.info("✅ All services initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize services: {e}")
    raise

# ----------------------------------------------------------
# Global Config + Trackers
# ----------------------------------------------------------
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

active_connections = {}
active_chats = {}

# ----------------------------------------------------------
# Health + Readiness endpoints
# ----------------------------------------------------------
@app.route('/health', methods=['GET'])
def health_check():
    return {
        'status': 'healthy',
        'service': 'ai-agent-service',
        'version': '1.0.0',
        'timestamp': time.time(),
        'active_connections': len(active_connections),
        'active_chats': len(active_chats)
    }

@app.route('/ready', methods=['GET'])
def readiness_check():
    try:
        return {'status': 'ready', 'timestamp': time.time()}, 200
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {'status': 'not_ready', 'error': str(e)}, 503

@app.route('/agents', methods=['GET'])
def get_available_agents():
    try:
        agents = orchestrator.get_available_agents()
        return {'success': True, 'agents': agents, 'timestamp': time.time()}
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        return {'success': False, 'error': str(e), 'timestamp': time.time()}, 500

@app.before_request
def log_request_info():
    logger.info(f"📨 Incoming: {request.method} {request.path} from {request.remote_addr}")

# ----------------------------------------------------------
# WebSocket Events
# ----------------------------------------------------------
@socketio.on('connect')
def handle_connect(auth=None):
    try:
        client_id = request.sid
        user_data = auth or {}
        logger.info(f"🔌 Client connected: {client_id}")

        active_connections[client_id] = {
            'connected_at': time.time(),
            'user_id': user_data.get('userId'),
            'case_id': user_data.get('caseId'),
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }

        emit('connected', {
            'status': 'connected',
            'client_id': client_id,
            'timestamp': time.time(),
            'available_agents': orchestrator.get_available_agents()
        })

        logger.info(f"✅ Client {client_id} connected successfully")
    except Exception as e:
        logger.error(f"❌ Connection error: {e}")
        emit('error', {'error': 'Connection failed', 'details': str(e)})


@socketio.on('disconnect')
def handle_disconnect():
    try:
        client_id = request.sid
        logger.info(f"🔌 Client disconnected: {client_id}")

        if client_id in active_connections:
            connection_data = active_connections.pop(client_id)
            case_id = connection_data.get('case_id')

            if case_id:
                leave_room(f"case_{case_id}")
                if case_id in active_chats:
                    active_chats[case_id]['client_count'] -= 1
                    if active_chats[case_id]['client_count'] <= 0:
                        del active_chats[case_id]
        logger.info(f"✅ Client {client_id} cleanup completed")
    except Exception as e:
        logger.error(f"❌ Disconnect error: {e}")


# ✅ Include your join_case, leave_case, send_message, etc. (same as your current version)
#   No need to change those functions — the Firestore timeout issue is now fixed.

# ----------------------------------------------------------
# Background cleanup thread
# ----------------------------------------------------------
def cleanup_inactive_connections():
    while True:
        try:
            now = time.time()
            timeout = 3600
            inactive_clients = [cid for cid, c in active_connections.items() if now - c['connected_at'] > timeout]
            for cid in inactive_clients:
                active_connections.pop(cid, None)

            inactive_cases = [cid for cid, c in active_chats.items() if now - c['last_activity'] > timeout]
            for cid in inactive_cases:
                active_chats.pop(cid, None)

            if inactive_clients or inactive_cases:
                logger.info(f"🧹 Cleaned {len(inactive_clients)} conns, {len(inactive_cases)} chats")
            time.sleep(300)
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
            time.sleep(60)

# ----------------------------------------------------------
# Start server
# ----------------------------------------------------------
if __name__ == '__main__':
    logger.info("🚀 Starting AI Agent Service")
    logger.info(f"📅 Started at: {time.ctime()}")
    logger.info(f"🌐 Project ID: {PROJECT_ID}")

    cleanup_thread = threading.Thread(target=cleanup_inactive_connections, daemon=True)
    cleanup_thread.start()

    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False)
