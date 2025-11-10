#services/ai-agent-service/src/tools/search_tool.py
import logging
import time
from typing import Dict, Any, List, Optional
from google.cloud import firestore

logger = logging.getLogger(__name__)

class SearchTool:
    """Tool for searching through case documents and data"""
    
    def __init__(self, firestore_client):
        self.firestore_client = firestore_client
        logger.info("✅ SearchTool initialized")

    def search_case_documents(self, case_id: str, search_terms: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Search through case documents for specific terms"""
        try:
            logger.info(f"🔍 Searching case {case_id} for terms: {search_terms}")
            
            # Get extracted documents for the case
            extracted_docs_query = self.firestore_client.collection('extracted_documents')\
                .where('caseId', '==', case_id)\
                .limit(50)  # Reasonable limit for search
            
            extracted_docs = extracted_docs_query.get()
            
            if not extracted_docs:
                return []
            
            results = []
            
            for doc in extracted_docs:
                doc_data = doc.to_dict()
                text = doc_data.get('text', '').lower()
                filename = doc_data.get('filename', 'Unknown')
                document_id = doc_data.get('documentId', doc.id)
                
                # Calculate relevance score
                relevance_score = self._calculate_relevance(text, search_terms)
                
                if relevance_score > 0:
                    # Find excerpt with search terms
                    excerpt = self._extract_excerpt(text, search_terms)
                    
                    results.append({
                        'document_id': document_id,
                        'filename': filename,
                        'relevance': relevance_score,
                        'excerpt': excerpt,
                        'uploaded_date': doc_data.get('createdAt', 'Unknown'),
                        'page_count': doc_data.get('pageCount', 0),
                        'text_length': len(text)
                    })
            
            # Sort by relevance score
            results.sort(key=lambda x: x['relevance'], reverse=True)
            
            logger.info(f"✅ Found {len(results)} relevant documents")
            return results[:limit]
            
        except Exception as e:
            logger.error(f"❌ Document search error: {e}")
            return []

    def search_case_analysis(self, case_id: str, search_terms: List[str]) -> List[Dict[str, Any]]:
        """Search through case analysis results"""
        try:
            # Get case analysis documents
            analysis_query = self.firestore_client.collection('case_analysis')\
                .where('caseId', '==', case_id)\
                .order_by('analyzedAt', direction=firestore.Query.DESCENDING)\
                .limit(5)
            
            analysis_docs = analysis_query.get()
            results = []
            
            for doc in analysis_docs:
                doc_data = doc.to_dict()
                
                # Search in analysis content
                searchable_content = f"{doc_data.get('executiveSummary', '')} {' '.join(doc_data.get('keyFindings', []))} {doc_data.get('legalRelevance', '')}"
                
                relevance = self._calculate_relevance(searchable_content.lower(), search_terms)
                
                if relevance > 0:
                    results.append({
                        'analysis_id': doc.id,
                        'type': 'case_analysis',
                        'relevance': relevance,
                        'analyzed_at': doc_data.get('analyzedAt', 'Unknown'),
                        'excerpt': self._extract_excerpt(searchable_content.lower(), search_terms),
                        'summary': doc_data.get('executiveSummary', '')[:200] + '...'
                    })
            
            return sorted(results, key=lambda x: x['relevance'], reverse=True)
            
        except Exception as e:
            logger.error(f"❌ Analysis search error: {e}")
            return []

    def search_chat_history(self, case_id: str, search_terms: List[str], limit: int = 20) -> List[Dict[str, Any]]:
        """Search through chat history"""
        try:
            # Get chat messages for the case
            messages_query = self.firestore_client.collection('chat_messages')\
                .where('caseId', '==', case_id)\
                .order_by('timestamp', direction=firestore.Query.DESCENDING)\
                .limit(100)  # Search last 100 messages
            
            messages = messages_query.get()
            results = []
            
            for msg in messages:
                msg_data = msg.to_dict()
                message_text = msg_data.get('message', '').lower()
                
                relevance = self._calculate_relevance(message_text, search_terms)
                
                if relevance > 0:
                    results.append({
                        'message_id': msg.id,
                        'type': msg_data.get('type', 'user'),
                        'relevance': relevance,
                        'timestamp': msg_data.get('timestamp', 'Unknown'),
                        'excerpt': self._extract_excerpt(message_text, search_terms),
                        'user_id': msg_data.get('userId', 'Unknown')
                    })
            
            return sorted(results, key=lambda x: x['relevance'], reverse=True)[:limit]
            
        except Exception as e:
            logger.error(f"❌ Chat history search error: {e}")
            return []

    def search_legal_entities(self, case_id: str, entity_type: str = None) -> List[Dict[str, Any]]:
        """Search for legal entities (people, organizations, dates, etc.) in case"""
        try:
            # Get document analysis that might contain entities
            analysis_query = self.firestore_client.collection('document_analysis')\
                .where('caseId', '==', case_id)\
                .limit(10)
            
            analysis_docs = analysis_query.get()
            entities = []
            
            for doc in analysis_docs:
                doc_data = doc.to_dict()
                doc_entities = doc_data.get('entities', {})
                
                if entity_type:
                    # Filter by specific entity type
                    if entity_type in doc_entities:
                        for entity in doc_entities[entity_type]:
                            entities.append({
                                'entity': entity,
                                'type': entity_type,
                                'document_id': doc_data.get('documentId', 'Unknown'),
                                'confidence': doc_data.get('confidence', 0.0)
                            })
                else:
                    # Get all entities
                    for ent_type, ent_list in doc_entities.items():
                        for entity in ent_list:
                            entities.append({
                                'entity': entity,
                                'type': ent_type,
                                'document_id': doc_data.get('documentId', 'Unknown'),
                                'confidence': doc_data.get('confidence', 0.0)
                            })
            
            # Remove duplicates and sort
            unique_entities = {}
            for entity in entities:
                key = f"{entity['entity']}_{entity['type']}"
                if key not in unique_entities or entity['confidence'] > unique_entities[key]['confidence']:
                    unique_entities[key] = entity
            
            return list(unique_entities.values())
            
        except Exception as e:
            logger.error(f"❌ Entity search error: {e}")
            return []

    def _calculate_relevance(self, text: str, search_terms: List[str]) -> float:
        """Calculate relevance score for text based on search terms"""
        if not text or not search_terms:
            return 0.0
        
        total_score = 0.0
        text_words = text.split()
        text_length = len(text_words)
        
        for term in search_terms:
            term_lower = term.lower()
            
            # Exact phrase match (highest score)
            if term_lower in text:
                phrase_count = text.count(term_lower)
                total_score += phrase_count * 3.0
            
            # Individual word matches
            term_words = term_lower.split()
            for word in term_words:
                if len(word) > 2:  # Skip very short words
                    word_count = text.count(word)
                    # Normalize by text length
                    word_score = (word_count / max(text_length, 1)) * 100
                    total_score += word_score
        
        # Normalize final score
        return min(total_score / len(search_terms), 1.0)

    def _extract_excerpt(self, text: str, search_terms: List[str], max_length: int = 200) -> str:
        """Extract relevant excerpt from text containing search terms"""
        if not text or not search_terms:
            return text[:max_length] + '...' if len(text) > max_length else text
        
        # Find the position of the first search term
        first_match_pos = len(text)
        matching_term = ""
        
        for term in search_terms:
            term_lower = term.lower()
            pos = text.find(term_lower)
            if pos != -1 and pos < first_match_pos:
                first_match_pos = pos
                matching_term = term_lower
        
        if first_match_pos == len(text):
            # No matches found, return beginning
            return text[:max_length] + '...' if len(text) > max_length else text
        
        # Extract context around the match
        start = max(0, first_match_pos - max_length // 3)
        end = min(len(text), first_match_pos + len(matching_term) + max_length * 2 // 3)
        
        excerpt = text[start:end]
        
        # Add ellipsis if truncated
        if start > 0:
            excerpt = '...' + excerpt
        if end < len(text):
            excerpt = excerpt + '...'
        
        return excerpt

    def get_search_suggestions(self, case_id: str, partial_term: str) -> List[str]:
        """Get search suggestions based on case content"""
        try:
            if len(partial_term) < 2:
                return []
            
            # Get extracted documents
            extracted_docs_query = self.firestore_client.collection('extracted_documents')\
                .where('caseId', '==', case_id)\
                .limit(10)
            
            extracted_docs = extracted_docs_query.get()
            
            suggestions = set()
            partial_lower = partial_term.lower()
            
            for doc in extracted_docs:
                doc_data = doc.to_dict()
                text = doc_data.get('text', '').lower()
                
                # Extract words that start with the partial term
                words = text.split()
                for word in words:
                    clean_word = word.strip('.,!?";()[]{}')
                    if (clean_word.startswith(partial_lower) and 
                        len(clean_word) > len(partial_term) and 
                        len(clean_word) < 20):  # Reasonable word length
                        suggestions.add(clean_word)
                    
                    if len(suggestions) >= 10:  # Limit suggestions
                        break
            
            return sorted(list(suggestions))[:10]
            
        except Exception as e:
            logger.error(f"❌ Search suggestions error: {e}")
            return []