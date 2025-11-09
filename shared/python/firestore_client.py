"""
Firestore Client for Legal Case AI - Python Implementation
Provides standardized database operations for Python services
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
import json

from google.cloud import firestore
from google.cloud.firestore import SERVER_TIMESTAMP, Increment, ArrayUnion, ArrayRemove

logger = logging.getLogger(__name__)

class FirestoreClient:
    """Firestore client wrapper for Legal Case AI Python services"""
    
    def __init__(self, project_id: Optional[str] = None, database_id: str = "(default)"):
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.database_id = database_id
        
        # Initialize Firestore client
        self.db = firestore.Client(project=self.project_id, database=self.database_id)
        
        # Collection references for easy access
        self.collections = {
            'cases': self.db.collection('cases'),
            'documents': self.db.collection('documents'),
            'extracted_documents': self.db.collection('extracted_documents'),
            'document_analysis': self.db.collection('document_analysis'),
            'case_analysis': self.db.collection('case_analysis'),
            'chat_messages': self.db.collection('chat_messages'),
            'users': self.db.collection('users'),
            'user_activities': self.db.collection('user_activities'),
            'pdf_reports': self.db.collection('pdf_reports'),
            'extraction_errors': self.db.collection('extraction_errors'),
            'system_logs': self.db.collection('system_logs'),
            'notifications': self.db.collection('notifications')
        }
        
        logger.info(f"✅ Firestore client initialized for project: {self.project_id}")

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            # Try to read from a collection to test connection
            list(self.collections['cases'].limit(1).get())
            logger.info("✅ Firestore connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ Firestore connection test failed: {e}")
            raise

    # ==================== CASE OPERATIONS ====================

    def create_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new case"""
        try:
            case_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            new_case = {
                'id': case_id,
                'title': case_data['title'],
                'type': case_data.get('type', 'general'),
                'description': case_data.get('description', ''),
                'status': 'active',
                'priority': case_data.get('priority', 'medium'),
                'createdBy': case_data['createdBy'],
                'createdAt': now,
                'updatedAt': now,
                'documentCount': 0,
                'analysisCount': 0,
                'extractionStatus': 'pending',
                'analysisStatus': 'pending',
                'tags': case_data.get('tags', []),
                'metadata': case_data.get('metadata', {})
            }
            
            # Set document with specific ID
            self.collections['cases'].document(case_id).set(new_case)
            
            # Log activity
            self.log_user_activity(case_data['createdBy'], 'case_created', {
                'caseId': case_id,
                'caseTitle': case_data['title']
            })
            
            logger.info(f"✅ Case created: {case_id}")
            return new_case
            
        except Exception as e:
            logger.error(f"❌ Error creating case: {e}")
            raise

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get case by ID"""
        try:
            doc = self.collections['cases'].document(case_id).get()
            
            if not doc.exists:
                return None
            
            case_data = doc.to_dict()
            case_data['id'] = doc.id
            return case_data
            
        except Exception as e:
            logger.error(f"❌ Error getting case {case_id}: {e}")
            raise

    def update_case(self, case_id: str, update_data: Dict[str, Any]) -> bool:
        """Update case"""
        try:
            updates = {
                **update_data,
                'updatedAt': datetime.now(timezone.utc)
            }
            
            self.collections['cases'].document(case_id).update(updates)
            
            logger.info(f"✅ Case updated: {case_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating case {case_id}: {e}")
            raise

    def get_user_cases(self, user_id: str, options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get cases for user with pagination"""
        try:
            if options is None:
                options = {}
                
            limit = options.get('limit', 20)
            offset = options.get('offset', 0)
            order_by = options.get('orderBy', 'updatedAt')
            order_direction = options.get('orderDirection', firestore.Query.DESCENDING)
            status = options.get('status')
            case_type = options.get('type')
            
            query = self.collections['cases'].where('createdBy', '==', user_id)
            
            if status:
                query = query.where('status', '==', status)
            
            if case_type:
                query = query.where('type', '==', case_type)
            
            query = query.order_by(order_by, direction=order_direction)
            query = query.limit(limit).offset(offset)
            
            docs = query.get()
            
            cases = []
            for doc in docs:
                case_data = doc.to_dict()
                case_data['id'] = doc.id
                cases.append(case_data)
            
            return cases
            
        except Exception as e:
            logger.error(f"❌ Error getting user cases for {user_id}: {e}")
            raise

    def delete_case(self, case_id: str, user_id: str) -> bool:
        """Delete case (soft delete)"""
        try:
            self.collections['cases'].document(case_id).update({
                'status': 'deleted',
                'deletedAt': datetime.now(timezone.utc),
                'deletedBy': user_id,
                'updatedAt': datetime.now(timezone.utc)
            })
            
            # Log activity
            self.log_user_activity(user_id, 'case_deleted', {'caseId': case_id})
            
            logger.info(f"✅ Case deleted: {case_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting case {case_id}: {e}")
            raise

    # ==================== DOCUMENT OPERATIONS ====================

    def create_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create document record"""
        try:
            document_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            new_document = {
                'id': document_id,
                'filename': document_data['filename'],
                'originalName': document_data.get('originalName', document_data['filename']),
                'contentType': document_data['contentType'],
                'size': document_data['size'],
                'caseId': document_data['caseId'],
                'storageKey': document_data['storageKey'],
                'checksum': document_data.get('checksum'),
                'uploadedBy': document_data['uploadedBy'],
                'uploadedAt': now,
                'createdAt': now,
                'updatedAt': now,
                'status': 'uploaded',
                'extractionStatus': 'pending',
                'analysisStatus': 'pending',
                'description': document_data.get('description', ''),
                'tags': document_data.get('tags', []),
                'version': 1,
                'metadata': document_data.get('metadata', {})
            }
            
            # Set document
            self.collections['documents'].document(document_id).set(new_document)
            
            # Update case document count
            self.collections['cases'].document(document_data['caseId']).update({
                'documentCount': Increment(1),
                'updatedAt': now
            })
            
            # Log activity
            self.log_user_activity(document_data['uploadedBy'], 'document_uploaded', {
                'documentId': document_id,
                'filename': document_data['filename'],
                'caseId': document_data['caseId']
            })
            
            logger.info(f"✅ Document created: {document_id}")
            return new_document
            
        except Exception as e:
            logger.error(f"❌ Error creating document: {e}")
            raise

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            doc = self.collections['documents'].document(document_id).get()
            
            if not doc.exists:
                return None
            
            document_data = doc.to_dict()
            document_data['id'] = doc.id
            return document_data
            
        except Exception as e:
            logger.error(f"❌ Error getting document {document_id}: {e}")
            raise

    def get_case_documents(self, case_id: str, options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get documents for case"""
        try:
            if options is None:
                options = {}
                
            limit = options.get('limit', 50)
            order_by = options.get('orderBy', 'uploadedAt')
            order_direction = options.get('orderDirection', firestore.Query.DESCENDING)
            status = options.get('status')
            
            query = self.collections['documents'].where('caseId', '==', case_id)
            
            if status:
                query = query.where('status', '==', status)
            else:
                # Exclude deleted documents by default
                query = query.where('status', '!=', 'deleted')
            
            query = query.order_by(order_by, direction=order_direction).limit(limit)
            
            docs = query.get()
            
            documents = []
            for doc in docs:
                document_data = doc.to_dict()
                document_data['id'] = doc.id
                documents.append(document_data)
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ Error getting case documents for {case_id}: {e}")
            raise

    def update_document_status(self, document_id: str, status: str, additional_data: Optional[Dict[str, Any]] = None) -> bool:
        """Update document status"""
        try:
            updates = {
                'status': status,
                'updatedAt': datetime.now(timezone.utc)
            }
            
            if additional_data:
                updates.update(additional_data)
            
            self.collections['documents'].document(document_id).update(updates)
            
            logger.info(f"✅ Document status updated: {document_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating document status {document_id}: {e}")
            raise

    # ==================== EXTRACTED DOCUMENTS OPERATIONS ====================

    def save_extracted_document(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save extracted document data"""
        try:
            extracted_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            extracted_document = {
                'id': extracted_id,
                'documentId': extracted_data['documentId'],
                'caseId': extracted_data['caseId'],
                'filename': extracted_data['filename'],
                'text': extracted_data['text'],
                'pageCount': extracted_data.get('pageCount', 0),
                'wordCount': extracted_data.get('wordCount', 0),
                'characterCount': extracted_data.get('characterCount', 0),
                'title': extracted_data.get('title', ''),
                'language': extracted_data.get('language', 'unknown'),
                'confidence': extracted_data.get('confidence', 0),
                'method': extracted_data.get('method', 'unknown'),
                'processingTime': extracted_data.get('processingTime', 0),
                'extractedBy': extracted_data['extractedBy'],
                'createdAt': now,
                'metadata': extracted_data.get('metadata', {})
            }
            
            self.collections['extracted_documents'].document(extracted_id).set(extracted_document)
            
            logger.info(f"✅ Extracted document saved: {extracted_id}")
            return extracted_document
            
        except Exception as e:
            logger.error(f"❌ Error saving extracted document: {e}")
            raise

    def get_extracted_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get extracted document by document ID"""
        try:
            docs = self.collections['extracted_documents']\
                .where('documentId', '==', document_id)\
                .order_by('createdAt', direction=firestore.Query.DESCENDING)\
                .limit(1).get()
            
            if not docs:
                return None
            
            doc = docs[0]
            extracted_data = doc.to_dict()
            extracted_data['id'] = doc.id
            return extracted_data
            
        except Exception as e:
            logger.error(f"❌ Error getting extracted document for {document_id}: {e}")
            raise

    # ==================== ANALYSIS OPERATIONS ====================

    def save_document_analysis(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save document analysis"""
        try:
            analysis_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            analysis = {
                'id': analysis_id,
                'documentId': analysis_data['documentId'],
                'caseId': analysis_data['caseId'],
                'analysisType': analysis_data.get('analysisType', 'full'),
                'summary': analysis_data.get('summary', ''),
                'keyPoints': analysis_data.get('keyPoints', []),
                'legalRelevance': analysis_data.get('legalRelevance', ''),
                'entities': analysis_data.get('entities', {}),
                'sentiment': analysis_data.get('sentiment', {}),
                'readability': analysis_data.get('readability', {}),
                'recommendations': analysis_data.get('recommendations', []),
                'confidence': analysis_data.get('confidence', 0),
                'processingTime': analysis_data.get('processingTime', 0),
                'analyzedBy': analysis_data['analyzedBy'],
                'analyzedAt': now,
                'metadata': analysis_data.get('metadata', {})
            }
            
            self.collections['document_analysis'].document(analysis_id).set(analysis)
            
            logger.info(f"✅ Document analysis saved: {analysis_id}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error saving document analysis: {e}")
            raise

    def save_case_analysis(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save case analysis"""
        try:
            analysis_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            analysis = {
                'id': analysis_id,
                'caseId': analysis_data['caseId'],
                'analysisType': analysis_data.get('analysisType', 'comprehensive'),
                'executiveSummary': analysis_data.get('executiveSummary', ''),
                'keyFindings': analysis_data.get('keyFindings', []),
                'strengthsWeaknesses': analysis_data.get('strengthsWeaknesses', {}),
                'legalIssues': analysis_data.get('legalIssues', []),
                'recommendations': analysis_data.get('recommendations', []),
                'riskAssessment': analysis_data.get('riskAssessment', {}),
                'timeline': analysis_data.get('timeline', []),
                'strategicAdvice': analysis_data.get('strategicAdvice', ''),
                'confidence': analysis_data.get('confidence', 0),
                'processingTime': analysis_data.get('processingTime', 0),
                'documentCount': analysis_data.get('documentCount', 0),
                'analyzedBy': analysis_data['analyzedBy'],
                'analyzedAt': now,
                'version': '1.0',
                'metadata': analysis_data.get('metadata', {})
            }
            
            self.collections['case_analysis'].document(analysis_id).set(analysis)
            
            # Update case analysis count
            self.collections['cases'].document(analysis_data['caseId']).update({
                'analysisCount': Increment(1),
                'lastAnalyzedAt': now,
                'analysisStatus': 'completed',
                'updatedAt': now
            })
            
            logger.info(f"✅ Case analysis saved: {analysis_id}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error saving case analysis: {e}")
            raise

    # ==================== CHAT OPERATIONS ====================

    def save_chat_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save chat message"""
        try:
            message_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            message = {
                'id': message_id,
                'caseId': message_data['caseId'],
                'userId': message_data['userId'],
                'message': message_data['message'],
                'type': message_data.get('type', 'user'),  # 'user' or 'ai'
                'agent': message_data.get('agent'),
                'confidence': message_data.get('confidence'),
                'timestamp': now,
                'metadata': message_data.get('metadata', {})
            }
            
            self.collections['chat_messages'].document(message_id).set(message)
            
            return message
            
        except Exception as e:
            logger.error(f"❌ Error saving chat message: {e}")
            raise

    def get_chat_messages(self, case_id: str, options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get chat messages for case"""
        try:
            if options is None:
                options = {}
                
            limit = options.get('limit', 50)
            offset = options.get('offset', 0)
            order_direction = options.get('orderDirection', firestore.Query.DESCENDING)
            
            query = self.collections['chat_messages']\
                .where('caseId', '==', case_id)\
                .order_by('timestamp', direction=order_direction)\
                .limit(limit)\
                .offset(offset)
            
            docs = query.get()
            
            messages = []
            for doc in docs:
                message_data = doc.to_dict()
                message_data['id'] = doc.id
                messages.append(message_data)
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error getting chat messages for case {case_id}: {e}")
            raise

    def clear_chat_messages(self, case_id: str, user_id: str) -> int:
        """Clear chat messages for case"""
        try:
            docs = self.collections['chat_messages']\
                .where('caseId', '==', case_id).get()
            
            batch = self.db.batch()
            delete_count = 0
            
            for doc in docs:
                batch.delete(doc.reference)
                delete_count += 1
            
            batch.commit()
            
            # Log activity
            self.log_user_activity(user_id, 'chat_cleared', {
                'caseId': case_id,
                'messageCount': delete_count
            })
            
            logger.info(f"✅ Cleared {delete_count} chat messages for case {case_id}")
            return delete_count
            
        except Exception as e:
            logger.error(f"❌ Error clearing chat messages for case {case_id}: {e}")
            raise

    # ==================== USER OPERATIONS ====================

    def save_user_profile(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update user profile"""
        try:
            now = datetime.now(timezone.utc)
            user_id = user_data['uid']
            
            user_profile = {
                'uid': user_id,
                'email': user_data['email'],
                'displayName': user_data.get('displayName', ''),
                'photoURL': user_data.get('photoURL', ''),
                'role': user_data.get('role', 'user'),
                'preferences': user_data.get('preferences', {}),
                'lastLoginAt': now,
                'updatedAt': now,
                'createdAt': user_data.get('createdAt', now),
                'isActive': True,
                'metadata': user_data.get('metadata', {})
            }
            
            # Use merge=True to update existing profile or create new one
            self.collections['users'].document(user_id).set(user_profile, merge=True)
            
            logger.info(f"✅ User profile saved: {user_id}")
            return user_profile
            
        except Exception as e:
            logger.error(f"❌ Error saving user profile: {e}")
            raise

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        try:
            doc = self.collections['users'].document(user_id).get()
            
            if not doc.exists:
                return None
            
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            return user_data
            
        except Exception as e:
            logger.error(f"❌ Error getting user profile {user_id}: {e}")
            raise

    def log_user_activity(self, user_id: str, activity: str, details: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Log user activity"""
        try:
            now = datetime.now(timezone.utc)
            activity_id = str(uuid.uuid4())
            
            if details is None:
                details = {}
            
            activity_log = {
                'id': activity_id,
                'userId': user_id,
                'activity': activity,
                'details': details,
                'timestamp': now,
                'ipAddress': details.get('ipAddress'),
                'userAgent': details.get('userAgent')
            }
            
            self.collections['user_activities'].document(activity_id).set(activity_log)
            
            return activity_id
            
        except Exception as e:
            logger.error(f"❌ Error logging user activity: {e}")
            # Don't raise error for logging failures
            return None

    # ==================== NOTIFICATION OPERATIONS ====================

    def create_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create notification"""
        try:
            now = datetime.now(timezone.utc)
            notification_id = str(uuid.uuid4())
            
            notification = {
                'id': notification_id,
                'userId': notification_data['userId'],
                'title': notification_data['title'],
                'message': notification_data['message'],
                'type': notification_data.get('type', 'info'),
                'caseId': notification_data.get('caseId'),
                'documentId': notification_data.get('documentId'),
                'isRead': False,
                'createdAt': now,
                'readAt': None,
                'metadata': notification_data.get('metadata', {})
            }
            
            self.collections['notifications'].document(notification_id).set(notification)
            
            logger.info(f"✅ Notification created: {notification_id}")
            return notification
            
        except Exception as e:
            logger.error(f"❌ Error creating notification: {e}")
            raise

    def get_user_notifications(self, user_id: str, options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get user notifications"""
        try:
            if options is None:
                options = {}
                
            limit = options.get('limit', 20)
            unread_only = options.get('unreadOnly', False)
            order_direction = options.get('orderDirection', firestore.Query.DESCENDING)
            
            query = self.collections['notifications'].where('userId', '==', user_id)
            
            if unread_only:
                query = query.where('isRead', '==', False)
            
            query = query.order_by('createdAt', direction=order_direction).limit(limit)
            
            docs = query.get()
            
            notifications = []
            for doc in docs:
                notification_data = doc.to_dict()
                notification_data['id'] = doc.id
                notifications.append(notification_data)
            
            return notifications
            
        except Exception as e:
            logger.error(f"❌ Error getting notifications for user {user_id}: {e}")
            raise

    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        try:
            self.collections['notifications'].document(notification_id).update({
                'isRead': True,
                'readAt': datetime.now(timezone.utc)
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error marking notification read {notification_id}: {e}")
            raise

    # ==================== PDF REPORT OPERATIONS ====================

    def save_pdf_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save PDF report metadata"""
        try:
            report_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            report = {
                'id': report_id,
                'caseId': report_data['caseId'],
                'userId': report_data['userId'],
                'reportType': report_data['reportType'],
                'storageKey': report_data['storageKey'],
                'filename': report_data['filename'],
                'generatedAt': now,
                'status': report_data.get('status', 'completed'),
                'fileSize': report_data.get('fileSize', 0),
                'metadata': report_data.get('metadata', {})
            }
            
            self.collections['pdf_reports'].document(report_id).set(report)
            
            logger.info(f"✅ PDF report saved: {report_id}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Error saving PDF report: {e}")
            raise

    def get_pdf_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get PDF report by ID"""
        try:
            doc = self.collections['pdf_reports'].document(report_id).get()
            
            if not doc.exists:
                return None
            
            report_data = doc.to_dict()
            report_data['id'] = doc.id
            return report_data
            
        except Exception as e:
            logger.error(f"❌ Error getting PDF report {report_id}: {e}")
            raise

    def get_case_reports(self, case_id: str, options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get reports for case"""
        try:
            if options is None:
                options = {}
                
            limit = options.get('limit', 20)
            order_direction = options.get('orderDirection', firestore.Query.DESCENDING)
            
            query = self.collections['pdf_reports']\
                .where('caseId', '==', case_id)\
                .order_by('generatedAt', direction=order_direction)\
                .limit(limit)
            
            docs = query.get()
            
            reports = []
            for doc in docs:
                report_data = doc.to_dict()
                report_data['id'] = doc.id
                reports.append(report_data)
            
            return reports
            
        except Exception as e:
            logger.error(f"❌ Error getting case reports for {case_id}: {e}")
            raise

    # ==================== ERROR LOGGING ====================

    def log_extraction_error(self, error_data: Dict[str, Any]) -> str:
        """Log extraction error"""
        try:
            error_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            error_log = {
                'id': error_id,
                'documentId': error_data.get('documentId'),
                'caseId': error_data.get('caseId'),
                'errorMessage': error_data['errorMessage'],
                'errorDetails': error_data.get('errorDetails', {}),
                'service': error_data.get('service', 'unknown'),
                'timestamp': now,
                'metadata': error_data.get('metadata', {})
            }
            
            self.collections['extraction_errors'].document(error_id).set(error_log)
            
            logger.info(f"✅ Extraction error logged: {error_id}")
            return error_id
            
        except Exception as e:
            logger.error(f"❌ Error logging extraction error: {e}")
            raise

    def log_system_event(self, event_data: Dict[str, Any]) -> str:
        """Log system event"""
        try:
            log_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            system_log = {
                'id': log_id,
                'service': event_data['service'],
                'event': event_data['event'],
                'level': event_data.get('level', 'info'),
                'message': event_data['message'],
                'details': event_data.get('details', {}),
                'timestamp': now,
                'userId': event_data.get('userId'),
                'metadata': event_data.get('metadata', {})
            }
            
            self.collections['system_logs'].document(log_id).set(system_log)
            
            return log_id
            
        except Exception as e:
            logger.error(f"❌ Error logging system event: {e}")
            raise

    # ==================== UTILITY METHODS ====================

    def get_server_timestamp(self):
        """Get server timestamp"""
        return SERVER_TIMESTAMP

    def get_current_timestamp(self) -> datetime:
        """Get current timestamp"""
        return datetime.now(timezone.utc)

    def create_batch(self):
        """Create batch operation"""
        return self.db.batch()

    def run_transaction(self, update_function):
        """Execute transaction"""
        return self.db.run_transaction(update_function)

    def get_collection(self, collection_name: str):
        """Get collection reference"""
        return self.db.collection(collection_name)

    def increment(self, value: int = 1):
        """Create increment field value"""
        return Increment(value)

    def array_union(self, *values):
        """Create array union field value"""
        return ArrayUnion(values)

    def array_remove(self, *values):
        """Create array remove field value"""
        return ArrayRemove(values)

    def close(self):
        """Close database connection"""
        try:
            # Firestore client doesn't have an explicit close method
            # but we can clear references
            self.db = None
            self.collections = {}
            logger.info("✅ Firestore connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing Firestore connection: {e}")

    # ==================== SEARCH AND QUERY HELPERS ====================

    def search_documents(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search documents with various filters"""
        try:
            query = self.collections['documents']
            
            # Apply filters
            if search_params.get('caseId'):
                query = query.where('caseId', '==', search_params['caseId'])
            
            if search_params.get('uploadedBy'):
                query = query.where('uploadedBy', '==', search_params['uploadedBy'])
            
            if search_params.get('contentType'):
                query = query.where('contentType', '==', search_params['contentType'])
            
            if search_params.get('status'):
                query = query.where('status', '==', search_params['status'])
            
            # Date range filter
            if search_params.get('startDate'):
                query = query.where('uploadedAt', '>=', search_params['startDate'])
            
            if search_params.get('endDate'):
                query = query.where('uploadedAt', '<=', search_params['endDate'])
            
            # Ordering and limiting
            order_by = search_params.get('orderBy', 'uploadedAt')
            order_direction = search_params.get('orderDirection', firestore.Query.DESCENDING)
            limit = search_params.get('limit', 50)
            
            query = query.order_by(order_by, direction=order_direction).limit(limit)
            
            docs = query.get()
            
            documents = []
            for doc in docs:
                document_data = doc.to_dict()
                document_data['id'] = doc.id
                documents.append(document_data)
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ Error searching documents: {e}")
            raise

    def get_analytics_data(self, user_id: str, date_range: Optional[Dict[str, datetime]] = None) -> Dict[str, Any]:
        """Get analytics data for user"""
        try:
            analytics = {
                'totalCases': 0,
                'totalDocuments': 0,
                'totalAnalyses': 0,
                'recentActivity': [],
                'casesByStatus': {},
                'documentsProcessed': 0
            }
            
            # Get user cases
            cases = self.get_user_cases(user_id, {'limit': 1000})
            analytics['totalCases'] = len(cases)
            
            # Count cases by status
            for case in cases:
                status = case.get('status', 'unknown')
                analytics['casesByStatus'][status] = analytics['casesByStatus'].get(status, 0) + 1
            
            # Get total documents
            all_case_ids = [case['id'] for case in cases]
            for case_id in all_case_ids:
                docs = self.get_case_documents(case_id, {'limit': 1000})
                analytics['totalDocuments'] += len(docs)
                analytics['documentsProcessed'] += len([d for d in docs if d.get('extractionStatus') == 'completed'])
            
            # Get recent activities
            activities_query = self.collections['user_activities']\
                .where('userId', '==', user_id)\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(10)
            
            activities = activities_query.get()
            for activity_doc in activities:
                activity_data = activity_doc.to_dict()
                activity_data['id'] = activity_doc.id
                analytics['recentActivity'].append(activity_data)
            
            return analytics
            
        except Exception as e:
            logger.error(f"❌ Error getting analytics data: {e}")
            raise

    def cleanup_old_data(self, days_old: int = 30) -> Dict[str, int]:
        """Clean up old data (utility function)"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            cleanup_stats = {
                'activities_deleted': 0,
                'logs_deleted': 0,
                'notifications_deleted': 0
            }
            
            # Clean old user activities
            old_activities = self.collections['user_activities']\
                .where('timestamp', '<', cutoff_date)\
                .limit(500).get()
            
            batch = self.db.batch()
            batch_count = 0
            
            for activity in old_activities:
                batch.delete(activity.reference)
                batch_count += 1
                cleanup_stats['activities_deleted'] += 1
                
                if batch_count >= 500:
                    batch.commit()
                    batch = self.db.batch()
                    batch_count = 0
            
            if batch_count > 0:
                batch.commit()
            
            # Clean old system logs
            old_logs = self.collections['system_logs']\
                .where('timestamp', '<', cutoff_date)\
                .limit(500).get()
            
            batch = self.db.batch()
            batch_count = 0
            
            for log in old_logs:
                batch.delete(log.reference)
                batch_count += 1
                cleanup_stats['logs_deleted'] += 1
                
                if batch_count >= 500:
                    batch.commit()
                    batch = self.db.batch()
                    batch_count = 0
            
            if batch_count > 0:
                batch.commit()
            
            # Clean old read notifications
            old_notifications = self.collections['notifications']\
                .where('isRead', '==', True)\
                .where('createdAt', '<', cutoff_date)\
                .limit(500).get()
            
            batch = self.db.batch()
            batch_count = 0
            
            for notification in old_notifications:
                batch.delete(notification.reference)
                batch_count += 1
                cleanup_stats['notifications_deleted'] += 1
                
                if batch_count >= 500:
                    batch.commit()
                    batch = self.db.batch()
                    batch_count = 0
            
            if batch_count > 0:
                batch.commit()
            
            logger.info(f"✅ Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
            raise