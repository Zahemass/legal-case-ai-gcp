# services/ai-agent-service/src/main.py
import eventlet
eventlet.monkey_patch()


import os
import json
import logging
import threading
import time
from flask import Flask, request, copy_current_request_context
from flask_socketio import SocketIO, emit, join_room, leave_room
from google.auth import default
from google.cloud import firestore, storage
from google.api_core.client_options import ClientOptions
from google.api_core.gapic_v1.client_info import ClientInfo
from google.api_core.exceptions import GoogleAPICallError
from dotenv import load_dotenv

from orchestrator import AgentOrchestrator
from websocket_handler import WebSocketHandler

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()

# ----------------------------
# Initialize Google credentials early (avoid 300s delay)
# ----------------------------
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

# ✅ Check key presence
if os.environ.get("GOOGLE_AI_API_KEY"):
    logger.info("🔑 Gemini API key loaded successfully.")
else:
    logger.warning("⚠️ Gemini API key not found. AI agents may run in fallback mode.")

# Initialize Flask app with Socket.IO
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'legal-ai-secret-key')

# Initialize Socket.IO with CORS support
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=180,
    ping_interval=20,
    async_mode="eventlet",
    max_http_buffer_size=10_000_000
)

# Initialize services
try:
    firestore_client = None
    storage_client = None
    def get_firestore_client():
        global firestore_client
        if firestore_client is None:
         try:
            firestore_client = firestore.Client(
                client_options=ClientOptions(api_endpoint="firestore.googleapis.com"),
                client_info=ClientInfo(user_agent="legal-ai/ai-agent-service")
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

    orchestrator = AgentOrchestrator(get_firestore_client(), get_storage_client()) 
    websocket_handler = WebSocketHandler(orchestrator, get_firestore_client())
    
    logger.info("✅ All services initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize services: {e}")
    raise

# Configuration
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

# Active connections tracking
active_connections = {}
active_chats = {}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
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
    """Lightweight readiness check for Cloud Run"""
    try:
        # Minimal test — don't call Firestore to avoid cold-start blocking
        status = {
            'status': 'ready',
            'timestamp': time.time()
        }
        return status, 200
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {'status': 'not_ready', 'error': str(e)}, 503

@app.route('/agents', methods=['GET'])
def get_available_agents():
    """Get list of available AI agents"""
    try:
        agents = orchestrator.get_available_agents()
        return {
            'success': True,
            'agents': agents,
            'timestamp': time.time()
        }
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }, 500

@app.before_request
def log_request_info():
    logger.info(f"📨 Incoming: {request.method} {request.path} from {request.remote_addr}")

# WebSocket Events
@socketio.on('connect')
def handle_connect(auth=None):
    """Handle client connection"""
    try:
        client_id = request.sid
        user_data = auth or {}
        
        logger.info(f"🔌 Client connected: {client_id}")
        
        # Store connection info
        active_connections[client_id] = {
            'connected_at': time.time(),
            'user_id': user_data.get('userId'),
            'case_id': user_data.get('caseId'),
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }
        
        # Send welcome message
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
    """Handle client disconnection"""
    try:
        client_id = request.sid
        logger.info(f"🔌 Client disconnected: {client_id}")
        
        # Clean up connection data
        if client_id in active_connections:
            connection_data = active_connections.pop(client_id)
            case_id = connection_data.get('case_id')
            
            # Leave case room if in one
            if case_id:
                leave_room(f"case_{case_id}")
                
                # Clean up active chat if it was the last client
                if case_id in active_chats:
                    active_chats[case_id]['client_count'] -= 1
                    if active_chats[case_id]['client_count'] <= 0:
                        del active_chats[case_id]
        
        logger.info(f"✅ Client {client_id} cleanup completed")
        
    except Exception as e:
        logger.error(f"❌ Disconnect error: {e}")

