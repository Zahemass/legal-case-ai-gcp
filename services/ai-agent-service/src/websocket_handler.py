import logging
import time
import datetime
from typing import Dict, Any, List, Optional
from google.cloud import firestore
from google.api_core.exceptions import DeadlineExceeded, NotFound, GoogleAPICallError
from google.api_core.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------
# Utility
# ---------------------------
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


class WebSocketHandler:
    """Handles WebSocket-related operations for AI agent chat"""

    def __init__(self, orchestrator, firestore_client):
        self.orchestrator = orchestrator
        self.firestore_client = firestore_client
        self.case_access_cache = {}  # ✅ Cache user→case verifications
        self.retry_policy = Retry(initial=1.0, maximum=10.0, multiplier=2.0, deadline=15.0)
        logger.info("✅ WebSocketHandler initialized")

    # -----------------------------------------------------
    # 🔐 CASE ACCESS
    # -----------------------------------------------------
    def verify_case_access(self, case_id: str, user_id: str) -> bool:
        """Verify user has access to the case (optimized + retry + timeout + cache)"""
        try:
            if not case_id or not user_id:
                logger.warning("⚠️ Missing case_id or user_id in verify_case_access()")
                return False

            cache_key = f"{user_id}:{case_id}"
            cached = self.case_access_cache.get(cache_key)
            if cached and time.time() - cached["ts"] < 600:  # 10-min cache
                return cached["access"]

            case_ref = self.firestore_client.collection("cases").document(case_id)

            # ✅ Retry + Timeout to avoid 300s Firestore hang
            case_doc = case_ref.get(retry=self.retry_policy, timeout=8)

            if not case_doc.exists:
                logger.warning(f"⚠️ Case {case_id} not found")
                self.case_access_cache[cache_key] = {"access": False, "ts": time.time()}
                return False

            case_data = case_doc.to_dict()
            created_by = case_data.get("createdBy")

            # ✅ Only owner access for now
            has_access = created_by == user_id

            self.case_access_cache[cache_key] = {"access": has_access, "ts": time.time()}

            if has_access:
                logger.info(f"✅ Verified access: user {user_id} owns case {case_id}")
                return True

            logger.warning(f"🚫 User {user_id} denied access to case {case_id}")
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

    # -----------------------------------------------------
    # 📁 CASE INFO
    # -----------------------------------------------------
    def get_case_info(self, case_id: str) -> Dict[str, Any]:
        """Get case information for client"""
        try:
            case_ref = self.firestore_client.collection("cases").document(case_id)
            case_doc = case_ref.get(retry=self.retry_policy, timeout=8)

            if not case_doc.exists:
                return {"error": "Case not found"}

            case_data = case_doc.to_dict()

            docs_query = (
                self.firestore_client.collection("documents")
                .where("caseId", "==", case_id)
                .where("status", "!=", "deleted")
            )

            docs = docs_query.get(retry=self.retry_policy, timeout=8)
            doc_count = len(docs)

            return to_json_serializable(
                {
                    "id": case_id,
                    "title": case_data.get("title", "Untitled Case"),
                    "type": case_data.get("type", "general"),
                    "status": case_data.get("status", "active"),
                    "priority": case_data.get("priority", "medium"),
                    "description": case_data.get("description", ""),
                    "createdAt": case_data.get("createdAt"),
                    "updatedAt": case_data.get("updatedAt"),
                    "documentCount": doc_count,
                    "analysisCount": case_data.get("analysisCount", 0),
                }
            )

        except Exception as e:
            logger.error(f"❌ Error getting case info: {e}")
            return {"error": "Failed to get case information"}

    # -----------------------------------------------------
    # 💬 CHAT HISTORY
    # -----------------------------------------------------
    def get_chat_history(self, case_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get chat history for a case"""
        try:
            messages_query = (
                self.firestore_client.collection("chat_messages")
                .where("caseId", "==", case_id)
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .offset(offset)
            )

            messages = []
            for doc in messages_query.get(retry=self.retry_policy, timeout=8):
                msg_data = doc.to_dict()
                messages.append(
                    {
                        "id": doc.id,
                        "caseId": msg_data.get("caseId"),
                        "userId": msg_data.get("userId"),
                        "message": msg_data.get("message"),
                        "type": msg_data.get("type", "user"),
                        "agent": msg_data.get("agent"),
                        "timestamp": msg_data.get("timestamp"),
                        "confidence": msg_data.get("confidence"),
                        "metadata": msg_data.get("metadata", {}),
                    }
                )

            messages.reverse()
            return to_json_serializable(messages)

        except Exception as e:
            logger.error(f"❌ Error getting chat history: {e}")
            return []

    # -----------------------------------------------------
    # 💾 SAVE MESSAGE
    # -----------------------------------------------------
    def save_message(
        self,
        case_id: str,
        user_id: str,
        message: str,
        message_type: str = "user",
        metadata: Dict[str, Any] = None,
    ) -> str:
        """Save a chat message to Firestore"""
        try:
            message_data = {
                "caseId": case_id,
                "userId": user_id,
                "message": message,
                "type": message_type,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "metadata": metadata or {},
            }

            if message_type == "ai":
                message_data["agent"] = metadata.get("agent", "general") if metadata else "general"
                message_data["confidence"] = metadata.get("confidence", 0.0) if metadata else 0.0

            doc_ref = self.firestore_client.collection("chat_messages").add(message_data, timeout=8)
            logger.info(f"💾 Saved {message_type} message for case {case_id}")
            return doc_ref[1].id

        except Exception as e:
            logger.error(f"❌ Error saving message: {e}")
            return f"error_{int(time.time())}"

    # -----------------------------------------------------
    # 🧹 CLEAR CHAT
    # -----------------------------------------------------
    def clear_chat_history(self, case_id: str, user_id: str) -> int:
        """Clear chat history for a case"""
        try:
            if not self.verify_case_access(case_id, user_id):
                return 0

            messages_query = self.firestore_client.collection("chat_messages").where("caseId", "==", case_id)
            messages = messages_query.get(retry=self.retry_policy, timeout=10)

            batch_size = 500
            deleted_count = 0
            batch = self.firestore_client.batch()

            for i, msg in enumerate(messages, start=1):
                batch.delete(msg.reference)
                deleted_count += 1
                if i % batch_size == 0:
                    batch.commit()
                    batch = self.firestore_client.batch()

            if deleted_count % batch_size != 0:
                batch.commit()

            logger.info(f"🗑️ Cleared {deleted_count} messages for case {case_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"❌ Error clearing chat history: {e}")
            return 0
