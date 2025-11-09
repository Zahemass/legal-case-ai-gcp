import logging
import time
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import os

logger = logging.getLogger(__name__)

class DraftAgent:
    """AI agent specialized in legal document drafting"""
    
    def __init__(self, firestore_client, document_tool):
        self.firestore_client = firestore_client
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
        
        # Document templates
        self.templates = {
            'legal_letter': self._get_legal_letter_template(),
            'motion': self._get_motion_template(),
            'brief': self._get_brief_template(), 
            'contract_review': self._get_contract_review_template(),
            'memo': self._get_memo_template(),
            'response': self._get_response_template()
        }
        
        logger.info("✅ DraftAgent initialized")

    def test_connection(self):
        """Test agent connection"""
        try:
            if self.model:
                response = self.model.generate_content("Test draft agent")
                return bool(response.text)
            return True
        except Exception as e:
            logger.error(f"Draft agent test failed: {e}")
            raise

    def process_message(self, case_id: str, user_id: str, message: str, conversation_history: List[Dict] = None) -> Optional[str]:
        """Process message for document drafting requests"""
        try:
            logger.info(f"📝 DraftAgent processing message for case {case_id}")
            
            # Analyze the message to determine drafting request type
            request_type = self._analyze_drafting_request(message)
            
            if request_type == 'letter':
                return self._draft_legal_letter(case_id, message)
            elif request_type == 'motion':
                return self._draft_motion(case_id, message)
            elif request_type == 'brief':
                return self._draft_brief(case_id, message)
            elif request_type == 'contract_review':
                return self._draft_contract_review(case_id, message)
            elif request_type == 'memo':
                return self._draft_memo(case_id, message)
            elif request_type == 'response':
                return self._draft_response(case_id, message)
            elif request_type == 'template':
                return self._provide_template(message)
            else:
                return self._general_drafting_assistance(case_id, message, conversation_history)
                
        except Exception as e:
            logger.error(f"❌ DraftAgent error: {e}")
            return "I encountered an error while drafting the document. Please try rephrasing your request or contact support if the issue persists."

    def _analyze_drafting_request(self, message: str) -> str:
        """Analyze message to determine type of drafting request"""
        message_lower = message.lower()
        
        # Letter-related keywords
        if any(word in message_lower for word in ['letter', 'correspondence', 'write to', 'contact', 'notify']):
            return 'letter'
        
        # Motion-related keywords
        if any(word in message_lower for word in ['motion', 'petition', 'application', 'request to court']):
            return 'motion'
        
        # Brief-related keywords
        if any(word in message_lower for word in ['brief', 'memorandum of law', 'legal argument', 'position paper']):
            return 'brief'
        
        # Contract review keywords
        if any(word in message_lower for word in ['contract', 'agreement', 'review', 'terms', 'clause']):
            return 'contract_review'
        
        # Memo keywords
        if any(word in message_lower for word in ['memo', 'memorandum', 'note', 'internal']):
            return 'memo'
        
        # Response keywords
        if any(word in message_lower for word in ['response', 'reply', 'answer', 'respond to']):
            return 'response'
        
        # Template keywords
        if any(word in message_lower for word in ['template', 'format', 'structure', 'example']):
            return 'template'
        
        return 'general_drafting'

    def _draft_legal_letter(self, case_id: str, message: str) -> str:
        """Draft a legal letter"""
        try:
            case_data = self._get_case_data(case_id)
            case_context = self.document_tool.get_case_context(case_id)
            
            prompt = f"""
            Please draft a professional legal letter based on this request:

            User request: "{message}"

            Case context:
            - Case: {case_data.get('title', 'Legal Matter')}
            - Type: {case_data.get('type', 'General')}
            
            Additional context:
            {case_context}

            Please create a formal legal letter that includes:
            1. Proper legal letterhead format (placeholder for firm info)
            2. Date line
            3. Recipient address (placeholder if not specified)
            4. Professional salutation
            5. Clear subject line
            6. Well-structured body with legal reasoning
            7. Professional closing
            8. Signature block

            Use professional legal language and proper formatting.
            Include placeholders where specific information is needed.
            Make the letter comprehensive yet concise.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"📧 **Legal Letter Draft**\n\n```\n{response.text}\n```\n\n💡 **Note:** Please review and customize the letter with specific details, firm letterhead, and recipient information before sending."
            
            return self._create_basic_letter_template(message, case_data)
            
        except Exception as e:
            logger.error(f"Legal letter drafting error: {e}")
            return "I encountered an error while drafting the legal letter. Please provide more specific details about the letter you need."

    def _draft_motion(self, case_id: str, message: str) -> str:
        """Draft a legal motion"""
        try:
            case_data = self._get_case_data(case_id)
            case_context = self.document_tool.get_case_context(case_id)
            
            prompt = f"""
            Please draft a legal motion based on this request:

            User request: "{message}"

            Case information:
            - Case: {case_data.get('title', 'Legal Matter')}
            - Type: {case_data.get('type', 'General')}

            Case context:
            {case_context}

            Please create a formal motion that includes:
            1. Caption with court and case information (placeholder format)
            2. Title of the motion
            3. Introduction stating the motion
            4. Statement of facts
            5. Legal argument with citations (placeholder citations)
            6. Conclusion and prayer for relief
            7. Signature block and certificate of service

            Use proper legal motion format and professional language.
            Include legal reasoning and supporting arguments.
            Add placeholder citations where legal authority would be cited.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"⚖️ **Legal Motion Draft**\n\n```\n{response.text}\n```\n\n💡 **Note:** Please review the motion, add proper case caption, legal citations, and ensure compliance with local court rules before filing."
            
            return self._create_basic_motion_template(message, case_data)
            
        except Exception as e:
            logger.error(f"Motion drafting error: {e}")
            return "I encountered an error while drafting the motion. Please provide more specific details about the type of motion needed."

    def _draft_brief(self, case_id: str, message: str) -> str:
        """Draft a legal brief"""
        try:
            case_data = self._get_case_data(case_id)
            case_context = self.document_tool.get_case_context(case_id)
            
            prompt = f"""
            Please draft a legal brief based on this request:

            User request: "{message}"

            Case information:
            - Case: {case_data.get('title', 'Legal Matter')}
            - Type: {case_data.get('type', 'General')}

            Case context:
            {case_context}

            Please create a legal brief that includes:
            1. Table of contents
            2. Table of authorities
            3. Statement of the case
            4. Statement of facts
            5. Summary of argument
            6. Detailed argument with legal analysis
            7. Conclusion
            8. Certificate of compliance (if applicable)

            Structure the argument logically with:
            - Clear headings and subheadings
            - Legal reasoning and analysis
            - Fact-to-law application
            - Policy considerations where relevant
            - Strong conclusion

            Use professional legal writing style with proper citations (placeholders).
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"📜 **Legal Brief Draft**\n\n```\n{response.text}\n```\n\n💡 **Note:** Please review the brief, add proper legal citations, verify all facts, and ensure compliance with court formatting requirements."
            
            return self._create_basic_brief_template(message, case_data)
            
        except Exception as e:
            logger.error(f"Brief drafting error: {e}")
            return "I encountered an error while drafting the brief. Please provide more specific details about the legal arguments and issues."

    def _draft_contract_review(self, case_id: str, message: str) -> str:
        """Draft contract review comments"""
        try:
            case_data = self._get_case_data(case_id)
            documents = self.document_tool.get_contract_documents(case_id)
            
            prompt = f"""
            Please draft contract review comments based on this request:

            User request: "{message}"

            Case: {case_data.get('title', 'Contract Review')}

            Available contract documents:
            {documents}

            Please provide a contract review that includes:
            1. Executive summary of key issues
            2. Detailed clause-by-clause analysis
            3. Risk assessment for each major provision
            4. Recommended changes and modifications
            5. Negotiation points and priorities
            6. Compliance and regulatory considerations
            7. Action items and next steps

            Focus on:
            - Legal risks and exposures
            - Business implications
            - Enforceability issues
            - Missing or unclear provisions
            - Standard vs. non-standard terms
            """
            
            if self.model and documents:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"📋 **Contract Review**\n\n{response.text}\n\n💡 **Note:** This review is based on available information. Please ensure all contract documents are reviewed by qualified legal counsel."
            
            return self._create_basic_contract_review_template(message)
            
        except Exception as e:
            logger.error(f"Contract review drafting error: {e}")
            return "I encountered an error while drafting the contract review. Please ensure contract documents are uploaded and try again."

    def _draft_memo(self, case_id: str, message: str) -> str:
        """Draft a legal memorandum"""
        try:
            case_data = self._get_case_data(case_id)
            case_context = self.document_tool.get_case_context(case_id)
            
            prompt = f"""
            Please draft a legal memorandum based on this request:

            User request: "{message}"

            Case: {case_data.get('title', 'Legal Matter')}
            Type: {case_data.get('type', 'General')}

            Context:
            {case_context}

            Please create a legal memo that includes:
            1. Header with TO/FROM/DATE/RE information
            2. Executive summary
            3. Question presented
            4. Brief answer
            5. Statement of facts
            6. Discussion/Analysis
            7. Conclusion and recommendations

            Structure the analysis with:
            - Clear legal framework
            - Application of law to facts
            - Risk assessment
            - Practical recommendations
            - Action items

            Use objective legal analysis and professional memo format.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"📄 **Legal Memorandum Draft**\n\n```\n{response.text}\n```\n\n💡 **Note:** Please review the memorandum for accuracy and completeness before distribution."
            
            return self._create_basic_memo_template(message, case_data)
            
        except Exception as e:
            logger.error(f"Memo drafting error: {e}")
            return "I encountered an error while drafting the memorandum. Please provide more specific details about the legal issue to analyze."

    def _draft_response(self, case_id: str, message: str) -> str:
        """Draft a response document"""
        try:
            case_data = self._get_case_data(case_id)
            case_context = self.document_tool.get_case_context(case_id)
            
            prompt = f"""
            Please draft a legal response based on this request:

            User request: "{message}"

            Case: {case_data.get('title', 'Legal Matter')}

            Context:
            {case_context}

            Please create a response that includes:
            1. Proper document heading
            2. Introduction acknowledging what is being responded to
            3. Point-by-point response to issues raised
            4. Supporting legal and factual arguments
            5. Counter-arguments where appropriate
            6. Conclusion with requested relief or position
            7. Professional closing

            Structure the response to:
            - Address each point systematically
            - Provide clear legal reasoning
            - Support positions with facts
            - Maintain professional tone
            - Be persuasive but objective
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"↩️ **Response Document Draft**\n\n```\n{response.text}\n```\n\n💡 **Note:** Please review the response for completeness and ensure all relevant points are addressed."
            
            return self._create_basic_response_template(message, case_data)
            
        except Exception as e:
            logger.error(f"Response drafting error: {e}")
            return "I encountered an error while drafting the response. Please provide more details about what document or issue you're responding to."

    def _provide_template(self, message: str) -> str:
        """Provide document templates"""
        try:
            message_lower = message.lower()
            
            if 'letter' in message_lower:
                return self.templates['legal_letter']
            elif 'motion' in message_lower:
                return self.templates['motion']
            elif 'brief' in message_lower:
                return self.templates['brief']
            elif 'contract' in message_lower:
                return self.templates['contract_review']
            elif 'memo' in message_lower:
                return self.templates['memo']
            elif 'response' in message_lower:
                return self.templates['response']
            else:
                return self._list_available_templates()
                
        except Exception as e:
            logger.error(f"Template provision error: {e}")
            return "I encountered an error while providing the template. Please specify which type of document template you need."

    def _general_drafting_assistance(self, case_id: str, message: str, conversation_history: List[Dict] = None) -> str:
        """Provide general drafting assistance"""
        try:
            case_context = self.document_tool.get_case_context(case_id)
            
            prompt = f"""
            As a legal document drafting specialist, please help with this request:

            User request: "{message}"

            Case context:
            {case_context}

            Please provide guidance on:
            - Document drafting best practices
            - Appropriate document types for the situation
            - Key elements to include
            - Legal writing techniques
            - Formatting and structure suggestions
            - Common pitfalls to avoid

            Keep advice practical and actionable for legal professionals.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return response.text
            
            return self._fallback_drafting_guidance(message)
            
        except Exception as e:
            logger.error(f"General drafting assistance error: {e}")
            return "I'm here to help with legal document drafting. Could you please be more specific about what type of document you need help with?"

    # Helper methods and templates
    def _get_case_data(self, case_id: str) -> Dict[str, Any]:
        """Get case data from Firestore"""
        try:
            case_ref = self.firestore_client.collection('cases').document(case_id)
            case_doc = case_ref.get()
            return case_doc.to_dict() if case_doc.exists else {}
        except Exception as e:
            logger.error(f"Error getting case data: {e}")
            return {}

    def _get_legal_letter_template(self) -> str:
        return "📧 **Legal Letter Template**"