@socketio.on('join_case')
def handle_join_case(data):
    """Handle client joining a case chat room"""
    try:
        client_id = request.sid
        case_id = data.get('caseId')
        user_id = data.get('userId')
        
        if not case_id or not user_id:
            emit('error', {'error': 'caseId and userId are required'})
            return
        
        # Verify user has access to case
        if not websocket_handler.verify_case_access(case_id, user_id):
            emit('error', {'error': 'Access denied to case'})
            return
        
        # Join case room
        join_room(f"case_{case_id}")
        
        # Update connection info
        if client_id in active_connections:
            active_connections[client_id]['case_id'] = case_id
            active_connections[client_id]['user_id'] = user_id
        
        # Initialize or update active chat
        if case_id not in active_chats:
            active_chats[case_id] = {
                'case_id': case_id,
                'created_at': time.time(),
                'client_count': 0,
                'message_count': 0,
                'last_activity': time.time()
            }
        
        active_chats[case_id]['client_count'] += 1
        active_chats[case_id]['last_activity'] = time.time()
        
        # Send case info and chat history
        case_info = websocket_handler.get_case_info(case_id)
        chat_history = websocket_handler.get_chat_history(case_id, limit=20)
        
        emit('case_joined', {
            'caseId': case_id,
            'caseInfo': case_info,
            'chatHistory': chat_history,
            'timestamp': time.time()
        })
        
        # Notify other clients in the room
        emit('user_joined', {
            'userId': user_id,
            'timestamp': time.time()
        }, room=f"case_{case_id}", include_self=False)
        
        logger.info(f"✅ Client {client_id} joined case {case_id}")
        
    except Exception as e:
        logger.error(f"❌ Join case error: {e}")
        emit('error', {'error': 'Failed to join case', 'details': str(e)})

@socketio.on('leave_case')
def handle_leave_case(data):
    """Handle client leaving a case chat room"""
    try:
        client_id = request.sid
        case_id = data.get('caseId')
        user_id = data.get('userId')
        
        if case_id:
            leave_room(f"case_{case_id}")
            
            # Update active chat
            if case_id in active_chats:
                active_chats[case_id]['client_count'] -= 1
                if active_chats[case_id]['client_count'] <= 0:
                    del active_chats[case_id]
            
            # Notify other clients
            emit('user_left', {
                'userId': user_id,
                'timestamp': time.time()
            }, room=f"case_{case_id}")
        
        # Update connection info
        if client_id in active_connections:
            active_connections[client_id]['case_id'] = None
        
        emit('case_left', {'caseId': case_id, 'timestamp': time.time()})
        
        logger.info(f"✅ Client {client_id} left case {case_id}")
        
    except Exception as e:
        logger.error(f"❌ Leave case error: {e}")
        emit('error', {'error': 'Failed to leave case', 'details': str(e)})

