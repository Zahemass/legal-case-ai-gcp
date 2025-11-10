#services/case-analysis-service/src/gemini_client.py
import logging
import time
import os
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from dotenv import load_dotenv  # ✅ NEW

# ✅ Load environment variables from .env (even in local dev)
env_path = os.path.join(os.path.dirname(__file__), "../.env")
print(f"🔍 Loading .env from: {os.path.abspath(env_path)}")
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

class GeminiClient:
    """Enhanced Gemini client for case analysis"""
    
    def __init__(self):
        try:
            api_key = os.environ.get('GOOGLE_AI_API_KEY')
            if not api_key:
                raise Exception("GOOGLE_AI_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-pro')
            
            # Enhanced generation config for case analysis
            self.generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=4096,  # Increased for comprehensive analysis
                temperature=0.2,  # Lower temperature for more consistent legal analysis
                top_p=0.9,
                top_k=40
            )
            
            self.safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
            
            logger.info("✅ Enhanced Gemini client initialized for case analysis")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini client: {e}")
            raise

    def test_connection(self) -> bool:
        """Test connection to Gemini API"""
        try:
            response = self.model.generate_content(
                "Test legal analysis connection",
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            if response.text:
                logger.info("✅ Gemini connection test successful")
                return True
            else:
                raise Exception("No response from Gemini")
                
        except Exception as e:
            logger.error(f"❌ Gemini connection test failed: {e}")
            raise

    def analyze_document(self, prompt: str) -> Optional[str]:
        """Analyze document with enhanced legal context"""
        try:
            logger.info("🤖 Starting Gemini legal analysis")
            start_time = time.time()
            
            # Add legal context to prompt
            enhanced_prompt = f"""
            You are a senior legal analyst with expertise in case analysis and legal document review.
            Please provide a thorough, professional analysis following legal industry standards.

            {prompt}

            Please ensure your analysis is:
            - Comprehensive and detailed
            - Legally accurate and professional
            - Structured and well-organized
            - Actionable for legal professionals
            - Based on the evidence presented
            """
            
            response = self.model.generate_content(
                enhanced_prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            processing_time = time.time() - start_time
            
            if response.text:
                logger.info(f"✅ Gemini legal analysis completed in {processing_time:.2f}s")
                return response.text.strip()
            else:
                logger.warning("⚠️ Gemini returned empty response")
                return None
                
        except Exception as e:
            logger.error(f"❌ Gemini legal analysis error: {e}")
            return None

    def summarize_case(self, case_data: Dict[str, Any], combined_text: str, max_length: int = 1000) -> Optional[str]:
        """Generate comprehensive case summary"""
        try:
            prompt = f"""
            Please provide a comprehensive case summary for legal professionals.

            Case Information:
            - Title: {case_data.get('title', 'Unknown')}
            - Type: {case_data.get('type', 'General')}
            - Priority: {case_data.get('priority', 'Medium')}
            - Created: {case_data.get('createdAt', 'Unknown')}

            Case Documents Content:
            {combined_text[:8000]}  # Limit input

            Please provide a summary that includes:
            1. Case overview and background
            2. Key parties involved
            3. Main legal issues
            4. Current status
            5. Critical findings or evidence
            6. Next steps or recommendations

            Maximum length: {max_length} characters
            Target audience: Senior legal professionals
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            if response.text:
                summary = response.text.strip()
                if len(summary) > max_length:
                    summary = summary[:max_length-3] + "..."
                return summary
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Case summarization error: {e}")
            return None

    def extract_key_points(self, text: str, max_points: int = 10) -> List[str]:
        """Extract key legal points from case text"""
        try:
            prompt = f"""
            As a legal analyst, please extract the {max_points} most critical legal points from this case content.

            Focus on:
            - Key legal arguments
            - Important evidence
            - Critical facts
            - Significant precedents
            - Important deadlines or dates
            - Key contractual terms
            - Liability issues
            - Damages or financial implications

            Case Content:
            {text[:8000]}

            Please provide exactly {max_points} key points, formatted as:
            1. [Point 1]
            2. [Point 2]
            etc.

            Keep each point concise but comprehensive.
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            if response.text:
                lines = response.text.strip().split('\n')
                points = []
                
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                        point = line.split('.', 1)[-1].strip() if '.' in line else line[1:].strip()
                        if point:
                            points.append(point)
                
                return points[:max_points]
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Key points extraction error: {e}")
            return []

    def assess_case_strength(self, case_content: str) -> Optional[Dict[str, Any]]:
        """Assess overall case strength and viability"""
        try:
            prompt = f"""
            As a senior legal strategist, please assess the strength and viability of this case.

            Case Content:
            {case_content[:8000]}

            Please provide an assessment including:

            1. Overall Case Strength (Strong/Moderate/Weak)
            2. Probability of Success (High/Medium/Low)
            3. Key Strengths (3-5 points)
            4. Key Weaknesses (3-5 points)
            5. Critical Success Factors
            6. Major Risk Factors
            7. Strategic Recommendations

            Please format your response in a structured manner for easy parsing.
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            if response.text:
                # Parse structured response
                assessment = {
                    'overallStrength': 'Moderate',
                    'successProbability': 'Medium',
                    'strengths': [],
                    'weaknesses': [],
                    'successFactors': [],
                    'riskFactors': [],
                    'recommendations': [],
                    'fullAssessment': response.text.strip()
                }
                
                # Extract structured data from response
                lines = response.text.split('\n')
                current_section = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Identify sections
                    if 'overall case strength' in line.lower():
                        if 'strong' in line.lower():
                            assessment['overallStrength'] = 'Strong'
                        elif 'weak' in line.lower():
                            assessment['overallStrength'] = 'Weak'
                        elif 'moderate' in line.lower():
                            assessment['overallStrength'] = 'Moderate'
                    
                    elif 'probability of success' in line.lower():
                        if 'high' in line.lower():
                            assessment['successProbability'] = 'High'
                        elif 'low' in line.lower():
                            assessment['successProbability'] = 'Low'
                        elif 'medium' in line.lower():
                            assessment['successProbability'] = 'Medium'
                    
                    elif 'key strengths' in line.lower():
                        current_section = 'strengths'
                    elif 'key weaknesses' in line.lower():
                        current_section = 'weaknesses'
                    elif 'success factors' in line.lower():
                        current_section = 'successFactors'
                    elif 'risk factors' in line.lower():
                        current_section = 'riskFactors'
                    elif 'recommendations' in line.lower():
                        current_section = 'recommendations'
                    
                    # Extract items
                    elif line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                        item = line.split('.', 1)[-1].strip() if '.' in line else line[1:].strip()
                        if item and current_section in assessment:
                            assessment[current_section].append(item)
                
                return assessment
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Case strength assessment error: {e}")
            return None

    def generate_legal_strategy(self, case_data: Dict[str, Any], analysis_results: Dict[str, Any]) -> Optional[str]:
        """Generate comprehensive legal strategy"""
        try:
            prompt = f"""
            Based on the comprehensive case analysis, please develop a legal strategy for this case.

            Case Information:
            - Title: {case_data.get('title', 'Unknown')}
            - Type: {case_data.get('type', 'General')}
            - Priority: {case_data.get('priority', 'Medium')}

            Analysis Results:
            - Key Findings: {', '.join(analysis_results.get('keyFindings', [])[:5])}
            - Strengths: {', '.join(analysis_results.get('strengthsWeaknesses', {}).get('strengths', [])[:3])}
            - Weaknesses: {', '.join(analysis_results.get('strengthsWeaknesses', {}).get('weaknesses', [])[:3])}
            - Legal Issues: {len(analysis_results.get('legalIssues', []))} identified
            - Risk Level: {analysis_results.get('riskAssessment', {}).get('overallRiskLevel', 'Unknown')}

            Please develop a comprehensive legal strategy including:

            1. PRIMARY STRATEGY APPROACH
            2. TACTICAL CONSIDERATIONS
            3. EVIDENCE STRATEGY
            4. SETTLEMENT VS. LITIGATION ANALYSIS
            5. TIMELINE AND MILESTONES
            6. RESOURCE REQUIREMENTS
            7. CONTINGENCY PLANNING

            Provide strategic guidance suitable for senior legal counsel.
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            if response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Legal strategy generation error: {e}")
            return None