# services/extraction-service/src/firestore_client.py
import logging
from google.cloud import firestore
from google.cloud.firestore import SERVER_TIMESTAMP
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class FirestoreClient:
    """Firestore client for document extraction service"""
    
    def __init__(self):
        try:
            self.db = firestore.Client()
            logger.info("✅ Firestore client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firestore client: {e}")
            raise

    def test_connection(self):
        """Test Firestore connection"""
        try:
            # Try to read a collection to test connection
            collections = list(self.db.collections())
            logger.info("✅ Firestore connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ Firestore connection test failed: {e}")
            raise

    def update_document_status(self, document_id: str, status: str, **kwargs):
        """Update document extraction status"""
        try:
            doc_ref = self.db.collection('documents').document(document_id)
            
            update_data = {
                'extractionStatus': status,
                'updatedAt': SERVER_TIMESTAMP
            }
            
            # Add any additional fields
            for key, value in kwargs.items():
                if value is not None:
                    update_data[key] = value
            
            doc_ref.update(update_data)
            logger.info(f"✅ Updated document {document_id} status to: {status}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update document status for {document_id}: {e}")
            raise

    def save_extracted_document(self, extraction_data: Dict[str, Any]) -> str:
        """Save extracted document data to Firestore"""
        try:
            doc_ref = self.db.collection('extracted_documents').document()
            doc_ref.set(extraction_data)
            
            logger.info(f"✅ Saved extracted document data: {doc_ref.id}")
            return doc_ref.id
            
        except Exception as e:
            logger.error(f"❌ Failed to save extracted document data: {e}")
            raise

    def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document information from Firestore"""
        try:
            doc_ref = self.db.collection('documents').document(document_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                logger.warning(f"⚠️ Document {document_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get document info for {document_id}: {e}")
            raise

    def log_extraction_error(self, document_id: str, error_message: str, error_details: Dict[str, Any] = None):
        """Log extraction error to Firestore"""
        try:
            error_data = {
                'documentId': document_id,
                'errorMessage': error_message,
                'errorDetails': error_details or {},
                'timestamp': SERVER_TIMESTAMP,
                'service': 'extraction-service'
            }
            
            self.db.collection('extraction_errors').add(error_data)
            logger.info(f"✅ Logged extraction error for document {document_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to log extraction error: {e}")

    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        try:
            # Get recent extractions
            recent_extractions = self.db.collection('extracted_documents')\
                .order_by('createdAt', direction=firestore.Query.DESCENDING)\
                .limit(100)\
                .get()
            
            total_extractions = len(recent_extractions.docs)
            
            # Count by method
            methods = {}
            languages = {}
            
            for doc in recent_extractions:
                data = doc.to_dict()
                method = data.get('method', 'unknown')
                language = data.get('language', 'unknown')
                
                methods[method] = methods.get(method, 0) + 1
                languages[language] = languages.get(language, 0) + 1
            
            return {
                'totalExtractions': total_extractions,
                'methodBreakdown': methods,
                'languageBreakdown': languages
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get extraction stats: {e}")
            return {}