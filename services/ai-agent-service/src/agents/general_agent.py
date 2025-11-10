#services/ai-agent-service/src/agents/general_agent.py
import logging
import time
from typing import Dict, Any, List, Optional
import google.generativeai as genai
import os

logger = logging.getLogger(__name__)

class GeneralAgent:
    """AI agent for general legal assistance and guidance"""
    
    def __init__(self, firestore_client, search_tool, document_tool):
        self.firestore_client = firestore_client
        self.search_tool = search_tool
        self.document_tool = document_tool
        
        # Initialize Gemini
        try:
            api_key = os.environ.get('GOOGLE_AI_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.5-pro')
            else:
                self.model = None
                logger.warning("⚠️ Gemini API key not found, using fallback responses")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            self.model = None
        
        logger.info("✅ GeneralAgent initialized")

    def test_connection(self):
        """Test agent connection"""
        try:
            if self.model:
                response = self.model.generate_content("Test general legal agent")
                return bool(response.text)
            return True
        except Exception as e:
            logger.error(f"General agent test failed: {e}")
            raise

    def process_message(self, case_id: str, user_id: str, message: str, conversation_history: List[Dict] = None) -> Optional[str]:
        """Process message for general legal assistance"""
        try:
            logger.info(f"⚖️ GeneralAgent processing message for case {case_id}")
            
            # Analyze the message to determine type of assistance needed
            assistance_type = self._analyze_assistance_type(message)
            
            if assistance_type == 'legal_advice':
                return self._provide_legal_guidance(case_id, message, conversation_history)
            elif assistance_type == 'case_strategy':
                return self._provide_case_strategy(case_id, message)
            elif assistance_type == 'procedure_guidance':
                return self._provide_procedure_guidance(message)
            elif assistance_type == 'research_help':
                return self._provide_research_assistance(case_id, message)
            elif assistance_type == 'risk_assessment':
                return self._provide_risk_assessment(case_id, message)
            elif assistance_type == 'settlement_analysis':
                return self._provide_settlement_analysis(case_id, message)
            elif assistance_type == 'timeline_guidance':
                return self._provide_timeline_guidance(case_id, message)
            else:
                return self._general_legal_assistance(case_id, message, conversation_history)
                
        except Exception as e:
            logger.error(f"❌ GeneralAgent error: {e}")
            return "I encountered an error while processing your request. Please try rephrasing your question or contact support if the issue persists."

    def _analyze_assistance_type(self, message: str) -> str:
        """Analyze message to determine type of assistance needed"""
        message_lower = message.lower()
        
        # Legal advice keywords
        if any(word in message_lower for word in ['advice', 'recommend', 'should i', 'what do you think', 'opinion']):
            return 'legal_advice'
        
        # Strategy keywords
        if any(word in message_lower for word in ['strategy', 'approach', 'plan', 'tactics', 'how to handle']):
            return 'case_strategy'
        
        # Procedure keywords
        if any(word in message_lower for word in ['procedure', 'process', 'steps', 'how to', 'court rules']):
            return 'procedure_guidance'
        
        # Research keywords
        if any(word in message_lower for word in ['research', 'law', 'statute', 'case law', 'precedent']):
            return 'research_help'
        
        # Risk keywords
        if any(word in message_lower for word in ['risk', 'danger', 'problem', 'issue', 'concern']):
            return 'risk_assessment'
        
        # Settlement keywords
        if any(word in message_lower for word in ['settlement', 'negotiate', 'resolve', 'compromise']):
            return 'settlement_analysis'
        
        # Timeline keywords
        if any(word in message_lower for word in ['timeline', 'deadline', 'when', 'schedule', 'timing']):
            return 'timeline_guidance'
        
        return 'general_assistance'

    def _provide_legal_guidance(self, case_id: str, message: str, conversation_history: List[Dict] = None) -> str:
        """Provide general legal guidance"""
        try:
            case_data = self._get_case_data(case_id)
            case_context = self.document_tool.get_case_context(case_id)
            
            # Build conversation context
            context = ""
            if conversation_history:
                context = "Previous conversation context:\n"
                for msg in conversation_history[-3:]:
                    role = "User" if msg.get('type') == 'user' else "Assistant"
                    context += f"{role}: {msg.get('message', '')}\n"
            
            prompt = f"""
            As a senior legal advisor, please provide guidance on this legal question:

            User question: "{message}"

            Case information:
            - Case: {case_data.get('title', 'Legal Matter')}
            - Type: {case_data.get('type', 'General')}
            - Status: {case_data.get('status', 'Active')}

            Case context:
            {case_context}

            {context}

            Please provide:
            1. Analysis of the legal question
            2. Relevant legal principles and considerations
            3. Practical guidance and recommendations
            4. Potential risks or issues to consider
            5. Suggested next steps or actions

            Important: This is general guidance only and does not constitute formal legal advice. 
            Recommend consulting with qualified legal counsel for specific legal decisions.

            Keep the response professional, practical, and actionable.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"⚖️ **Legal Guidance**\n\n{response.text}\n\n📋 **Disclaimer:** This guidance is for informational purposes only and does not constitute formal legal advice. Please consult with qualified legal counsel for specific legal decisions."
            
            return self._fallback_legal_guidance(message, case_data)
            
        except Exception as e:
            logger.error(f"Legal guidance error: {e}")
            return "I encountered an error while providing legal guidance. Please try rephrasing your question or provide more specific details."

    def _provide_case_strategy(self, case_id: str, message: str) -> str:
        """Provide case strategy advice"""
        try:
            case_data = self._get_case_data(case_id)
            case_analysis = self._get_recent_case_analysis(case_id)
            
            prompt = f"""
            As a legal strategist, please provide strategic advice for this case:

            User request: "{message}"

            Case information:
            - Title: {case_data.get('title', 'Legal Matter')}
            - Type: {case_data.get('type', 'General')} 
            - Priority: {case_data.get('priority', 'Medium')}
            - Status: {case_data.get('status', 'Active')}

            Recent analysis:
            {case_analysis}

            Please provide strategic guidance covering:
            1. **Strategic Approach**: Overall strategy recommendations
            2. **Key Objectives**: Primary goals and desired outcomes
            3. **Tactical Considerations**: Specific tactics and methods
            4. **Resource Allocation**: How to prioritize time and resources
            5. **Timeline Strategy**: Optimal timing and sequencing
            6. **Risk Mitigation**: How to minimize strategic risks
            7. **Success Metrics**: How to measure progress and success

            Focus on practical, actionable strategic advice for legal professionals.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"🎯 **Case Strategy Advice**\n\n{response.text}"
            
            return self._fallback_strategy_guidance(message, case_data)
            
        except Exception as e:
            logger.error(f"Case strategy error: {e}")
            return "I encountered an error while providing strategy advice. Please provide more details about the strategic challenge you're facing."

    def _provide_procedure_guidance(self, message: str) -> str:
        """Provide legal procedure guidance"""
        try:
            prompt = f"""
            As a legal procedure expert, please provide guidance on this procedural question:

            User question: "{message}"

            Please provide:
            1. **Procedural Overview**: Explanation of the relevant procedure
            2. **Required Steps**: Step-by-step process
            3. **Key Requirements**: Important requirements and deadlines
            4. **Common Pitfalls**: What to avoid
            5. **Best Practices**: Recommended approaches
            6. **Resources**: Where to find additional information
            7. **Practical Tips**: Helpful implementation advice

            Focus on practical guidance that legal professionals can implement.
            Include reminders about local rule variations and the importance of checking current requirements.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"📋 **Procedure Guidance**\n\n{response.text}\n\n⚠️ **Important:** Procedural rules can vary by jurisdiction and change over time. Always verify current local rules and requirements."
            
            return self._fallback_procedure_guidance(message)
            
        except Exception as e:
            logger.error(f"Procedure guidance error: {e}")
            return "I encountered an error while providing procedure guidance. Please be more specific about the legal procedure you need help with."

    def _provide_research_assistance(self, case_id: str, message: str) -> str:
        """Provide legal research assistance"""
        try:
            case_data = self._get_case_data(case_id)
            
            prompt = f"""
            As a legal research specialist, please help with this research request:

            User request: "{message}"

            Case context: {case_data.get('title', 'Legal Matter')} ({case_data.get('type', 'General')})

            Please provide:
            1. **Research Strategy**: How to approach this research
            2. **Key Legal Areas**: Relevant areas of law to investigate
            3. **Primary Sources**: Statutes, regulations, and case law to review
            4. **Secondary Sources**: Treatises, articles, and practice guides
            5. **Search Terms**: Effective keywords and phrases
            6. **Research Databases**: Recommended research platforms
            7. **Organization Tips**: How to organize and track findings

            Focus on efficient research methods and reliable sources.
            Include both traditional and modern research approaches.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"🔍 **Legal Research Assistance**\n\n{response.text}"
            
            return self._fallback_research_guidance(message)
            
        except Exception as e:
            logger.error(f"Research assistance error: {e}")
            return "I encountered an error while providing research assistance. Please specify what legal topic or issue you need help researching."

    def _provide_risk_assessment(self, case_id: str, message: str) -> str:
        """Provide risk assessment"""
        try:
            case_data = self._get_case_data(case_id)
            case_analysis = self._get_recent_case_analysis(case_id)
            
            prompt = f"""
            As a legal risk analyst, please assess the risks related to this question:

            User concern: "{message}"

            Case: {case_data.get('title', 'Legal Matter')}
            Type: {case_data.get('type', 'General')}

            Available analysis:
            {case_analysis}

            Please provide risk assessment covering:
            1. **Risk Identification**: Specific risks identified
            2. **Risk Level**: High/Medium/Low risk categorization
            3. **Impact Analysis**: Potential consequences of each risk
            4. **Probability Assessment**: Likelihood of risk occurring
            5. **Mitigation Strategies**: How to reduce or manage risks
            6. **Contingency Planning**: What to do if risks materialize
            7. **Monitoring Recommendations**: How to track risk factors

            Focus on practical risk management for legal professionals.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"⚠️ **Risk Assessment**\n\n{response.text}"
            
            return self._fallback_risk_assessment(message, case_data)
            
        except Exception as e:
            logger.error(f"Risk assessment error: {e}")
            return "I encountered an error while assessing risks. Please provide more specific details about the risks or concerns you'd like me to analyze."

    def _provide_settlement_analysis(self, case_id: str, message: str) -> str:
        """Provide settlement analysis"""
        try:
            case_data = self._get_case_data(case_id)
            case_context = self.document_tool.get_case_context(case_id)
            
            prompt = f"""
            As a settlement negotiation expert, please provide analysis on this settlement question:

            User question: "{message}"

            Case: {case_data.get('title', 'Legal Matter')}
            Type: {case_data.get('type', 'General')}

            Case context:
            {case_context}

            Please analyze:
            1. **Settlement Feasibility**: Likelihood of successful settlement
            2. **Valuation Factors**: Key factors affecting case value
            3. **Negotiation Position**: Strengths and weaknesses
            4. **Settlement Range**: Potential settlement parameters
            5. **Negotiation Strategy**: Recommended approach
            6. **Timing Considerations**: Optimal timing for settlement discussions
            7. **Alternative Outcomes**: Comparison with litigation outcomes

            Focus on practical settlement strategy and negotiation tactics.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"🤝 **Settlement Analysis**\n\n{response.text}"
            
            return self._fallback_settlement_analysis(message, case_data)
            
        except Exception as e:
            logger.error(f"Settlement analysis error: {e}")
            return "I encountered an error while analyzing settlement options. Please provide more details about the settlement situation you're considering."

    def _provide_timeline_guidance(self, case_id: str, message: str) -> str:
        """Provide timeline and deadline guidance"""
        try:
            case_data = self._get_case_data(case_id)
            
            prompt = f"""
            As a legal project manager, please provide timeline guidance for this question:

            User question: "{message}"

            Case: {case_data.get('title', 'Legal Matter')}
            Type: {case_data.get('type', 'General')}
            Created: {case_data.get('createdAt', 'Unknown')}

            Please provide:
            1. **Timeline Framework**: Recommended timeline structure
            2. **Key Milestones**: Critical deadlines and milestones
            3. **Dependencies**: Tasks that depend on others
            4. **Buffer Time**: Recommended cushions for delays
            5. **Critical Path**: Most time-sensitive activities
            6. **Resource Planning**: When to engage resources
            7. **Contingency Planning**: Alternative timelines if issues arise

            Focus on practical project management for legal matters.
            Include consideration of court schedules and opposing party timelines.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return f"📅 **Timeline Guidance**\n\n{response.text}"
            
            return self._fallback_timeline_guidance(message, case_data)
            
        except Exception as e:
            logger.error(f"Timeline guidance error: {e}")
            return "I encountered an error while providing timeline guidance. Please specify what timeline or deadline questions you have."

    def _general_legal_assistance(self, case_id: str, message: str, conversation_history: List[Dict] = None) -> str:
        """Provide general legal assistance"""
        try:
            case_context = self.document_tool.get_case_context(case_id)
            
            prompt = f"""
            As a general legal assistant, please help with this question:

            User question: "{message}"

            Case context:
            {case_context}

            Please provide helpful guidance covering:
            - Legal principles relevant to the question
            - Practical considerations and implications
            - Recommended actions or next steps
            - Resources for additional information
            - Potential issues or concerns to consider

            Keep the response professional, practical, and actionable for legal professionals.
            If the question is outside typical legal scope, explain why and suggest alternatives.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    return response.text
            
            return self._fallback_general_assistance(message)
            
        except Exception as e:
            logger.error(f"General legal assistance error: {e}")
            return "I'm here to help with your legal questions. Could you please provide more details or rephrase your question so I can better assist you?"

    def analyze_case_insights(self, case_id: str, case_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze case for AI insights"""
        try:
            case_context = self.document_tool.get_case_context(case_id)
            
            prompt = f"""
            Please analyze this legal case and provide insights:

            Case: {case_data.get('title', 'Legal Matter')}
            Type: {case_data.get('type', 'General')}
            Status: {case_data.get('status', 'Active')}

            Context:
            {case_context}

            Please provide:
            1. Key topics and themes (list of 5-7 topics)
            2. Recent activity summary (brief description)
            3. Suggested actions (3-5 actionable recommendations)
            4. Risk factors (3-5 potential risks)
            5. Opportunities (3-5 potential opportunities or advantages)

            Format as structured data that can be parsed.
            """
            
            if self.model:
                response = self.model.generate_content(prompt)
                if response.text:
                    # Parse response into structured data
                    return self._parse_insights_response(response.text)
            
            return self._create_basic_insights(case_data)
            
        except Exception as e:
            logger.error(f"Case insights analysis error: {e}")
            return None

    # Helper methods
    def _get_case_data(self, case_id: str) -> Dict[str, Any]:
        """Get case data from Firestore"""
        try:
            case_ref = self.firestore_client.collection('cases').document(case_id)
            case_doc = case_ref.get()
            return case_doc.to_dict() if case_doc.exists else {}
        except Exception as e:
            logger.error(f"Error getting case data: {e}")
            return {}

    def _get_recent_case_analysis(self, case_id: str) -> str:
        """Get recent case analysis if available"""
        try:
            analysis_query = self.firestore_client.collection('case_analysis')\
                .where('caseId', '==', case_id)\
                .order_by('analyzedAt', direction='DESCENDING')\
                .limit(1)
            
            docs = analysis_query.get()
            if docs:
                analysis = docs[0].to_dict()
                return f"Executive Summary: {analysis.get('executiveSummary', 'No analysis available')}"
            
            return "No recent case analysis available."
        except Exception as e:
            logger.error(f"Error getting case analysis: {e}")
            return "Case analysis information unavailable."

    def _parse_insights_response(self, response: str) -> Dict[str, Any]:
        """Parse AI insights response into structured data"""
        try:
            insights = {
                'keyTopics': [],
                'recentActivity': '',
                'suggestedActions': [],
                'riskFactors': [],
                'opportunities': []
            }
            
            lines = response.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Identify sections
                if 'key topics' in line.lower() or 'topics' in line.lower():
                    current_section = 'keyTopics'
                elif 'recent activity' in line.lower() or 'activity' in line.lower():
                    current_section = 'recentActivity'
                elif 'suggested actions' in line.lower() or 'actions' in line.lower():
                    current_section = 'suggestedActions'
                elif 'risk factors' in line.lower() or 'risks' in line.lower():
                    current_section = 'riskFactors'
                elif 'opportunities' in line.lower():
                    current_section = 'opportunities'
                elif line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '•')):
                    # Extract list items
                    item = line.split('.', 1)[-1].strip() if '.' in line else line[1:].strip()
                    if current_section in ['keyTopics', 'suggestedActions', 'riskFactors', 'opportunities']:
                        insights[current_section].append(item)
                elif current_section == 'recentActivity' and not line.startswith(('1.', '2.', '3.')):
                    insights['recentActivity'] += line + ' '
            
            return insights
            
        except Exception as e:
            logger.error(f"Error parsing insights response: {e}")
            return self._create_basic_insights({})

    def _create_basic_insights(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create basic insights when AI is unavailable"""
        return {
            'keyTopics': [
                'Case management and organization',
                'Document review and analysis', 
                'Legal strategy development',
                'Risk assessment and mitigation'
            ],
            'recentActivity': f'Case "{case_data.get("title", "Legal Matter")}" is in {case_data.get("status", "active")} status with ongoing document management.',
            'suggestedActions': [
                'Review and organize all case documents',
                'Conduct comprehensive case analysis',
                'Develop strategic action plan',
                'Identify key legal issues and risks'
            ],
            'riskFactors': [
                'Incomplete document collection',
                'Missing critical evidence',
                'Approaching deadlines',
                'Regulatory compliance requirements'
            ],
            'opportunities': [
                'Strong document organization system',
                'AI-powered analysis capabilities',
                'Comprehensive case management tools',
                'Efficient collaboration platform'
            ]
        }

    # Fallback methods when AI is unavailable
    def _fallback_legal_guidance(self, message: str, case_data: Dict) -> str:
        return f"""⚖️ **Legal Guidance**

**Your Question:** "{message}"

**General Legal Considerations:**

📋 **Key Principles:**
- Every legal situation is unique and fact-specific
- Legal outcomes depend on applicable laws and jurisdiction
- Professional legal counsel is essential for important decisions
- Documentation and evidence are critical

🎯 **Recommended Approach:**
1. **Gather Information**: Collect all relevant facts and documents
2. **Research Applicable Law**: Identify relevant statutes and case law
3. **Analyze Options**: Consider all available legal strategies
4. **Assess Risks**: Evaluate potential outcomes and consequences
5. **Seek Counsel**: Consult with qualified legal professionals

⚠️ **Important Considerations for {case_data.get('type', 'Legal')} matters:**
- Jurisdiction-specific requirements
- Applicable statutes of limitations
- Procedural requirements and deadlines
- Potential liability and risk factors

📋 **Next Steps:**
- Document all relevant facts
- Research applicable legal standards
- Consider engaging specialized counsel
- Develop comprehensive strategy

**Disclaimer:** This guidance is for informational purposes only and does not constitute formal legal advice."""

    def _fallback_strategy_guidance(self, message: str, case_data: Dict) -> str:
        return f"""🎯 **Case Strategy Framework**

**Your Strategic Question:** "{message}"

**Strategic Analysis Framework:**

📊 **Case Assessment:**
- Current case status: {case_data.get('status', 'Active')}
- Case type: {case_data.get('type', 'General')}
- Priority level: {case_data.get('priority', 'Medium')}

🎯 **Strategic Objectives:**
1. **Primary Goals**: Define desired outcomes
2. **Success Metrics**: Establish measurable criteria
3. **Timeline Targets**: Set realistic deadlines
4. **Resource Allocation**: Plan staffing and budget

⚡ **Tactical Considerations:**
- **Evidence Strategy**: Gather and organize supporting evidence
- **Legal Research**: Identify favorable precedents and authorities
- **Risk Management**: Minimize exposure and vulnerabilities
- **Stakeholder Management**: Coordinate with all parties

📅 **Implementation Steps:**
1. Conduct comprehensive case analysis
2. Develop detailed action plan
3. Assign responsibilities and deadlines
4. Monitor progress and adjust as needed

💡 **Best Practices:**
- Regular strategy review and adjustment
- Clear communication with all team members
- Contingency planning for various scenarios
- Documentation of all strategic decisions"""

    def _fallback_procedure_guidance(self, message: str) -> str:
        return f"""📋 **Legal Procedure Guidance**

**Your Procedural Question:** "{message}"

**General Procedural Framework:**

📝 **Planning Phase:**
1. **Identify Requirements**: Determine applicable rules and procedures
2. **Check Deadlines**: Note all relevant time limits and deadlines
3. **Gather Documents**: Collect all necessary forms and supporting materials
4. **Verify Jurisdiction**: Ensure proper court or administrative body

⚖️ **Execution Phase:**
1. **Prepare Documents**: Draft all required pleadings or applications
2. **File Properly**: Submit documents according to local rules
3. **Serve Parties**: Provide proper notice to all required parties
4. **Track Deadlines**: Monitor all response and action deadlines

🔍 **Key Considerations:**
- **Local Rules**: Each jurisdiction may have specific requirements
- **Standing Requirements**: Verify authority to bring action
- **Service of Process**: Ensure proper notification procedures
- **Fee Requirements**: Prepare for applicable filing fees

⚠️ **Common Pitfalls to Avoid:**
- Missing critical deadlines
- Improper service of process
- Incomplete or incorrect documentation
- Failure to follow local court rules

📚 **Resources:**
- Local court rules and procedures
- State bar practice guides
- Court clerk's office guidance
- Legal research databases

**Important:** Always verify current local rules and requirements, as procedures can vary significantly by jurisdiction."""

    def _fallback_research_guidance(self, message: str) -> str:
        return f"""🔍 **Legal Research Strategy**

**Your Research Question:** "{message}"

**Research Methodology:**

📚 **Primary Sources (Start Here):**
1. **Statutes**: Relevant federal and state statutes
2. **Regulations**: Administrative rules and regulations
3. **Case Law**: Controlling and persuasive court decisions
4. **Constitutional Provisions**: Applicable constitutional law

📖 **Secondary Sources (For Context):**
1. **Legal Treatises**: Comprehensive topic coverage
2. **Law Review Articles**: Scholarly analysis and commentary
3. **Practice Guides**: Practical implementation guidance
4. **Legal Encyclopedias**: Broad topic overviews

🔍 **Research Strategy:**
1. **Start Broad**: Use secondary sources for background
2. **Narrow Focus**: Identify specific legal issues
3. **Find Primary Law**: Locate controlling authorities
4. **Update Research**: Ensure current validity
5. **Organize Findings**: Create systematic research notes

💻 **Research Tools:**
- **Legal Databases**: Westlaw, Lexis, Bloomberg Law
- **Free Resources**: Google Scholar, Justia, FindLaw
- **Court Websites**: Local court rules and decisions
- **Government Sites**: Statutory and regulatory materials

📋 **Research Tips:**
- Use multiple search terms and approaches
- Check for recent developments and updates
- Verify jurisdiction-specific variations
- Track your research path and sources

🎯 **Organization:**
- Create outline of legal issues
- Categorize sources by relevance
- Note citation information for all sources
- Prepare summary of key findings"""

    def _fallback_risk_assessment(self, message: str, case_data: Dict) -> str:
        return f"""⚠️ **Risk Assessment Framework**

**Your Risk Concern:** "{message}"

**Risk Analysis Structure:**

🎯 **Risk Categories:**

**📋 Legal Risks:**
- Adverse legal precedents
- Jurisdictional challenges
- Procedural compliance issues
- Evidence admissibility problems

**💰 Financial Risks:**
- Litigation costs and expenses
- Potential damages or penalties
- Fee shifting provisions
- Collection difficulties

**⏰ Timeline Risks:**
- Statute of limitations issues
- Court scheduling delays
- Discovery deadline pressures
- Settlement timing considerations

**👥 Operational Risks:**
- Resource allocation challenges
- Team coordination difficulties
- Client relationship management
- Public relations considerations

🔍 **Risk Assessment Process:**
1. **Identify**: List all potential risks
2. **Assess**: Evaluate probability and impact
3. **Prioritize**: Rank risks by severity
4. **Mitigate**: Develop prevention strategies
5. **Monitor**: Track risk factors over time

📊 **Risk Mitigation Strategies:**
- **Prevention**: Eliminate risk sources where possible
- **Reduction**: Minimize risk probability or impact
- **Transfer**: Use insurance or contractual protection
- **Acceptance**: Acknowledge and plan for unavoidable risks

💡 **Case-Specific Considerations for {case_data.get('type', 'Legal')} matters:**
- Industry-specific regulatory requirements
- Typical challenge areas and pitfalls
- Standard mitigation approaches
- Benchmark outcomes and expectations"""

    def _fallback_settlement_analysis(self, message: str, case_data: Dict) -> str:
        return f"""🤝 **Settlement Analysis Framework**

**Your Settlement Question:** "{message}"

**Settlement Evaluation Factors:**

💰 **Valuation Components:**
- **Economic Damages**: Quantifiable financial losses
- **Non-Economic Damages**: Pain, suffering, reputation
- **Punitive Damages**: If applicable in jurisdiction
- **Attorney Fees**: Potential fee shifting or recovery

⚖️ **Strength Assessment:**
- **Liability Analysis**: Strength of legal claims
- **Evidence Quality**: Supporting documentation and witnesses
- **Legal Precedents**: Favorable vs. unfavorable case law
- **Procedural Advantages**: Discovery, motion practice

🎯 **Settlement Considerations:**
- **Cost-Benefit Analysis**: Settlement vs. litigation costs
- **Time Factors**: Resolution timeline preferences
- **Risk Tolerance**: Client's appetite for uncertainty
- **Relationship Preservation**: Ongoing business relationships

📊 **Negotiation Strategy:**
1. **Preparation**: Research opponent's position and constraints
2. **Opening Position**: Set initial offer or demand strategically
3. **Concession Planning**: Plan negotiation moves and limits
4. **Alternative Solutions**: Consider creative resolution options
5. **Implementation**: Structure enforceable settlement terms

⏰ **Timing Considerations:**
- **Early Settlement**: Lower costs, less risk, limited information
- **Post-Discovery**: More information, higher costs, better case assessment
- **Pre-Trial**: Final opportunity, maximum pressure, highest costs

💡 **Best Practices:**
- Document all settlement discussions appropriately
- Consider tax implications of settlement terms
- Plan for enforcement and compliance mechanisms
- Maintain confidentiality as required"""

    def _fallback_timeline_guidance(self, message: str, case_data: Dict) -> str:
        return f"""📅 **Timeline Management Framework**

**Your Timeline Question:** "{message}"

**Case Timeline Structure:**

🎯 **Phase-Based Planning:**

**📋 Phase 1: Case Initiation (0-30 days)**
- Case setup and initial assessment
- Document collection and organization
- Initial research and strategy development
- Team assignment and coordination

**🔍 Phase 2: Discovery & Analysis (1-6 months)**
- Comprehensive document review
- Evidence gathering and analysis
- Legal research and case law review
- Initial witness interviews and evidence preservation

**⚙️ Phase 3: Motion Practice & Pre-Trial (3-9 months)**
- File and respond to dispositive and discovery motions
- Narrow issues through motions in limine and procedural filings
- Focused depositions and expert identification
- Prepare exhibits and trial notebooks

**🏛️ Phase 4: Trial Preparation & Trial (6-12+ months)**
- Finalize witness lists and trial strategy
- Conduct mock examinations and trial runs
- Prepare jury instructions and trial briefs (if applicable)
- Execute trial presentation and evidence admission

**🔁 Phase 5: Post-Trial & Resolution**
- Prepare for post-trial motions or appeals as needed
- Implement settlement or enforcement steps
- Close out case files and document lessons learned

**📋 Practical Tips:**
- Build a timeline with milestones, owners, and buffer time for each task
- Track court deadlines and statutory limitations closely
- Allocate resources early for high-priority tasks (e.g., expert work)
- Maintain regular status updates with the team and client

**📌 Case Context:** {case_data.get('type', 'Legal')} matter; adjust timelines based on jurisdictional rules and case complexity.

**Next Steps:**
1. Create a detailed milestone plan with dates and responsible parties
2. Identify critical path tasks and assign extra buffer time
3. Monitor progress weekly and adjust the timeline as new information arrives
4. Consider early settlement discussions if it aligns with client goals

**Important:** Timelines vary widely by jurisdiction and case specifics; always verify local rules and court schedules when planning."""