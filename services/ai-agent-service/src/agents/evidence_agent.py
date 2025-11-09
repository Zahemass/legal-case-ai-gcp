import logging
import time
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import os

logger = logging.getLogger(__name__)

class EvidenceAgent:
    """AI agent specialized in evidence analysis and document search"""
    
    def __init__(self, firestore_client, search_tool, document_tool):
        self.firestore_client = firestore_client
        self.search_tool = search_tool
        self.document_tool = document_tool
        
        # Initialize Gemini
        try:
            api_key = os.environ.get('GOOGLE_AI_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            else:
                self.model = None
                logger.warning("⚠️ Gemini API key not found, using fallback responses")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            self.model = None
        
        logger.info("✅ EvidenceAgent initialized")

    def test_connection(self):
        """Test agent connection"""
        try:
            if self.model:
                response = self.model.generate_content("Test evidence agent")
                return bool(response.text)
            return True
        except Exception as e:
            logger.error(f"Evidence agent test failed: {e}")
            raise

    def process_message(self, case_id: str, user_id: str, message: str, conversation_history: List[Dict] = None) -> Optional[str]:
        """Process message for evidence-related queries"""
        try:
            logger.info(f"🔍 EvidenceAgent processing message for case {case_id}")
            
            # Analyze the message to determine the type of evidence request
            request_type = self._analyze_request_type(message)
            
            if request_type == 'search_documents':
                return self._search_documents(case_id, message)
            elif request_type == 'analyze_evidence':
                return self._analyze_evidence(case_id, message)
            elif request_type == 'build_timeline':
                return self._build_timeline(case_id, message)
            elif request_type == 'find_contradictions':
                return self._find_contradictions(case_id, message)
            elif request_type == 'extract_facts':
                return self._extract_facts(case_id, message)
            else:
                return self._general_evidence_assistance(case_id, message, conversation_history)
                
        except Exception as e:
            logger.error(f"❌ EvidenceAgent error: {e}")
            return "I encountered an error while analyzing the evidence. Please try rephrasing your question or contact support if the issue persists."

    def _analyze_request_type(self, message: str) -> str:
        """Analyze the message to determine the type of evidence request"""
        message_lower = message.lower()
        
        # Search-related keywords
        if any(word in message_lower for word in ['search', 'find', 'locate', 'look for', 'show me']):
            return 'search_documents'
        
        # Timeline-related keywords
        if any(word in message_lower for word in ['timeline', 'chronology', 'sequence', 'when', 'order']):
            return 'build_timeline'
        
        # Contradiction-related keywords
        if any(word in message_lower for word in ['contradiction', 'inconsistent', 'conflict', 'discrepancy']):
            return 'find_contradictions'
        
        # Fact extraction keywords
        if any(word in message_lower for word in ['facts', 'extract', 'key points', 'important details']):
            return 'extract_facts'
        
        # Analysis keywords
        if any(word in message_lower for word in ['analyze', 'analysis', 'examine', 'review', 'evaluate']):
            return 'analyze_evidence'
        
        return 'general_evidence'

    def _search_documents(self, case_id: str, message: str) -> str:
        """Search through case documents"""
        try:
            # Extract search terms from the message
            search_terms = self._extract_search_terms(message)
            
            # Search documents using the search tool
            search_results = self.search_tool.search_case_documents(case_id, search_terms)
            
            if not search_results:
                return f"I couldn't find any documents matching '{' '.join(search_terms)}' in this case. You might want to try different search terms or check if the documents have been uploaded and processed."
            
            # Format results
            response = f"I found {len(search_results)} document(s) related to your search:\n\n"
            
            for i, result in enumerate(search_results[:5], 1):  # Limit to top 5
                response += f"**{i}. {result['filename']}**\n"
                response += f"   📄 Relevance: {result['relevance']:.0%}\n"
                if result.get('excerpt'):
                    response += f"   📝 Excerpt: {result['excerpt'][:200]}...\n"
                response += f"   📅 Uploaded: {result.get('uploaded_date', 'Unknown')}\n\n"
            
            if len(search_results) > 5:
                response += f"... and {len(search_results) - 5} more documents. Would you like me to show more results or refine the search?"
            
            return response
            
        except Exception as e:
            logger.error(f"Document search error: {e}")
            return "I encountered an error while searching through the documents. Please try again with different search terms."

    def _analyze_evidence(self, case_id: str, message: str) -> str:
        """Analyze evidence in the case"""
        try:
            # Get case documents and analysis
            documents = self.document_tool.get_case_documents_summary(case_id)
            
            if not documents:
                return "I don't see any documents in this case to analyze. Please upload some documents first, and I'll be happy to help analyze the evidence."
            
            # Create analysis prompt
            prompt = f"""
            As a legal evidence analyst, please analyze the evidence in this case based on the user's request: "{message}"

            Available documents and evidence:
            {documents}

            Please provide:
            1. Key evidence identified
            2. Strength of evidence
            3. Potential gaps or weaknesses
            4. Recommendations for additional evidence

            Focus on factual analysis and legal relevance.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                return response.text if response.text else self._fallback_evidence_analysis(documents)
            else:
                return self._fallback_evidence_analysis(documents)
                
        except Exception as e:
            logger.error(f"Evidence analysis error: {e}")
            return "I encountered an error while analyzing the evidence. Please try again or contact support."

    def _build_timeline(self, case_id: str, message: str) -> str:
        """Build a timeline of events from case documents"""
        try:
            # Get extracted texts from case documents
            timeline_data = self.document_tool.extract_timeline_data(case_id)
            
            if not timeline_data:
                return "I couldn't find enough chronological information in the case documents to build a timeline. Please ensure that documents containing dates and events have been uploaded and processed."
            
            # Use AI to build comprehensive timeline
            prompt = f"""
            Based on the following information from legal documents, please create a chronological timeline of events:

            Document data:
            {timeline_data}

            User request: "{message}"

            Please create a clear timeline showing:
            1. Date (if available)
            2. Event description
            3. Source document
            4. Significance to the case

            Format as a chronological list with dates in ascending order.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"📅 **Case Timeline**\n\n{response.text}"
            
            # Fallback timeline
            return self._create_basic_timeline(timeline_data)
            
        except Exception as e:
            logger.error(f"Timeline building error: {e}")
            return "I encountered an error while building the timeline. Please ensure your documents contain date information and try again."

    def _find_contradictions(self, case_id: str, message: str) -> str:
        """Find contradictions or inconsistencies in case documents"""
        try:
            # Get document contents for analysis
            document_contents = self.document_tool.get_documents_for_analysis(case_id)
            
            if not document_contents:
                return "I need case documents to analyze for contradictions. Please upload documents first."
            
            prompt = f"""
            As a legal analyst, please review these case documents for contradictions, inconsistencies, or conflicting statements:

            Documents:
            {document_contents}

            User query: "{message}"

            Please identify:
            1. Any contradictory statements or facts
            2. Inconsistent dates or timelines
            3. Conflicting witness accounts
            4. Discrepancies in financial figures
            5. Inconsistent legal positions

            For each contradiction found, specify:
            - What is contradictory
            - Which documents contain the conflicting information
            - Potential impact on the case
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"🔍 **Contradiction Analysis**\n\n{response.text}"
            
            return "I've reviewed the documents but couldn't identify any obvious contradictions. This could mean the documents are consistent, or the analysis requires more detailed review by a legal professional."
            
        except Exception as e:
            logger.error(f"Contradiction analysis error: {e}")
            return "I encountered an error while analyzing for contradictions. Please try again."

    def _extract_facts(self, case_id: str, message: str) -> str:
        """Extract key facts from case documents"""
        try:
            # Get case documents
            documents_data = self.document_tool.get_case_documents_summary(case_id)
            
            if not documents_data:
                return "I don't see any documents in this case. Please upload documents so I can extract the key facts for you."
            
            prompt = f"""
            Please extract the key facts from this legal case based on the user's request: "{message}"

            Case documents:
            {documents_data}

            Please provide:
            1. **Established Facts**: Facts that are clearly documented
            2. **Disputed Facts**: Facts that may be in question
            3. **Key Dates**: Important dates and deadlines
            4. **Parties Involved**: Key individuals and entities
            5. **Financial Information**: Amounts, damages, costs mentioned
            6. **Legal Issues**: Laws, regulations, or legal principles involved

            Present facts clearly and cite source documents where possible.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"📋 **Key Facts Summary**\n\n{response.text}"
            
            return self._create_basic_facts_summary(documents_data)
            
        except Exception as e:
            logger.error(f"Fact extraction error: {e}")
            return "I encountered an error while extracting facts. Please try again."

    def _general_evidence_assistance(self, case_id: str, message: str, conversation_history: List[Dict] = None) -> str:
        """Provide general evidence assistance"""
        try:
            # Get case context
            case_context = self.document_tool.get_case_context(case_id)
            
            # Build conversation context
            context = "Previous conversation:\n"
            if conversation_history:
                for msg in conversation_history[-3:]:  # Last 3 messages
                    role = "User" if msg.get('type') == 'user' else "Assistant"
                    context += f"{role}: {msg.get('message', '')}\n"
            
            prompt = f"""
            As a legal evidence analyst, please help the user with their question about case evidence.

            Case context:
            {case_context}

            {context}

            User question: "{message}"

            Please provide helpful guidance about:
            - Evidence analysis techniques
            - Document organization strategies
            - Fact-finding approaches
            - Evidence evaluation methods
            - Legal research suggestions

            Keep your response practical and actionable for legal professionals.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return response.text
            
            return self._fallback_evidence_guidance(message)
            
        except Exception as e:
            logger.error(f"General evidence assistance error: {e}")
            return "I'm here to help with evidence analysis. Could you please rephrase your question or be more specific about what type of evidence assistance you need?"

    def _extract_search_terms(self, message: str) -> List[str]:
        """Extract search terms from user message"""
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'find', 'search', 'look', 'show', 'me'}
        
        words = message.lower().split()
        search_terms = [word.strip('.,!?";') for word in words if word not in stop_words and len(word) > 2]
        
        return search_terms[:5]  # Limit to 5 terms

    def _fallback_evidence_analysis(self, documents: str) -> str:
        """Fallback evidence analysis when AI is unavailable"""
        return f"""Based on the available documents in this case, here's a basic evidence analysis:

📄 **Document Summary**: I found {documents.count('Document')} documents in this case.

🔍 **Analysis Approach**:
1. Review each document for factual content
2. Identify key evidence and supporting materials
3. Look for corroborating evidence across documents
4. Note any potential gaps in evidence

💡 **Recommendations**:
- Organize evidence by relevance to key legal issues
- Create a document index for easy reference
- Consider additional evidence that may strengthen the case
- Review documents for completeness and authenticity

For a more detailed analysis, please specify what particular aspect of the evidence you'd like me to focus on."""

    def _create_basic_timeline(self, timeline_data: str) -> str:
        """Create a basic timeline from available data"""
        return f"""📅 **Basic Timeline Analysis**

Based on the documents I reviewed, here's what I found:

{timeline_data}

**Note**: This is a preliminary timeline based on available information. For a more comprehensive timeline, please ensure all relevant documents with date information have been uploaded and processed.

**Recommendations**:
- Review documents for additional date references
- Verify dates for accuracy
- Consider adding witness statements or depositions for timeline clarity"""

    def _create_basic_facts_summary(self, documents_data: str) -> str:
        """Create basic facts summary when AI is unavailable"""
        return f"""📋 **Key Facts Summary**

Based on the case documents, here are the key areas to review:

**Document Analysis**:
{documents_data}

**Fact Categories to Review**:
1. **Parties**: Identify all individuals and entities involved
2. **Dates**: Key dates, deadlines, and chronological events  
3. **Locations**: Relevant locations and jurisdictions
4. **Financial**: Amounts, damages, costs, and financial terms
5. **Legal Issues**: Laws, regulations, and legal principles applicable

**Next Steps**:
- Review each document systematically
- Create a fact matrix organizing information by category
- Cross-reference facts across multiple documents
- Identify areas needing additional documentation"""

    def _fallback_evidence_guidance(self, message: str) -> str:
        """Provide fallback guidance when AI is unavailable"""
        return f"""🔍 **Evidence Analysis Guidance**

I understand you're asking about: "{message}"

Here are some general evidence analysis approaches that might help:

**📋 Document Review Process**:
1. Catalog all documents by type and date
2. Create a summary of each document's key points
3. Identify relevance to case issues
4. Note potential evidence gaps

**🔎 Search Strategies**:
- Use keyword searches across all documents
- Look for patterns and connections between documents
- Identify corroborating evidence
- Flag inconsistencies for further review

**⚖️ Evidence Evaluation**:
- Assess credibility and reliability of sources
- Consider authentication requirements
- Evaluate relevance to legal theories
- Determine admissibility issues

**💡 Best Practices**:
- Maintain detailed evidence logs
- Use consistent naming conventions
- Create cross-reference indices
- Regular backup and version control

Would you like me to help you with a more specific aspect of evidence analysis?"""