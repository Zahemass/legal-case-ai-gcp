#/services/ai-agent-service/src/websocket_handler.py
import logging
import time
from typing import Dict, Any, List, Optional
from google.cloud import firestore
from google.api_core.exceptions import DeadlineExceeded, NotFound, GoogleAPICallError
import datetime

def to_json_serializable(obj):
    """Recursively convert Firestore Timestamp or datetime to JSON-safe values"""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_json_serializable(v) for v in obj]
    else:
        return obj
logger = logging.getLogger(__name__)

class WebSocketHandler:
    """Handles WebSocket-related operations for AI agent chat"""
    
    def __init__(self, orchestrator, firestore_client):
        self.orchestrator = orchestrator
        self.firestore_client = firestore_client
        logger.info("✅ WebSocketHandler initialized")

    
       

    def verify_case_access(self, case_id: str, user_id: str) -> bool:
        """Verify user has access to the case (optimized for Cloud Run)"""
        try:
            if not case_id or not user_id:
                logger.warning("⚠️ Missing case_id or user_id in verify_case_access()")
                return False
            
            case_ref = self.firestore_client.collection('cases').document(case_id)
            case_doc = case_ref.get()
            
            if not case_doc.exists:
                logger.warning(f"⚠️Case {case_id} not found")
                return False
            
            case_data = case_doc.to_dict()
            created_by = case_data.get('createdBy')
            
            # Check if user is the case owner
            if created_by == user_id:
                logger.info(f"✅ Verified access: user {user_id} owns case {case_id}")
                return True
            
            # TODO: Add support for shared cases or team access
            # For now, only case owner has access
            
            logger.warning(f"User {user_id} denied access to case {case_id}")
            return False
        except DeadlineExceeded:
            logger.error(f"⏱️ Firestore timeout verifying case {case_id} for user {user_id}")
            return False
        except NotFound:
            logger.error(f"❌ Firestore document not found for case {case_id}")
            return False
        except GoogleAPICallError as api_err:
            logger.error(f"❌ Google API error verifying case access: {api_err}")
            return False   
        except Exception as e:
            logger.error(f"❌ Error verifying case access: {e}")
            return False

    def get_case_info(self, case_id: str) -> Dict[str, Any]:
        """Get case information for client"""
        try:
            case_ref = self.firestore_client.collection('cases').document(case_id)
            case_doc = case_ref.get()
            
            if not case_doc.exists:
                return {'error': 'Case not found'}
            
            case_data = case_doc.to_dict()
            
            # Get document count
            docs_query = self.firestore_client.collection('documents')\
                .where('caseId', '==', case_id)\
                .where('status', '!=', 'deleted')
            
            doc_count = len(docs_query.get())
            
            return to_json_serializable({
    'id': case_id,
    'title': case_data.get('title', 'Untitled Case'),
    'type': case_data.get('type', 'general'),
    'status': case_data.get('status', 'active'),
    'priority': case_data.get('priority', 'medium'),
    'description': case_data.get('description', ''),
    'createdAt': case_data.get('createdAt'),
    'updatedAt': case_data.get('updatedAt'),
    'documentCount': doc_count,
    'analysisCount': case_data.get('analysisCount', 0)
})

            
        except Exception as e:
            logger.error(f"❌ Error getting case info: {e}")
            return {'error': 'Failed to get case information'}

    def get_chat_history(self, case_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get chat history for a case"""
        try:
            messages_query = self.firestore_client.collection('chat_messages')\
                .where('caseId', '==', case_id)\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .offset(offset)
            
            messages = []
            for doc in messages_query.get():
                msg_data = doc.to_dict()
                messages.append({
                    'id': doc.id,
                    'caseId': msg_data.get('caseId'),
                    'userId': msg_data.get('userId'),
                    'message': msg_data.get('message'),
                    'type': msg_data.get('type', 'user'),
                    'agent': msg_data.get('agent'),
                    'timestamp': msg_data.get('timestamp'),
                    'confidence': msg_data.get('confidence'),
                    'metadata': msg_data.get('metadata', {})
                })
            
            # Reverse to get chronological order (oldest first)
            messages.reverse()
            
            # ✅ Convert timestamps to JSON-safe values
            return to_json_serializable(messages)
        except Exception as e:
            logger.error(f"❌ Error getting chat history: {e}")
            return []

    def save_message(self, case_id: str, user_id: str, message: str, message_type: str = 'user', 
                    metadata: Dict[str, Any] = None) -> str:
        """Save a chat message to Firestore"""
        try:
            message_data = {
                'caseId': case_id,
                'userId': user_id,
                'message': message,
                'type': message_type,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'metadata': metadata or {}
            }
            
            # Add agent-specific fields
            if message_type == 'ai':
                message_data['agent'] = metadata.get('agent', 'general') if metadata else 'general'
                message_data['confidence'] = metadata.get('confidence', 0.0) if metadata else 0.0
            
            # Save to Firestore
            doc_ref = self.firestore_client.collection('chat_messages').add(message_data)
            
            logger.info(f"💾 Saved {message_type} message for case {case_id}")
            return doc_ref[1].id
            
        except Exception as e:
            logger.error(f"❌ Error saving message: {e}")
            return f"error_{int(time.time())}"

    def clear_chat_history(self, case_id: str, user_id: str) -> int:
        """Clear chat history for a case"""
        try:
            # Verify user has access
            if not self.verify_case_access(case_id, user_id):
                return 0
            
            # Get all messages for the case
            messages_query = self.firestore_client.collection('chat_messages')\
                .where('caseId', '==', case_id)
            
            messages = messages_query.get()
            
            # Delete messages in batches
            batch_size = 500
            deleted_count = 0
            
            batch = self.firestore_client.batch()
            batch_count = 0
            
            for msg in messages:
                batch.delete(msg.reference)
                batch_count += 1
                deleted_count += 1
                
                if batch_count >= batch_size:
                    batch.commit()
                    batch = self.firestore_client.batch()
                    batch_count = 0
            
            # Commit remaining deletions
            if batch_count > 0:
                batch.commit()
            
            logger.info(f"🗑️ Cleared {deleted_count} messages for case {case_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Error clearing chat history: {e}")
            return 0

    def get_conversation_context(self, case_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation context for AI agents"""
        try:
            messages_query = self.firestore_client.collection('chat_messages')\
                .where('caseId', '==', case_id)\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(limit)
            
            messages = []
            for doc in messages_query.get():
                msg_data = doc.to_dict()
                messages.append({
                    'type': msg_data.get('type', 'user'),
                    'message': msg_data.get('message', ''),
                    'agent': msg_data.get('agent'),
                    'timestamp': msg_data.get('timestamp'),
                    'userId': msg_data.get('userId')
                })
            
            # Return in chronological order
            messages.reverse()
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error getting conversation context: {e}")
            return []

    def log_user_activity(self, case_id: str, user_id: str, activity: str, details: Dict[str, Any] = None):
        """Log user activity for analytics"""
        try:
            activity_data = {
                'caseId': case_id,
                'userId': user_id,
                'activity': activity,
                'details': details or {},
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            
            self.firestore_client.collection('user_activities').add(activity_data)
            
        except Exception as e:
            logger.error(f"❌ Error logging user activity: {e}")

    def get_active_users(self, case_id: str) -> List[Dict[str, Any]]:
        """Get list of users currently active in the case"""
        try:
            # Get recent activities (last 5 minutes)
            five_minutes_ago = time.time() - 300
            
            activities_query = self.firestore_client.collection('user_activities')\
                .where('caseId', '==', case_id)\
                .where('timestamp', '>=', five_minutes_ago)\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)
            
            activities = activities_query.get()
            
            active_users = {}
            for activity in activities:
                activity_data = activity.to_dict()
                user_id = activity_data.get('userId')
                
                if user_id not in active_users:
                    active_users[user_id] = {
                        'userId': user_id,
                        'lastActivity': activity_data.get('timestamp'),
                        'activityType': activity_data.get('activity')
                    }
            
            return list(active_users.values())
            
        except Exception as e:
            logger.error(f"❌ Error getting active users: {e}")
            return []

    def get_chat_statistics(self, case_id: str) -> Dict[str, Any]:
        """Get chat statistics for a case"""
        try:
            messages_query = self.firestore_client.collection('chat_messages')\
                .where('caseId', '==', case_id)
            
            messages = messages_query.get()
            
            stats = {
                'totalMessages': len(messages),
                'userMessages': 0,
                'aiMessages': 0,
                'agents': {},
                'mostActiveDay': None,
                'avgMessagesPerDay': 0
            }
            
            message_dates = {}
            
            for msg in messages:
                msg_data = msg.to_dict()
                msg_type = msg_data.get('type', 'user')
                
                if msg_type == 'user':
                    stats['userMessages'] += 1
                elif msg_type == 'ai':
                    stats['aiMessages'] += 1
                    agent = msg_data.get('agent', 'unknown')
                    stats['agents'][agent] = stats['agents'].get(agent, 0) + 1
                
                # Track daily message counts
                timestamp = msg_data.get('timestamp')
                if timestamp:
                    date_str = timestamp.strftime('%Y-%m-%d') if hasattr(timestamp, 'strftime') else 'unknown'
                    message_dates[date_str] = message_dates.get(date_str, 0) + 1
            
            # Find most active day
            if message_dates:
                most_active = max(message_dates.items(), key=lambda x: x[1])
                stats['mostActiveDay'] = {'date': most_active[0], 'count': most_active[1]}
                stats['avgMessagesPerDay'] = round(sum(message_dates.values()) / len(message_dates), 1)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting chat statistics: {e}")
            return {'error': 'Failed to get chat statistics'}