@socketio.on('send_message')
def handle_send_message(data):
    """Handle incoming chat message"""
    try:
        client_id = request.sid
        case_id = data.get('caseId')
        user_id = data.get('userId')
        message = data.get('message', '').strip()
        message_type = data.get('type', 'user')
        
        if not all([case_id, user_id, message]):
            emit('error', {'error': 'caseId, userId, and message are required'})
            return
        
        if len(message) > 4000:
            emit('error', {'error': 'Message too long (max 4000 characters)'})
            return
        
        # Verify access
        if not websocket_handler.verify_case_access(case_id, user_id):
            emit('error', {'error': 'Access denied'})
            return
        
        logger.info(f"💬 Processing message from user {user_id} in case {case_id}")
        
        # Save user message
        user_message_id = websocket_handler.save_message(
            case_id=case_id,
            user_id=user_id,
            message=message,
            message_type='user',
            metadata={'client_id': client_id}
        )
        
        # Broadcast user message to all clients in the room
        user_message_data = {
            'id': user_message_id,
            'caseId': case_id,
            'userId': user_id,
            'message': message,
            'type': 'user',
            'timestamp': time.time()
        }
        
        emit('message_received', user_message_data, room=f"case_{case_id}")
        
        # Update active chat
        if case_id in active_chats:
            active_chats[case_id]['message_count'] += 1
            active_chats[case_id]['last_activity'] = time.time()
        
        # Process message with AI agents (async)
        @copy_current_request_context
        def process_ai_response():
            try:
                # Indicate that AI is thinking
                emit('ai_thinking', {
                    'caseId': case_id,
                    'timestamp': time.time()
                }, room=f"case_{case_id}")
                
                # Get AI response from orchestrator
                ai_response = orchestrator.process_message(
                    case_id=case_id,
                    user_id=user_id,
                    message=message,
                    conversation_history=websocket_handler.get_chat_history(case_id, limit=10)
                )
                
                if ai_response:
                    # Save AI message
                    ai_message_id = websocket_handler.save_message(
                        case_id=case_id,
                        user_id='ai_agent',
                        message=ai_response['response'],
                        message_type='ai',
                        metadata={
                            'agent': ai_response.get('agent', 'general'),
                            'confidence': ai_response.get('confidence', 0.0),
                            'processing_time': ai_response.get('processing_time', 0.0)
                        }
                    )
                    
                    # Broadcast AI response
                    ai_message_data = {
                        'id': ai_message_id,
                        'caseId': case_id,
                        'userId': 'ai_agent',
                        'message': ai_response['response'],
                        'type': 'ai',
                        'agent': ai_response.get('agent', 'general'),
                        'confidence': ai_response.get('confidence', 0.0),
                        'timestamp': time.time()
                    }
                    
                    socketio.emit('message_received', ai_message_data, room=f"case_{case_id}")
                    
                    # Update active chat
                    if case_id in active_chats:
                        active_chats[case_id]['message_count'] += 1
                        active_chats[case_id]['last_activity'] = time.time()
                
                else:
                    # Send error message if AI failed
                    error_message_data = {
                        'id': f"error_{int(time.time())}",
                        'caseId': case_id,
                        'userId': 'ai_agent',
                        'message': 'I apologize, but I encountered an error processing your request. Please try again.',
                        'type': 'ai',
                        'agent': 'error',
                        'timestamp': time.time()
                    }
                    
                    socketio.emit('message_received', error_message_data, room=f"case_{case_id}")
                
                # Stop thinking indicator
                socketio.emit('ai_thinking_stop', {
                    'caseId': case_id,
                    'timestamp': time.time()
                }, room=f"case_{case_id}")
                
            except Exception as e:
                logger.error(f"❌ AI processing error: {e}")
                
                # Send error message
                error_message_data = {
                    'id': f"error_{int(time.time())}",
                    'caseId': case_id,
                    'userId': 'ai_agent',
                    'message': 'I apologize, but I encountered a technical error. Please try again later.',
                    'type': 'ai',
                    'agent': 'error',
                    'timestamp': time.time()
                }
                
                socketio.emit('message_received', error_message_data, room=f"case_{case_id}")
                socketio.emit('ai_thinking_stop', {
                    'caseId': case_id,
                    'timestamp': time.time()
                }, room=f"case_{case_id}")
        
        # Start AI processing in background thread
        socketio.start_background_task(process_ai_response)

        
        logger.info(f"✅ Message processed for case {case_id}")
        
    except Exception as e:
        logger.error(f"❌ Send message error: {e}")
        emit('error', {'error': 'Failed to send message', 'details': str(e)})

