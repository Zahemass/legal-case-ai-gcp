import logging
import time
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import os

logger = logging.getLogger(__name__)

class SummaryAgent:
    """AI agent specialized in case summarization and overview"""
    
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
        
        logger.info("✅ SummaryAgent initialized")

    def test_connection(self):
        """Test agent connection"""
        try:
            if self.model:
                response = self.model.generate_content("Test summary agent")
                return bool(response.text)
            return True
        except Exception as e:
            logger.error(f"Summary agent test failed: {e}")
            raise

    def process_message(self, case_id: str, user_id: str, message: str, conversation_history: List[Dict] = None) -> Optional[str]:
        """Process message for summary-related queries"""
        try:
            logger.info(f"📋 SummaryAgent processing message for case {case_id}")
            
            # Analyze the message to determine the type of summary request
            request_type = self._analyze_request_type(message)
            
            if request_type == 'case_overview':
                return self._generate_case_overview(case_id)
            elif request_type == 'document_summary':
                return self._generate_document_summary(case_id, message)
            elif request_type == 'status_update':
                return self._generate_status_update(case_id)
            elif request_type == 'key_issues':
                return self._summarize_key_issues(case_id)
            elif request_type == 'progress_summary':
                return self._generate_progress_summary(case_id)
            elif request_type == 'conversation_summary':
                return self._summarize_conversation(conversation_history)
            else:
                return self._general_summary_assistance(case_id, message, conversation_history)
                
        except Exception as e:
            logger.error(f"❌ SummaryAgent error: {e}")
            return "I encountered an error while generating the summary. Please try rephrasing your request or contact support if the issue persists."

    def _analyze_request_type(self, message: str) -> str:
        """Analyze the message to determine the type of summary request"""
        message_lower = message.lower()
        
        # Case overview keywords
        if any(word in message_lower for word in ['overview', 'case summary', 'overall', 'big picture', 'case status']):
            return 'case_overview'
        
        # Document summary keywords  
        if any(word in message_lower for word in ['document summary', 'summarize documents', 'document overview']):
            return 'document_summary'
        
        # Status update keywords
        if any(word in message_lower for word in ['status', 'update', 'current state', 'where are we']):
            return 'status_update'
        
        # Key issues keywords
        if any(word in message_lower for word in ['key issues', 'main issues', 'important points', 'highlights']):
            return 'key_issues'
        
        # Progress keywords
        if any(word in message_lower for word in ['progress', 'advancement', 'milestones', 'achievements']):
            return 'progress_summary'
        
        # Conversation summary keywords
        if any(word in message_lower for word in ['conversation', 'discussion', 'chat summary', 'what we discussed']):
            return 'conversation_summary'
        
        return 'general_summary'

    def _generate_case_overview(self, case_id: str) -> str:
        """Generate comprehensive case overview"""
        try:
            # Get case data
            case_data = self._get_case_data(case_id)
            if not case_data:
                return "I couldn't find this case. Please make sure you're in the correct case chat."
            
            # Get documents summary
            documents_summary = self.document_tool.get_case_documents_summary(case_id)
            
            # Get recent analysis if available
            recent_analysis = self._get_recent_case_analysis(case_id)
            
            prompt = f"""
            Please provide a comprehensive case overview for this legal case:

            Case Information:
            - Title: {case_data.get('title', 'Untitled Case')}
            - Type: {case_data.get('type', 'General')}
            - Status: {case_data.get('status', 'Active')}
            - Created: {case_data.get('createdAt', 'Unknown')}
            - Priority: {case_data.get('priority', 'Medium')}
            - Description: {case_data.get('description', 'No description available')}

            Documents: {len(documents_summary.split('Document:')) - 1 if documents_summary else 0} documents uploaded

            {f"Recent Analysis: {recent_analysis}" if recent_analysis else ""}

            Please provide an overview that includes:
            1. **Case Background**: Brief description and context
            2. **Current Status**: Where the case stands now
            3. **Key Components**: Main elements and documents
            4. **Next Steps**: Recommended actions or areas of focus
            5. **Timeline**: Important dates and milestones

            Keep it concise but comprehensive for legal professionals.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"📋 **Case Overview: {case_data.get('title', 'Untitled Case')}**\n\n{response.text}"
            
            return self._create_basic_case_overview(case_data, documents_summary)
            
        except Exception as e:
            logger.error(f"Case overview generation error: {e}")
            return "I encountered an error while generating the case overview. Please try again."

    def _generate_document_summary(self, case_id: str, message: str) -> str:
        """Generate summary of case documents"""
        try:
            # Get documents data
            documents = self.document_tool.get_case_documents_detailed(case_id)
            
            if not documents:
                return "There are no documents in this case yet. Please upload documents to get a summary."
            
            prompt = f"""
            Please provide a summary of the documents in this legal case:

            User request: "{message}"

            Documents:
            {documents}

            Please provide:
            1. **Document Count**: Total number of documents
            2. **Document Types**: Breakdown by type (contracts, correspondence, etc.)
            3. **Key Documents**: Most important or relevant documents
            4. **Content Overview**: Brief summary of what the documents contain
            5. **Completeness Assessment**: Any apparent gaps or missing documents
            6. **Organization Suggestions**: How to better organize or categorize

            Focus on helping legal professionals understand the document landscape.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"📄 **Document Summary**\n\n{response.text}"
            
            return self._create_basic_document_summary(documents)
            
        except Exception as e:
            logger.error(f"Document summary generation error: {e}")
            return "I encountered an error while summarizing the documents. Please try again."

    def _generate_status_update(self, case_id: str) -> str:
        """Generate current case status update"""
        try:
            case_data = self._get_case_data(case_id)
            if not case_data:
                return "I couldn't access the case information for the status update."
            
            # Get recent activities
            recent_activities = self._get_recent_activities(case_id)
            
            # Get document counts
            doc_counts = self.document_tool.get_document_statistics(case_id)
            
            prompt = f"""
            Please provide a current status update for this legal case:

            Case: {case_data.get('title', 'Untitled Case')}
            Status: {case_data.get('status', 'Active')}
            Last Updated: {case_data.get('updatedAt', 'Unknown')}

            Document Statistics:
            {doc_counts}

            Recent Activities:
            {recent_activities}

            Please provide a status update including:
            1. **Current Phase**: What stage the case is in
            2. **Recent Progress**: What has been accomplished recently  
            3. **Active Items**: What's currently being worked on
            4. **Pending Actions**: What needs to be done next
            5. **Timeline**: Key upcoming dates or deadlines
            6. **Concerns**: Any issues or blockers to address

            Keep it professional and actionable.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"📊 **Status Update - {case_data.get('title', 'Case')}**\n\n{response.text}"
            
            return self._create_basic_status_update(case_data, doc_counts)
            
        except Exception as e:
            logger.error(f"Status update generation error: {e}")
            return "I encountered an error while generating the status update. Please try again."

    def _summarize_key_issues(self, case_id: str) -> str:
        """Summarize key issues in the case"""
        try:
            case_data = self._get_case_data(case_id)
            documents_content = self.document_tool.get_documents_for_analysis(case_id, limit=5000)
            
            if not documents_content:
                return "I need case documents to identify key issues. Please upload relevant documents first."
            
            prompt = f"""
            Based on this legal case, please identify and summarize the key issues:

            Case: {case_data.get('title', 'Untitled Case')}
            Type: {case_data.get('type', 'General')}

            Document Content:
            {documents_content}

            Please identify:
            1. **Primary Legal Issues**: Main legal questions or disputes
            2. **Factual Issues**: Key factual disputes or uncertainties  
            3. **Procedural Issues**: Process or procedural concerns
            4. **Strategic Issues**: Strategic considerations for case management
            5. **Risk Factors**: Potential risks or challenges
            6. **Opportunities**: Potential advantages or opportunities

            For each issue, provide a brief explanation and its significance to the case.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"🎯 **Key Issues Analysis**\n\n{response.text}"
            
            return "I've reviewed the available information. To provide a detailed key issues summary, I recommend having more specific case documents available for analysis."
            
        except Exception as e:
            logger.error(f"Key issues summarization error: {e}")
            return "I encountered an error while analyzing key issues. Please try again."

    def _generate_progress_summary(self, case_id: str) -> str:
        """Generate case progress summary"""
        try:
            case_data = self._get_case_data(case_id)
            activities = self._get_case_activities(case_id)
            
            created_date = case_data.get('createdAt', 'Unknown')
            current_status = case_data.get('status', 'Active')
            
            prompt = f"""
            Please provide a progress summary for this legal case:

            Case: {case_data.get('title', 'Untitled Case')}  
            Created: {created_date}
            Current Status: {current_status}
            
            Activities and Progress:
            {activities}

            Please summarize:
            1. **Case Milestones**: Major milestones achieved
            2. **Timeline Progress**: How the case has progressed over time
            3. **Document Progress**: Document collection and processing status
            4. **Analysis Progress**: Any analysis or review work completed
            5. **Outstanding Items**: What still needs to be completed
            6. **Next Milestones**: Upcoming goals or milestones

            Focus on measurable progress and concrete achievements.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"📈 **Progress Summary**\n\n{response.text}"
            
            return self._create_basic_progress_summary(case_data, activities)
            
        except Exception as e:
            logger.error(f"Progress summary generation error: {e}")
            return "I encountered an error while generating the progress summary. Please try again."

    def summarize_conversation(self, messages: List[Dict]) -> str:
        """Summarize conversation history"""
        try:
            if not messages:
                return "No conversation to summarize yet. Start by asking me questions about your case!"
            
            # Format messages for analysis
            conversation_text = ""
            for msg in messages[-10:]:  # Last 10 messages
                role = "User" if msg.get('type') == 'user' else "Assistant"
                timestamp = msg.get('timestamp', time.time())
                content = msg.get('message', '')
                conversation_text += f"{role}: {content}\n"
            
            prompt = f"""
            Please provide a summary of this conversation between a user and legal AI assistants:

            Conversation:
            {conversation_text}

            Please summarize:
            1. **Main Topics**: Key topics discussed
            2. **Questions Asked**: Primary questions the user had
            3. **Information Provided**: Key information or guidance given
            4. **Action Items**: Any suggested actions or next steps
            5. **Unresolved Items**: Questions that may need follow-up

            Keep the summary concise and focused on the legal aspects.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"💬 **Conversation Summary**\n\n{response.text}"
            
            return self._create_basic_conversation_summary(messages)
            
        except Exception as e:
            logger.error(f"Conversation summary error: {e}")
            return "I encountered an error while summarizing the conversation. Please try again."

    def _general_summary_assistance(self, case_id: str, message: str, conversation_history: List[Dict] = None) -> str:
        """Provide general summary assistance"""
        try:
            case_context = self.document_tool.get_case_context(case_id)
            
            prompt = f"""
            As a legal case summarization specialist, please help with this request:

            User request: "{message}"

            Case context:
            {case_context}

            Please provide helpful guidance about:
            - Case summarization techniques
            - Key information organization  
            - Status reporting best practices
            - Progress tracking methods
            - Summary presentation formats

            Keep your response practical and actionable for legal professionals.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return response.text
            
            return self._fallback_summary_guidance(message)
            
        except Exception as e:
            logger.error(f"General summary assistance error: {e}")
            return "I'm here to help with case summaries and overviews. Could you please be more specific about what type of summary you need?"

    # Helper methods
    def _get_case_data(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get case data from Firestore"""
        try:
            case_ref = self.firestore_client.collection('cases').document(case_id)
            case_doc = case_ref.get()
            return case_doc.to_dict() if case_doc.exists else None
        except Exception as e:
            logger.error(f"Error getting case data: {e}")
            return None

    def _get_recent_case_analysis(self, case_id: str) -> str:
        """Get recent case analysis if available"""
        try:
            analysis_query = self.firestore_client.collection('case_analysis')\
                .where('caseId', '==', case_id)\
                .order_by('analyzedAt', direction='DESCENDING')\
                .limit(1)
            
            docs = analysis_query.get()
            if docs:
                analysis_data = docs[0].to_dict()
                return f"Executive Summary: {analysis_data.get('executiveSummary', 'No summary available')}"
            
            return ""
        except Exception as e:
            logger.error(f"Error getting recent analysis: {e}")
            return ""

    def _get_recent_activities(self, case_id: str) -> str:
        """Get recent case activities"""
        try:
            activities_query = self.firestore_client.collection('case_activities')\
                .where('caseId', '==', case_id)\
                .order_by('timestamp', direction='DESCENDING')\
                .limit(5)
            
            activities = []
            for doc in activities_query.get():
                activity = doc.to_dict()
                activities.append(f"- {activity.get('action', 'Unknown')} ({activity.get('timestamp', 'Unknown time')})")
            
            return '\n'.join(activities) if activities else "No recent activities recorded."
        except Exception as e:
            logger.error(f"Error getting activities: {e}")
            return "Activity information unavailable."

    def _get_case_activities(self, case_id: str) -> str:
        """Get all case activities"""
        try:
            activities_query = self.firestore_client.collection('case_activities')\
                .where('caseId', '==', case_id)\
                .order_by('timestamp', direction='DESCENDING')\
                .limit(20)
            
            activities = []
            for doc in activities_query.get():
                activity = doc.to_dict()
                activities.append(f"- {activity.get('action', 'Unknown')} ({activity.get('timestamp', 'Unknown time')})")
            
            return '\n'.join(activities) if activities else "No activities recorded."
        except Exception as e:
            logger.error(f"Error getting case activities: {e}")
            return "Activity information unavailable."

    def _create_basic_case_overview(self, case_data: Dict, documents_summary: str) -> str:
        """Create basic case overview when AI is unavailable"""
        doc_count = len(documents_summary.split('Document:')) - 1 if documents_summary else 0
        
        return f"""📋 **Case Overview: {case_data.get('title', 'Untitled Case')}**

**📝 Basic Information:**
- **Type:** {case_data.get('type', 'General')}
- **Status:** {case_data.get('status', 'Active')}
- **Priority:** {case_data.get('priority', 'Medium')}
- **Created:** {case_data.get('createdAt', 'Unknown')}
- **Last Updated:** {case_data.get('updatedAt', 'Unknown')}

**📄 Documents:** {doc_count} documents uploaded

**📋 Description:**
{case_data.get('description', 'No description available.')}

**🎯 Current Focus:**
- Review and organize case documents
- Identify key legal issues
- Develop case strategy
- Prepare for next steps

**💡 Recommendations:**
- Ensure all relevant documents are uploaded
- Consider running a comprehensive case analysis
- Review document completeness
- Identify any missing information or evidence"""

    def _create_basic_document_summary(self, documents: str) -> str:
        """Create basic document summary when AI is unavailable"""
        doc_count = documents.count('filename:')
        
        return f"""📄 **Document Summary**

**📊 Overview:**
- **Total Documents:** {doc_count}
- **Processing Status:** Documents uploaded and processed

**📋 Document Collection:**
{documents[:1000]}{'...' if len(documents) > 1000 else ''}

**💡 Recommendations:**
- Review document organization and naming
- Ensure all relevant documents are included
- Consider creating document categories
- Verify document completeness for case needs"""

    def _create_basic_status_update(self, case_data: Dict, doc_counts: str) -> str:
        """Create basic status update when AI is unavailable"""
        return f"""📊 **Status Update - {case_data.get('title', 'Case')}**

**🎯 Current Status:** {case_data.get('status', 'Active')}
**📅 Last Updated:** {case_data.get('updatedAt', 'Unknown')}

**📄 Document Status:**
{doc_counts}

**🔄 Current Phase:**
Case is in active management phase with document collection and analysis underway.

**✅ Recent Progress:**
- Case setup completed
- Documents uploaded and processed
- Ready for detailed analysis

**📋 Next Steps:**
- Continue document collection as needed
- Run comprehensive case analysis
- Identify key issues and strategy
- Prepare action plan

**⚠️ Attention Items:**
- Ensure all relevant documents are collected
- Review case timeline and deadlines
- Consider additional evidence needs"""

    def _create_basic_progress_summary(self, case_data: Dict, activities: str) -> str:
        """Create basic progress summary when AI is unavailable"""
        return f"""📈 **Progress Summary**

**🏁 Case Milestones:**
- ✅ Case created and configured
- ✅ Initial documents uploaded
- ✅ Processing and analysis setup
- 🔄 Ongoing document review and analysis

**📊 Current Progress:**
{activities}

**🎯 Achievements:**
- Case infrastructure established
- Document processing pipeline active
- AI analysis capabilities enabled
- Secure collaboration environment ready

**📅 Timeline:**
- **Started:** {case_data.get('createdAt', 'Unknown')}
- **Current Status:** {case_data.get('status', 'Active')}
- **Last Activity:** {case_data.get('updatedAt', 'Unknown')}

**🔜 Upcoming Goals:**
- Complete comprehensive case analysis
- Develop case strategy and action plan
- Organize findings and recommendations
- Prepare progress reports for stakeholders"""

    def _create_basic_conversation_summary(self, messages: List[Dict]) -> str:
        """Create basic conversation summary when AI is unavailable"""
        user_messages = [msg for msg in messages if msg.get('type') == 'user']
        ai_messages = [msg for msg in messages if msg.get('type') == 'ai']
        
        return f"""💬 **Conversation Summary**

**📊 Overview:**
- **Total Messages:** {len(messages)}
- **User Questions:** {len(user_messages)}
- **AI Responses:** {len(ai_messages)}

**🗣️ Recent Topics:**
Based on the conversation, you've been discussing case-related topics and getting assistance with legal matters.

**🎯 Main Focus Areas:**
- Case analysis and review
- Document examination  
- Legal guidance and advice
- Strategy and planning

**📋 Key Interactions:**
The conversation has covered various aspects of case management and legal analysis.

**🔜 Follow-up:**
Continue exploring specific aspects of your case that need attention or clarification."""

    def _fallback_summary_guidance(self, message: str) -> str:
        """Provide fallback guidance when AI is unavailable"""
        return f"""📋 **Summary Assistance**

You asked: "{message}"

Here are some ways I can help with case summaries:

**🎯 Types of Summaries Available:**
- **Case Overview**: Complete picture of the case
- **Document Summary**: Analysis of uploaded documents
- **Status Update**: Current case status and progress
- **Key Issues**: Main legal and factual issues
- **Progress Report**: Milestones and achievements
- **Conversation Summary**: Recent discussion highlights

**💡 Summary Best Practices:**
- Focus on key facts and issues
- Organize information logically
- Highlight important deadlines
- Note areas needing attention
- Include actionable next steps

**📋 How to Get Better Summaries:**
- Be specific about what you want summarized
- Ensure relevant documents are uploaded
- Provide context about your needs
- Ask follow-up questions for clarification

Would you like me to create a specific type of summary for your case?"""