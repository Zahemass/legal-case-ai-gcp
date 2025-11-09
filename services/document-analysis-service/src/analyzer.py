# services/document-analysis-service/src/analyzer.py
import logging
import time
import re
from typing import Dict, Any, List, Optional
import nltk
import textstat
from gemini_client import GeminiClient

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
    from nltk.sentiment import SentimentIntensityAnalyzer
    from nltk.corpus import stopwords
    from nltk.tokenize import sent_tokenize, word_tokenize
    NLTK_AVAILABLE = True
except Exception as e:
    logger.warning(f"NLTK setup incomplete: {e}")
    NLTK_AVAILABLE = False

class DocumentAnalyzer:
    """Document analysis service using AI and NLP techniques"""
    
    def __init__(self, gemini_client: GeminiClient, firestore_client):
        self.gemini_client = gemini_client
        self.firestore_client = firestore_client
        
        if NLTK_AVAILABLE:
            self.sentiment_analyzer = SentimentIntensityAnalyzer()
            self.stop_words = set(stopwords.words('english'))
        else:
            self.sentiment_analyzer = None
            self.stop_words = set()
        
        logger.info("✅ DocumentAnalyzer initialized")

    def analyze_document(self, document_id: str, analysis_type: str = 'full') -> Dict[str, Any]:
        """Analyze a document and return comprehensive insights"""
        start_time = time.time()
        
        try:
            # Get document and extracted text
            document_data = self._get_document_data(document_id)
            extracted_text = self._get_extracted_text(document_id)
            
            if not extracted_text:
                raise Exception("No extracted text found for document")
            
            logger.info(f"🔍 Analyzing document {document_id} ({len(extracted_text)} chars)")
            
            # Perform different types of analysis
            results = {
                'documentId': document_id,
                'analysisType': analysis_type,
                'textLength': len(extracted_text),
                'processingTime': 0.0
            }
            
            if analysis_type in ['full', 'basic']:
                # Basic text analysis
                results.update(self._analyze_basic_metrics(extracted_text))
                
                # AI-powered analysis
                ai_results = self._analyze_with_gemini(extracted_text, document_data)
                results.update(ai_results)
            
            if analysis_type == 'full':
                # Advanced analysis
                if NLTK_AVAILABLE:
                    results.update(self._analyze_sentiment(extracted_text))
                    results.update(self._analyze_readability(extracted_text))
                    results.update(self._extract_entities(extracted_text))
                
                # Legal-specific analysis
                results.update(self._analyze_legal_aspects(extracted_text))
            
            results['processingTime'] = time.time() - start_time
            results['confidence'] = self._calculate_confidence(results)
            
            logger.info(f"✅ Analysis completed in {results['processingTime']:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"❌ Analysis failed for document {document_id}: {e}")
            return {
                'documentId': document_id,
                'analysisType': analysis_type,
                'error': str(e),
                'processingTime': time.time() - start_time,
                'confidence': 0.0
            }

    def _get_document_data(self, document_id: str) -> Dict[str, Any]:
        """Get document metadata from Firestore"""
        try:
            doc_ref = self.firestore_client.collection('documents').document(document_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                raise Exception(f"Document {document_id} not found")
            
            return doc.to_dict()
            
        except Exception as e:
            logger.error(f"Error getting document data: {e}")
            raise

    def _get_extracted_text(self, document_id: str) -> str:
        """Get extracted text from Firestore"""
        try:
            query = self.firestore_client.collection('extracted_documents')\
                .where('documentId', '==', document_id)\
                .order_by('createdAt', direction='DESCENDING')\
                .limit(1)
            
            docs = query.get()
            
            if not docs:
                raise Exception(f"No extracted text found for document {document_id}")
            
            extracted_doc = docs[0].to_dict()
            return extracted_doc.get('text', '')
            
        except Exception as e:
            logger.error(f"Error getting extracted text: {e}")
            raise

    def _analyze_basic_metrics(self, text: str) -> Dict[str, Any]:
        """Analyze basic text metrics"""
        try:
            words = text.split()
            sentences = text.split('.')
            paragraphs = text.split('\n\n')
            
            # Remove empty elements
            words = [w for w in words if w.strip()]
            sentences = [s for s in sentences if s.strip()]
            paragraphs = [p for p in paragraphs if p.strip()]
            
            return {
                'wordCount': len(words),
                'sentenceCount': len(sentences),
                'paragraphCount': len(paragraphs),
                'averageWordsPerSentence': len(words) / max(len(sentences), 1),
                'averageSentencesPerParagraph': len(sentences) / max(len(paragraphs), 1)
            }
            
        except Exception as e:
            logger.error(f"Basic metrics analysis error: {e}")
            return {}

    def _analyze_with_gemini(self, text: str, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze document using Gemini AI"""
        try:
            filename = document_data.get('filename', 'Unknown')
            content_type = document_data.get('contentType', 'unknown')
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt(text, filename, content_type)
            
            # Get AI analysis
            ai_response = self.gemini_client.analyze_document(prompt)
            
            if not ai_response:
                return {'summary': 'Analysis unavailable', 'keyPoints': [], 'legalRelevance': ''}
            
            return self._parse_ai_response(ai_response)
            
        except Exception as e:
            logger.error(f"Gemini analysis error: {e}")
            return {
                'summary': 'AI analysis failed',
                'keyPoints': [],
                'legalRelevance': 'Unable to determine legal relevance',
                'aiError': str(e)
            }

    def _create_analysis_prompt(self, text: str, filename: str, content_type: str) -> str:
        """Create a comprehensive analysis prompt for Gemini"""
        # Truncate text if too long
        max_text_length = 8000
        if len(text) > max_text_length:
            text = text[:max_text_length] + "... [truncated]"
        
        prompt = f"""
        Please analyze the following legal document and provide a comprehensive analysis:

        Document Information:
        - Filename: {filename}
        - Type: {content_type}
        - Length: {len(text)} characters

        Document Content:
        {text}

        Please provide your analysis in the following JSON format:
        {{
            "summary": "A concise 2-3 sentence summary of the document",
            "keyPoints": ["List of 3-7 key points or main ideas"],
            "legalRelevance": "Assessment of legal significance and implications",
            "documentType": "Classification of document type (contract, legal brief, etc.)",
            "parties": ["List of parties mentioned in the document"],
            "dates": ["Important dates mentioned"],
            "obligations": ["Key obligations or requirements identified"],
            "risks": ["Potential legal risks or issues"],
            "recommendations": ["2-4 actionable recommendations"]
        }}

        Focus on legal implications, key clauses, obligations, and potential issues.
        """
        
        return prompt

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate AI response"""
        try:
            # Try to extract JSON from response
            import json
            
            # Look for JSON in the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                
                # Validate required fields
                result = {
                    'summary': parsed.get('summary', 'No summary provided'),
                    'keyPoints': parsed.get('keyPoints', []),
                    'legalRelevance': parsed.get('legalRelevance', 'Legal relevance not determined'),
                    'documentType': parsed.get('documentType', 'Unknown'),
                    'parties': parsed.get('parties', []),
                    'dates': parsed.get('dates', []),
                    'obligations': parsed.get('obligations', []),
                    'risks': parsed.get('risks', []),
                    'recommendations': parsed.get('recommendations', [])
                }
                
                return result
            else:
                # If no JSON, parse as text
                return self._parse_text_response(response)
                
        except Exception as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            return self._parse_text_response(response)

    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """Parse AI response as plain text"""
        lines = response.split('\n')
        
        result = {
            'summary': 'AI analysis completed',
            'keyPoints': [],
            'legalRelevance': 'See full analysis',
            'fullAnalysis': response
        }
        
        # Try to extract key points
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if 'key point' in line.lower() or line.startswith('•') or line.startswith('-'):
                point = re.sub(r'^[•\-\*]\s*', '', line)
                if point:
                    result['keyPoints'].append(point)
        
        # Extract summary from first few sentences
        sentences = response.split('.')[:3]
        if sentences:
            result['summary'] = '. '.join(sentences).strip() + '.'
        
        return result

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze document sentiment"""
        if not NLTK_AVAILABLE or not self.sentiment_analyzer:
            return {'sentiment': {'score': 0, 'label': 'neutral'}}
        
        try:
            scores = self.sentiment_analyzer.polarity_scores(text)
            
            # Determine overall sentiment
            if scores['compound'] >= 0.05:
                label = 'positive'
            elif scores['compound'] <= -0.05:
                label = 'negative'
            else:
                label = 'neutral'
            
            return {
                'sentiment': {
                    'score': scores['compound'],
                    'label': label,
                    'positive': scores['pos'],
                    'negative': scores['neg'],
                    'neutral': scores['neu']
                }
            }
            
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {'sentiment': {'score': 0, 'label': 'neutral', 'error': str(e)}}

    def _analyze_readability(self, text: str) -> Dict[str, Any]:
        """Analyze document readability"""
        try:
            flesch_score = textstat.flesch_reading_ease(text)
            flesch_grade = textstat.flesch_kincaid_grade(text)
            
            # Determine readability level
            if flesch_score >= 90:
                level = 'Very Easy'
            elif flesch_score >= 80:
                level = 'Easy'
            elif flesch_score >= 70:
                level = 'Fairly Easy'
            elif flesch_score >= 60:
                level = 'Standard'
            elif flesch_score >= 50:
                level = 'Fairly Difficult'
            elif flesch_score >= 30:
                level = 'Difficult'
            else:
                level = 'Very Difficult'
            
            return {
                'readability': {
                    'fleschScore': flesch_score,
                    'fleschGrade': flesch_grade,
                    'level': level,
                    'averageGradeLevel': textstat.text_standard(text, float_output=False)
                }
            }
            
        except Exception as e:
            logger.error(f"Readability analysis error: {e}")
            return {'readability': {'error': str(e)}}

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract named entities from text"""
        try:
            entities = {
                'people': [],
                'organizations': [],
                'locations': [],
                'dates': [],
                'amounts': []
            }
            
            # Simple regex-based entity extraction
            # Names (simple pattern)
            name_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'
            potential_names = re.findall(name_pattern, text)
            entities['people'] = list(set(potential_names))[:10]  # Limit to 10
            
            # Dates
            date_patterns = [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
                r'\b[A-Za-z]+ \d{1,2}, \d{4}\b',
                r'\b\d{1,2} [A-Za-z]+ \d{4}\b'
            ]
            for pattern in date_patterns:
                dates = re.findall(pattern, text)
                entities['dates'].extend(dates)
            
            entities['dates'] = list(set(entities['dates']))[:10]
            
            # Amounts (money)
            amount_pattern = r'\$[\d,]+\.?\d*'
            amounts = re.findall(amount_pattern, text)
            entities['amounts'] = list(set(amounts))[:10]
            
            return {'entities': entities}
            
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return {'entities': {}}

    def _analyze_legal_aspects(self, text: str) -> Dict[str, Any]:
        """Analyze legal-specific aspects of the document"""
        try:
            legal_analysis = {
                'legalTerms': [],
                'contractClauses': [],
                'obligations': [],
                'deadlines': [],
                'penalties': []
            }
            
            # Common legal terms
            legal_terms = [
                'whereas', 'therefore', 'pursuant to', 'notwithstanding',
                'liability', 'indemnify', 'breach', 'default', 'terminate',
                'covenant', 'warranty', 'representation', 'consideration',
                'jurisdiction', 'governing law', 'force majeure'
            ]
            
            text_lower = text.lower()
            found_terms = [term for term in legal_terms if term in text_lower]
            legal_analysis['legalTerms'] = found_terms
            
            # Look for contract clauses
            clause_patterns = [
                r'section \d+',
                r'article \d+',
                r'paragraph \([a-z]\)',
                r'subsection \([0-9]\)'
            ]
            
            clauses = []
            for pattern in clause_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                clauses.extend(matches)
            
            legal_analysis['contractClauses'] = list(set(clauses))[:10]
            
            # Look for obligations (shall, must, required to)
            obligation_pattern = r'[^.]*(?:shall|must|required to|obligated to)[^.]*\.'
            obligations = re.findall(obligation_pattern, text, re.IGNORECASE)
            legal_analysis['obligations'] = [obs.strip() for obs in obligations[:5]]
            
            # Look for deadlines
            deadline_pattern = r'[^.]*(?:within|by|no later than|deadline)[^.]*\.'
            deadlines = re.findall(deadline_pattern, text, re.IGNORECASE)
            legal_analysis['deadlines'] = [dl.strip() for dl in deadlines[:5]]
            
            return {'legalAnalysis': legal_analysis}
            
        except Exception as e:
            logger.error(f"Legal analysis error: {e}")
            return {'legalAnalysis': {}}

    def _calculate_confidence(self, results: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the analysis"""
        try:
            confidence = 0.5  # Base confidence
            
            # Increase confidence based on available data
            if results.get('summary'):
                confidence += 0.2
            
            if results.get('keyPoints') and len(results['keyPoints']) > 0:
                confidence += 0.1
            
            if results.get('legalRelevance'):
                confidence += 0.1
            
            if results.get('sentiment'):
                confidence += 0.05
            
            if results.get('entities'):
                confidence += 0.05
            
            # Adjust based on text length
            text_length = results.get('textLength', 0)
            if text_length > 1000:
                confidence += 0.1
            elif text_length < 100:
                confidence -= 0.2
            
            return min(1.0, max(0.0, confidence))
            
        except Exception:
            return 0.5