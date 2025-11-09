# services/document-analysis-service/src/gemini_client.py
import logging
import time
import os
from typing import Optional, Dict, Any
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for Google's Gemini AI model"""
    
    def __init__(self):
        try:
            # Configure Gemini
            api_key = os.environ.get('GOOGLE_AI_API_KEY')
            if not api_key:
                raise Exception("GOOGLE_AI_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            
            # Initialize model
            self.model = genai.GenerativeModel('gemini-2.5-pro')
            
            # Generation config
            self.generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=2048,
                temperature=0.3,
                top_p=0.8,
                top_k=40
            )
            
            # Safety settings
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
            
            logger.info("✅ Gemini client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini client: {e}")
            raise

    def test_connection(self) -> bool:
        """Test connection to Gemini API"""
        try:
            response = self.model.generate_content(
                "Test connection",
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
        """Analyze document using Gemini"""
        try:
            logger.info("🤖 Starting Gemini analysis")
            start_time = time.time()
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            processing_time = time.time() - start_time
            
            if response.text:
                logger.info(f"✅ Gemini analysis completed in {processing_time:.2f}s")
                return response.text.strip()
            else:
                logger.warning("⚠️ Gemini returned empty response")
                return None
                
        except Exception as e:
            logger.error(f"❌ Gemini analysis error: {e}")
            return None

    def summarize_text(self, text: str, max_length: int = 500) -> Optional[str]:
        """Generate a summary of the text"""
        try:
            prompt = f"""
            Please provide a concise summary of the following text in approximately {max_length} characters:

            {text[:8000]}  # Limit input text

            Summary should be:
            - Clear and professional
            - Focused on key points
            - Appropriate for legal context
            - Maximum {max_length} characters
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            if response.text:
                summary = response.text.strip()
                # Truncate if too long
                if len(summary) > max_length:
                    summary = summary[:max_length-3] + "..."
                return summary
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Summarization error: {e}")
            return None

    def extract_key_points(self, text: str, max_points: int = 7) -> Optional[list]:
        """Extract key points from text"""
        try:
            prompt = f"""
            Please extract the {max_points} most important key points from the following text.
            Return them as a simple numbered list, one point per line:

            {text[:8000]}

            Format:
            1. First key point
            2. Second key point
            etc.
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            if response.text:
                # Parse the numbered list
                lines = response.text.strip().split('\n')
                points = []
                
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                        # Remove numbering/bullets
                        point = line.split('.', 1)[-1].strip() if '.' in line else line[1:].strip()
                        if point:
                            points.append(point)
                
                return points[:max_points]
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Key points extraction error: {e}")
            return []

    def assess_legal_relevance(self, text: str) -> Optional[str]:
        """Assess the legal relevance of the text"""
        try:
            prompt = f"""
            As a legal expert, please assess the legal relevance and significance of the following document.
            Consider:
            - Legal implications
            - Potential risks or issues
            - Compliance requirements
            - Contractual obligations
            - Regulatory considerations

            Document:
            {text[:8000]}

            Please provide a professional assessment in 2-3 paragraphs.
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
            logger.error(f"❌ Legal relevance assessment error: {e}")
            return None

    def get_recommendations(self, text: str, context: Dict[str, Any] = None) -> Optional[list]:
        """Get AI recommendations based on document analysis"""
        try:
            context_info = ""
            if context:
                context_info = f"""
                Document Context:
                - Filename: {context.get('filename', 'Unknown')}
                - Type: {context.get('contentType', 'Unknown')}
                - Case ID: {context.get('caseId', 'Unknown')}
                """
            
            prompt = f"""
            Based on the following legal document, please provide 3-5 actionable recommendations
            for legal professionals handling this document.

            {context_info}

            Document Content:
            {text[:8000]}

            Please provide practical, actionable recommendations such as:
            - Areas requiring legal review
            - Potential risks to address
            - Compliance considerations
            - Next steps or actions needed

            Format as a numbered list.
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            if response.text:
                # Parse recommendations
                lines = response.text.strip().split('\n')
                recommendations = []
                
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                        rec = line.split('.', 1)[-1].strip() if '.' in line else line[1:].strip()
                        if rec:
                            recommendations.append(rec)
                
                return recommendations[:5]  # Limit to 5 recommendations
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Recommendations error: {e}")
            return []