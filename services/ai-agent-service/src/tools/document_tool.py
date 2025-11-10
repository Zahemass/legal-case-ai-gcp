#services/ai-agent-service/src/tools/document_tool.py
import logging
import time
from typing import Dict, Any, List, Optional
from google.cloud import firestore

logger = logging.getLogger(__name__)

class DocumentTool:
    """Tool for accessing and analyzing case documents"""
    
    def __init__(self, firestore_client, storage_client):
        self.firestore_client = firestore_client
        self.storage_client = storage_client
        logger.info("✅ DocumentTool initialized")

    def get_case_context(self, case_id: str) -> str:
        """Get comprehensive case context for AI agents"""
        try:
            # Get case basic info
            case_data = self._get_case_data(case_id)
            if not case_data:
                return "Case information not available."
            
            # Get document summary
            doc_summary = self.get_case_documents_summary(case_id)
            
            # Get recent analysis if available
            recent_analysis = self._get_recent_analysis_summary(case_id)
            
            context = f"""
Case: {case_data.get('title', 'Unknown')}
Type: {case_data.get('type', 'General')}
Status: {case_data.get('status', 'Active')}
Priority: {case_data.get('priority', 'Medium')}
Created: {case_data.get('createdAt', 'Unknown')}
Description: {case_data.get('description', 'No description available')}

Documents: {doc_summary}

{f"Recent Analysis: {recent_analysis}" if recent_analysis else "No recent analysis available."}
"""
            return context.strip()
            
        except Exception as e:
            logger.error(f"❌ Error getting case context: {e}")
            return "Case context unavailable due to error."

    def get_case_documents_summary(self, case_id: str) -> str:
        """Get summary of all case documents"""
        try:
            docs_query = self.firestore_client.collection('documents')\
                .where('caseId', '==', case_id)\
                .where('status', '!=', 'deleted')\
                .limit(20)
            
            documents = docs_query.get()
            
            if not documents:
                return "No documents uploaded yet."
            
            summary = f"{len(documents)} documents:\n"
            
            for doc in documents:
                doc_data = doc.to_dict()
                filename = doc_data.get('filename', 'Unknown')
                size = doc_data.get('size', 0)
                upload_date = doc_data.get('uploadedAt', 'Unknown')
                extraction_status = doc_data.get('extractionStatus', 'Unknown')
                
                size_mb = round(size / (1024 * 1024), 2) if size > 0 else 0
                summary += f"- {filename} ({size_mb}MB, {extraction_status}, {upload_date})\n"
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"❌ Error getting documents summary: {e}")
            return "Document summary unavailable."

    def get_case_documents_detailed(self, case_id: str) -> str:
        """Get detailed information about case documents"""
        try:
            docs_query = self.firestore_client.collection('documents')\
                .where('caseId', '==', case_id)\
                .where('status', '!=', 'deleted')
            
            documents = docs_query.get()
            
            if not documents:
                return "No documents available for analysis."
            
            detailed_info = ""
            
            for doc in documents:
                doc_data = doc.to_dict()
                doc_id = doc.id
                
                # Get extracted text if available
                extracted_text = self._get_extracted_text_preview(doc_id)
                
                detailed_info += f"""
Document: {doc_data.get('filename', 'Unknown')}
Size: {round(doc_data.get('size', 0) / (1024*1024), 2)}MB
Type: {doc_data.get('contentType', 'Unknown')}
Uploaded: {doc_data.get('uploadedAt', 'Unknown')}
Extraction Status: {doc_data.get('extractionStatus', 'Unknown')}
Text Preview: {extracted_text}

"""
            
            return detailed_info.strip()
            
        except Exception as e:
            logger.error(f"❌ Error getting detailed documents: {e}")
            return "Detailed document information unavailable."

    def get_documents_for_analysis(self, case_id: str, limit: int = 8000) -> str:
        """Get document contents for AI analysis"""
        try:
            # Get extracted documents
            extracted_query = self.firestore_client.collection('extracted_documents')\
                .where('caseId', '==', case_id)\
                .order_by('createdAt', direction=firestore.Query.DESCENDING)\
                .limit(10)
            
            extracted_docs = extracted_query.get()
            
            if not extracted_docs:
                return "No extracted document content available for analysis."
            
            combined_content = ""
            current_length = 0
            
            for doc in extracted_docs:
                doc_data = doc.to_dict()
                filename = doc_data.get('filename', 'Unknown')
                text = doc_data.get('text', '')
                
                # Add document header
                header = f"\n--- Document: {filename} ---\n"
                
                if current_length + len(header) + len(text) <= limit:
                    combined_content += header + text
                    current_length += len(header) + len(text)
                else:
                    # Add partial content to reach limit
                    remaining = limit - current_length - len(header)
                    if remaining > 100:
                        combined_content += header + text[:remaining] + "... [truncated]"
                    break
            
            return combined_content if combined_content else "No document content available."
            
        except Exception as e:
            logger.error(f"❌ Error getting documents for analysis: {e}")
            return "Document content unavailable for analysis."

    def get_contract_documents(self, case_id: str) -> str:
        """Get contract-related documents"""
        try:
            # Look for documents with contract-related names or types
            docs_query = self.firestore_client.collection('documents')\
                .where('caseId', '==', case_id)\
                .where('status', '!=', 'deleted')
            
            documents = docs_query.get()
            contract_docs = []
            
            for doc in documents:
                doc_data = doc.to_dict()
                filename = doc_data.get('filename', '').lower()
                
                # Check if filename suggests it's a contract
                contract_keywords = ['contract', 'agreement', 'terms', 'conditions', 'deal', 'mou', 'nda']
                if any(keyword in filename for keyword in contract_keywords):
                    contract_docs.append(doc)
            
            if not contract_docs:
                return "No contract documents identified in the case."
            
            # Get extracted text for contract documents
            contract_content = ""
            for doc in contract_docs:
                doc_data = doc.to_dict()
                extracted_text = self._get_extracted_text_preview(doc.id, preview_length=1000)
                
                contract_content += f"""
Contract Document: {doc_data.get('filename', 'Unknown')}
Content Preview: {extracted_text}

"""
            
            return contract_content.strip()
            
        except Exception as e:
            logger.error(f"❌ Error getting contract documents: {e}")
            return "Contract document information unavailable."

    def extract_timeline_data(self, case_id: str) -> str:
        """Extract timeline and date information from documents"""
        try:
            # Get extracted documents
            extracted_query = self.firestore_client.collection('extracted_documents')\
                .where('caseId', '==', case_id)\
                .limit(10)
            
            extracted_docs = extracted_query.get()
            
            if not extracted_docs:
                return "No documents available for timeline extraction."
            
            timeline_data = ""
            
            for doc in extracted_docs:
                doc_data = doc.to_dict()
                filename = doc_data.get('filename', 'Unknown')
                text = doc_data.get('text', '')
                
                # Extract date-related information (simple regex patterns)
                import re
                
                # Common date patterns
                date_patterns = [
                    r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or MM-DD-YYYY
                    r'\b[A-Za-z]+ \d{1,2}, \d{4}\b',        # Month DD, YYYY
                    r'\b\d{1,2} [A-Za-z]+ \d{4}\b',         # DD Month YYYY
                ]
                
                dates_found = []
                for pattern in date_patterns:
                    matches = re.findall(pattern, text)
                    dates_found.extend(matches)
                
                if dates_found:
                    timeline_data += f"Document: {filename}\n"
                    timeline_data += f"Dates found: {', '.join(set(dates_found[:10]))}\n\n"
            
            return timeline_data if timeline_data else "No date information found in documents."
            
        except Exception as e:
            logger.error(f"❌ Error extracting timeline data: {e}")
            return "Timeline data extraction failed."

    def get_document_statistics(self, case_id: str) -> str:
        """Get statistical information about case documents"""
        try:
            docs_query = self.firestore_client.collection('documents')\
                .where('caseId', '==', case_id)\
                .where('status', '!=', 'deleted')
            
            documents = docs_query.get()
            
            if not documents:
                return "No documents to analyze."
            
            total_docs = len(documents)
            total_size = 0
            doc_types = {}
            extraction_status = {'completed': 0, 'pending': 0, 'error': 0}
            
            for doc in documents:
                doc_data = doc.to_dict()
                
                # Size calculation
                size = doc_data.get('size', 0)
                total_size += size
                
                # Document type analysis
                content_type = doc_data.get('contentType', 'unknown')
                doc_type = content_type.split('/')[0] if '/' in content_type else content_type
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                
                # Extraction status
                status = doc_data.get('extractionStatus', 'pending')
                if status in extraction_status:
                    extraction_status[status] += 1
                else:
                    extraction_status['pending'] += 1
            
            # Format statistics
            size_mb = round(total_size / (1024 * 1024), 2)
            avg_size_mb = round(size_mb / total_docs, 2) if total_docs > 0 else 0
            
            stats = f"""Total Documents: {total_docs}
Total Size: {size_mb} MB
Average Size: {avg_size_mb} MB per document

Document Types:
{chr(10).join([f"- {doc_type}: {count}" for doc_type, count in doc_types.items()])}

Extraction Status:
- Completed: {extraction_status['completed']}
- Pending: {extraction_status['pending']}
- Error: {extraction_status['error']}"""
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting document statistics: {e}")
            return "Document statistics unavailable."

    def _get_case_data(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get case data from Firestore"""
        try:
            case_ref = self.firestore_client.collection('cases').document(case_id)
            case_doc = case_ref.get()
            return case_doc.to_dict() if case_doc.exists else None
        except Exception as e:
            logger.error(f"Error getting case data: {e}")
            return None

    def _get_extracted_text_preview(self, document_id: str, preview_length: int = 300) -> str:
        """Get preview of extracted text for a document"""
        try:
            extracted_query = self.firestore_client.collection('extracted_documents')\
                .where('documentId', '==', document_id)\
                .limit(1)
            
            docs = extracted_query.get()
            
            if not docs:
                return "Text not yet extracted."
            
            doc_data = docs[0].to_dict()
            text = doc_data.get('text', '')
            
            if len(text) <= preview_length:
                return text
            else:
                return text[:preview_length] + "..."
            
        except Exception as e:
            logger.error(f"Error getting extracted text preview: {e}")
            return "Text preview unavailable."

    def _get_recent_analysis_summary(self, case_id: str) -> str:
        """Get summary of recent case analysis"""
        try:
            analysis_query = self.firestore_client.collection('case_analysis')\
                .where('caseId', '==', case_id)\
                .order_by('analyzedAt', direction=firestore.Query.DESCENDING)\
                .limit(1)
            
            docs = analysis_query.get()
            
            if not docs:
                return ""
            
            analysis_data = docs[0].to_dict()
            summary = analysis_data.get('executiveSummary', '')
            
            # Truncate if too long
            if len(summary) > 500:
                summary = summary[:500] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting recent analysis: {e}")
            return ""