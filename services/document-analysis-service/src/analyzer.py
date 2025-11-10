# services/document-analysis-service/src/analyzer.py
import logging
import time
import re
from typing import Dict, Any, List, Optional
import nltk
import textstat
from typer import prompt
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

            # Step 1: Create analysis prompt
            prompt = self._create_analysis_prompt(text, filename, content_type)

            # Step 2: Get AI analysis response
            ai_response = self.gemini_client.analyze_document(prompt)

            if not ai_response:
                return {'summary': 'Analysis unavailable', 'keyPoints': [], 'legalRelevance': ''}

            # Step 3: Parse main AI analysis
            results = self._parse_ai_response(ai_response)

            # Step 4: Get structured legal relevance / analysis
            legal_relevance = self.gemini_client.assess_legal_relevance(text, filename)
            if legal_relevance:
                results['legalRelevance'] = legal_relevance.get("summary", "")
                results['legalAnalysis'] = legal_relevance
            else:
                results['legalRelevance'] = "No detailed legal analysis available."
                results['legalAnalysis'] = {}

            return results

        except Exception as e:
            logger.error(f"Gemini analysis error: {e}")
            return {
                'summary': 'AI analysis failed',
                'keyPoints': [],
                'legalRelevance': 'Unable to determine legal relevance',
                'aiError': str(e)
            }


    def _create_analysis_prompt(self, text: str, filename: str, content_type: str) -> str:
            """Create a detailed legal analysis prompt for Gemini."""
            max_text_length = 12000
            if len(text) > max_text_length:
             text = text[:max_text_length]

            prompt = f"""
You are a **Legal Document Analysis AI**. 
Read the following document and return a **structured JSON response only** — no markdown, explanations, or commentary.

The JSON must follow this schema exactly:

{{
  "summary": "Concise 2-3 sentence legal summary.",
  "keyPoints": ["Key point 1", "Key point 2", ...],
  "legalRelevance": "2-3 sentences on legal importance or implications.",
  "entities": {{
    "people": ["List of individuals involved (e.g., plaintiffs, defendants, judges)"],
    "organizations": ["Courts, firms, companies, agencies"],
    "locations": ["Cities, addresses, places"],
    "dates": ["Dates of events or filings"],
    "amounts": ["Monetary or quantitative amounts"]
  }},
  "risks": ["Contradictions, missing details, compliance risks"],
  "recommendations": ["Practical next steps or legal advice"],
  "credibility": 0-100
}}

Guidelines:
- Focus on factual details from the text.
- Ensure **people** are *real persons or named individuals*, not labels like "The Defense" or "Case Closed".
- If unsure about an entity type, omit it.
- Keep names and legal sections exactly as written.
- Return only **valid JSON** (no extra commentary).

Document name: {filename}
Content type: {content_type}

Document content:
---
{text}
---
Return only the JSON object.
"""
            return prompt
    def _create_legal_relevance_prompt(self, text: str, filename: str) -> str:
     """
     Create a structured prompt for legal relevance & analysis.
     Produces reasoning aligned with case outcomes, risks, and recommendations.
     """
     max_text_length = 10000
     if len(text) > max_text_length:
         text = text[:max_text_length]

     prompt = f"""
You are a **legal reasoning AI assistant**. Analyze the following document and return a JSON response only (no markdown, no explanations).

The JSON must follow this schema:
{{
  "legalAnalysis": {{
    "summary": "Brief overview of the document’s legal context.",
    "issues": ["Key legal issues or disputes identified"],
    "arguments": {{
      "plaintiff": ["Main arguments made by the plaintiff or claimant"],
      "defendant": ["Main arguments made by the defendant or respondent"]
    }},
    "verdictOrOutcome": "Describe the judgment, verdict, or likely outcome if applicable.",
    "lawsOrSectionsCited": ["Relevant legal sections, acts, or precedents referenced"],
    "risks": ["Potential legal risks, contradictions, or weak arguments"],
    "recommendations": ["Actionable recommendations for legal teams or compliance officers"],
    "confidenceScore": 0-100
  }}
}}

Guidelines:
- Use precise legal language (avoid narrative tone).
- If certain fields aren’t available, return them as empty arrays.
- If it’s not a judgment or verdict, infer implications based on the facts.
- Extract only meaningful data — avoid placeholders like "N/A" or "none".
- Return only the JSON object.

Document name: {filename}

Document content:
---
{text}
---
Return only the JSON object.
"""
     return prompt


    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
     import json
     try:
         clean = response.strip()
         if clean.startswith("```"):
            clean = clean.strip("`").replace("json", "")
         clean = clean.strip()

         json_start = clean.find("{")
         json_end = clean.rfind("}") + 1
         parsed = json.loads(clean[json_start:json_end])

        # Normalize nested structure
         entities = parsed.get("entities", {})
         if isinstance(entities, list):
            entities = {"people": entities, "organizations": [], "locations": [], "dates": [], "amounts": []}
         else:
            for key in ["people", "organizations", "locations", "dates", "amounts"]:
                entities[key] = entities.get(key, [])

         result = {
            "summary": parsed.get("summary", "No summary available")[:400],
            "keyPoints": parsed.get("keyPoints", []),
            "legalRelevance": parsed.get("legalRelevance", ""),
            "entities": entities,
            "risks": parsed.get("risks", []),
            "recommendations": parsed.get("recommendations", []),
            "credibility": parsed.get("credibility", 60)
        }
         return result

     except json.JSONDecodeError as e:
        logger.warning(f"⚠️ Gemini returned malformed JSON: {e}")
        return {"summary": response[:200], "keyPoints": [], "entities": {}, "credibility": 0}
     except Exception as e:
        logger.error(f"Failed to parse Gemini response: {e}")
        return {"summary": "Parsing failed", "keyPoints": [], "entities": {}, "credibility": 0}

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