@socketio.on('get_chat_history')
def handle_get_chat_history(data):
    """Handle request for chat history"""
    try:
        case_id = data.get('caseId')
        user_id = data.get('userId')
        limit = min(data.get('limit', 50), 100)  # Max 100 messages
        offset = data.get('offset', 0)
        
        if not websocket_handler.verify_case_access(case_id, user_id):
            emit('error', {'error': 'Access denied'})
            return
        
        chat_history = websocket_handler.get_chat_history(case_id, limit=limit, offset=offset)
        
        emit('chat_history', {
            'caseId': case_id,
            'history': chat_history,
            'limit': limit,
            'offset': offset,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"❌ Get chat history error: {e}")
        emit('error', {'error': 'Failed to get chat history', 'details': str(e)})

@socketio.on('clear_chat_history')
def handle_clear_chat_history(data):
    """Handle request to clear chat history"""
    try:
        case_id = data.get('caseId')
        user_id = data.get('userId')
        
        if not websocket_handler.verify_case_access(case_id, user_id):
            emit('error', {'error': 'Access denied'})
            return
        
        # Clear chat history
        cleared_count = websocket_handler.clear_chat_history(case_id, user_id)
        
        # Notify all clients in the room
        emit('chat_history_cleared', {
            'caseId': case_id,
            'clearedBy': user_id,
            'messageCount': cleared_count,
            'timestamp': time.time()
        }, room=f"case_{case_id}")
        
        logger.info(f"✅ Chat history cleared for case {case_id} by user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Clear chat history error: {e}")
        emit('error', {'error': 'Failed to clear chat history', 'details': str(e)})

@socketio.on('typing_start')
def handle_typing_start(data):
    """Handle typing start notification"""
    try:
        case_id = data.get('caseId')
        user_id = data.get('userId')
        
        # Broadcast to other clients in the room
        emit('user_typing_start', {
            'caseId': case_id,
            'userId': user_id,
            'timestamp': time.time()
        }, room=f"case_{case_id}", include_self=False)
        
    except Exception as e:
        logger.error(f"❌ Typing start error: {e}")

@socketio.on('typing_stop')
def handle_typing_stop(data):
    """Handle typing stop notification"""
    try:
        case_id = data.get('caseId')
        user_id = data.get('userId')
        
        # Broadcast to other clients in the room
        emit('user_typing_stop', {
            'caseId': case_id,
            'userId': user_id,
            'timestamp': time.time()
        }, room=f"case_{case_id}", include_self=False)
        
    except Exception as e:
        logger.error(f"❌ Typing stop error: {e}")

# Background task to clean up inactive connections
def cleanup_inactive_connections():
    """Clean up inactive connections and chats"""
    while True:
        try:
            current_time = time.time()
            timeout = 3600  # 1 hour timeout
            
            # Clean up inactive connections
            inactive_connections = []
            for client_id, conn_data in active_connections.items():
                if current_time - conn_data['connected_at'] > timeout:
                    inactive_connections.append(client_id)
            
            for client_id in inactive_connections:
                logger.info(f"🧹 Cleaning up inactive connection: {client_id}")
                active_connections.pop(client_id, None)
            
            # Clean up inactive chats
            inactive_chats = []
            for case_id, chat_data in active_chats.items():
                if current_time - chat_data['last_activity'] > timeout:
                    inactive_chats.append(case_id)
            
            for case_id in inactive_chats:
                logger.info(f"🧹 Cleaning up inactive chat: {case_id}")
                active_chats.pop(case_id, None)
            
            if inactive_connections or inactive_chats:
                logger.info(f"✅ Cleanup completed: {len(inactive_connections)} connections, {len(inactive_chats)} chats")
            
            # Sleep for 5 minutes before next cleanup
            time.sleep(300)
            
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")
            time.sleep(60)  # Wait 1 minute before retrying



if __name__ == '__main__':
    logger.info("🚀 Starting AI Agent Service")
    logger.info(f"📅 Started at: {time.ctime()}")
    logger.info(f"🌐 Project ID: {PROJECT_ID}")
    
    # Start cleanup task in background
    cleanup_thread = threading.Thread(target=cleanup_inactive_connections, daemon=True)
    cleanup_thread.start()
    
    # Start Socket.IO server
    port = int(os.environ.get('PORT', 8080))
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=port,
        debug=False,
        use_reloader=False
    )