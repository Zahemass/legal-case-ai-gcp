import logging
import time
from typing import Dict, Any, List, Optional
from agents.evidence_agent import EvidenceAgent
from agents.summary_agent import SummaryAgent
from agents.draft_agent import DraftAgent
from agents.general_agent import GeneralAgent
from tools.search_tool import SearchTool
from tools.document_tool import DocumentTool

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """Orchestrates multiple AI agents for legal case assistance"""
    
    def __init__(self, firestore_client, storage_client):
        self.firestore_client = firestore_client
        self.storage_client = storage_client
        
        # Initialize tools
        self.search_tool = SearchTool(firestore_client)
        self.document_tool = DocumentTool(firestore_client, storage_client)
        
        # Initialize agents
        self.agents = {
            'evidence': EvidenceAgent(firestore_client, self.search_tool, self.document_tool),
            'summary': SummaryAgent(firestore_client, self.document_tool),
            'draft': DraftAgent(firestore_client, self.document_tool),
            'general': GeneralAgent(firestore_client, self.search_tool, self.document_tool)
        }
        
        logger.info("✅ AgentOrchestrator initialized with 4 agents")

    def test_agents(self) -> bool:
        """Test all agents are working"""
        try:
            for agent_name, agent in self.agents.items():
                if hasattr(agent, 'test_connection'):
                    agent.test_connection()
            return True
        except Exception as e:
            logger.error(f"Agent test failed: {e}")
            raise

    def get_available_agents(self) -> List[Dict[str, Any]]:
        """Get list of available agents with their capabilities"""
        return [
            {
                'id': 'evidence',
                'name': 'Evidence Analyst',
                'description': 'Analyzes and searches through case evidence and documents',
                'icon': '🔍',
                'capabilities': [
                    'Document analysis',
                    'Evidence search',
                    'Fact extraction',
                    'Timeline reconstruction'
                ]
            },
            {
                'id': 'summary',
                'name': 'Case Summarizer',
                'description': 'Provides comprehensive case summaries and overviews',
                'icon': '📋',
                'capabilities': [
                    'Case summarization',
                    'Key points extraction',
                    'Status updates',
                    'Progress tracking'
                ]
            },
            {
                'id': 'draft',
                'name': 'Document Drafter',
                'description': 'Helps draft legal documents and correspondence',
                'icon': '📝',
                'capabilities': [
                    'Legal document drafting',
                    'Letter writing',
                    'Contract reviews',
                    'Motion preparation'
                ]
            },
            {
                'id': 'general',
                'name': 'Legal Assistant',
                'description': 'General legal assistance and case guidance',
                'icon': '⚖️',
                'capabilities': [
                    'Legal advice',
                    'Case strategy',
                    'Research assistance',
                    'General guidance'
                ]
            }
        ]

    def process_message(self, case_id: str, user_id: str, message: str, conversation_history: List[Dict] = None) -> Optional[Dict[str, Any]]:
        """Process user message and route to appropriate agent"""
        start_time = time.time()
        
        try:
            logger.info(f"🤖 Processing message for case {case_id}")
            
            # Determine which agent should handle the message
            selected_agent = self._select_agent(message, conversation_history)
            
            logger.info(f"🎯 Selected agent: {selected_agent}")
            
            # Get agent instance
            agent = self.agents.get(selected_agent)
            if not agent:
                logger.error(f"Agent {selected_agent} not found")
                return None
            
            # Process message with selected agent
            response = agent.process_message(
                case_id=case_id,
                user_id=user_id,
                message=message,
                conversation_history=conversation_history or []
            )
            
            processing_time = time.time() - start_time
            
            if response:
                result = {
                    'response': response,
                    'agent': selected_agent,
                    'processing_time': processing_time,
                    'confidence': self._calculate_confidence(response, selected_agent),
                    'timestamp': time.time()
                }
                
                logger.info(f"✅ Message processed by {selected_agent} in {processing_time:.2f}s")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Message processing error: {e}")
            return None

    def _select_agent(self, message: str, conversation_history: List[Dict] = None) -> str:
        """Select the most appropriate agent for the message"""
        try:
            message_lower = message.lower()
            
            # Evidence-related keywords
            evidence_keywords = [
                'evidence', 'document', 'search', 'find', 'locate', 'extract',
                'timeline', 'chronology', 'facts', 'witness', 'testimony',
                'exhibits', 'proof', 'analysis', 'examine'
            ]
            
            # Summary-related keywords
            summary_keywords = [
                'summary', 'summarize', 'overview', 'status', 'progress',
                'key points', 'main issues', 'brief', 'outline', 'recap'
            ]
            
            # Draft-related keywords
            draft_keywords = [
                'draft', 'write', 'compose', 'create', 'letter', 'document',
                'motion', 'brief', 'contract', 'agreement', 'response',
                'correspondence', 'memo', 'proposal'
            ]
            
            # General legal keywords
            general_keywords = [
                'advice', 'strategy', 'legal', 'law', 'case', 'court',
                'judge', 'attorney', 'counsel', 'litigation', 'settlement',
                'rights', 'liability', 'damages', 'jurisdiction'
            ]
            
            # Count keyword matches for each agent
            scores = {
                'evidence': sum(1 for keyword in evidence_keywords if keyword in message_lower),
                'summary': sum(1 for keyword in summary_keywords if keyword in message_lower),
                'draft': sum(1 for keyword in draft_keywords if keyword in message_lower),
                'general': sum(1 for keyword in general_keywords if keyword in message_lower)
            }
            
            # Check for specific patterns
            if any(word in message_lower for word in ['what is', 'tell me about', 'explain']):
                scores['general'] += 2
            
            if any(word in message_lower for word in ['find', 'search', 'look for']):
                scores['evidence'] += 2
            
            if any(word in message_lower for word in ['summarize', 'overview', 'status']):
                scores['summary'] += 2
            
            if any(word in message_lower for word in ['write', 'draft', 'create']):
                scores['draft'] += 2
            
            # Consider conversation context
            if conversation_history:
                last_message = conversation_history[-1] if conversation_history else {}
                last_agent = last_message.get('agent')
                
                # Slight preference for continuing with same agent
                if last_agent and last_agent in scores:
                    scores[last_agent] += 0.5
            
            # Select agent with highest score
            selected_agent = max(scores, key=scores.get)
            
            # If no clear winner, use general agent
            if scores[selected_agent] == 0:
                selected_agent = 'general'
            
            return selected_agent
            
        except Exception as e:
            logger.error(f"Agent selection error: {e}")
            return 'general'  # Default fallback

    def _calculate_confidence(self, response: str, agent_type: str) -> float:
        """Calculate confidence score for the response"""
        try:
            confidence = 0.5  # Base confidence
            
            # Adjust based on response length and quality
            if response and len(response) > 50:
                confidence += 0.2
            
            if response and len(response) > 200:
                confidence += 0.1
            
            # Adjust based on agent specialization
            agent_confidence_bonus = {
                'evidence': 0.1,
                'summary': 0.1,
                'draft': 0.1,
                'general': 0.05
            }
            
            confidence += agent_confidence_bonus.get(agent_type, 0)
            
            # Check for indicators of uncertainty
            uncertainty_indicators = [
                'i\'m not sure', 'i don\'t know', 'unclear', 'uncertain',
                'maybe', 'possibly', 'might be', 'could be'
            ]
            
            if response:
                response_lower = response.lower()
                uncertainty_count = sum(1 for indicator in uncertainty_indicators if indicator in response_lower)
                confidence -= uncertainty_count * 0.1
            
            return min(1.0, max(0.0, confidence))
            
        except Exception:
            return 0.5

    def get_agent_capabilities(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed capabilities of a specific agent"""
        agents_info = {
            'evidence': {
                'name': 'Evidence Analyst',
                'description': 'Specialized in analyzing case evidence and documents',
                'capabilities': [
                    'Document content analysis',
                    'Evidence timeline reconstruction',
                    'Fact pattern identification',
                    'Witness statement analysis',
                    'Exhibit cross-referencing',
                    'Contradiction detection'
                ],
                'best_for': [
                    'Searching through case documents',
                    'Finding specific evidence',
                    'Analyzing document relationships',
                    'Building chronologies'
                ]
            },
            'summary': {
                'name': 'Case Summarizer',
                'description': 'Provides comprehensive case overviews and status updates',
                'capabilities': [
                    'Multi-document summarization',
                    'Key issue identification',
                    'Progress tracking',
                    'Status reporting',
                    'Milestone tracking',
                    'Case overview generation'
                ],
                'best_for': [
                    'Getting case overviews',
                    'Understanding key issues',
                    'Tracking progress',
                    'Preparing status reports'
                ]
            },
            'draft': {
                'name': 'Document Drafter',
                'description': 'Assists with drafting legal documents and correspondence',
                'capabilities': [
                    'Legal document creation',
                    'Motion drafting',
                    'Letter composition',
                    'Contract review assistance',
                    'Brief preparation',
                    'Template customization'
                ],
                'best_for': [
                    'Writing legal documents',
                    'Drafting correspondence',
                    'Preparing motions',
                    'Creating templates'
                ]
            },
            'general': {
                'name': 'Legal Assistant',
                'description': 'General legal guidance and case strategy assistance',
                'capabilities': [
                    'Legal advice and guidance',
                    'Case strategy development',
                    'Legal research assistance',
                    'Procedural guidance',
                    'Risk assessment',
                    'Settlement analysis'
                ],
                'best_for': [
                    'General legal questions',
                    'Case strategy discussions',
                    'Legal procedure guidance',
                    'Risk assessment'
                ]
            }
        }
        
        return agents_info.get(agent_id)

    def get_conversation_summary(self, case_id: str, message_count: int = 10) -> Optional[str]:
        """Generate a summary of recent conversation"""
        try:
            # Get recent messages
            messages_query = self.firestore_client.collection('chat_messages')\
                .where('caseId', '==', case_id)\
                .order_by('timestamp', direction='DESCENDING')\
                .limit(message_count)
            
            messages = []
            for doc in messages_query.get():
                msg_data = doc.to_dict()
                messages.append(msg_data)
            
            if not messages:
                return "No recent conversation to summarize."
            
            # Use summary agent to create conversation summary
            summary_agent = self.agents.get('summary')
            if summary_agent:
                return summary_agent.summarize_conversation(messages)
            
            return "Conversation summary unavailable."
            
        except Exception as e:
            logger.error(f"Conversation summary error: {e}")
            return "Error generating conversation summary."

    def get_case_insights(self, case_id: str) -> Dict[str, Any]:
        """Get AI-powered insights about the case"""
        try:
            insights = {
                'keyTopics': [],
                'recentActivity': '',
                'suggestedActions': [],
                'riskFactors': [],
                'opportunities': []
            }
            
            # Get case data
            case_ref = self.firestore_client.collection('cases').document(case_id)
            case_doc = case_ref.get()
            
            if not case_doc.exists:
                return insights
            
            case_data = case_doc.to_dict()
            
            # Use general agent to generate insights
            general_agent = self.agents.get('general')
            if general_agent:
                ai_insights = general_agent.analyze_case_insights(case_id, case_data)
                if ai_insights:
                    insights.update(ai_insights)
            
            return insights
            
        except Exception as e:
            logger.error(f"Case insights error: {e}")
            return {
                'keyTopics': [],
                'recentActivity': 'Error loading recent activity',
                'suggestedActions': [],
                'riskFactors': [],
                'opportunities': []
            }