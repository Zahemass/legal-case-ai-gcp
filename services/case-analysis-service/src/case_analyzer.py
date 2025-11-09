#services/case-analysis-service/src/case_analyzer.py
import logging
import os
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from gemini_client import GeminiClient
from dotenv import load_dotenv  # ✅ NEW

# ✅ Load environment variables from .env (even in local dev)
env_path = os.path.join(os.path.dirname(__file__), "../.env")
print(f"🔍 Loading .env from: {os.path.abspath(env_path)}")
load_dotenv(dotenv_path=env_path)
logger = logging.getLogger(__name__)

class CaseAnalyzer:
    """Comprehensive case analysis service using AI and data analytics"""
    
    def __init__(self, gemini_client: GeminiClient, firestore_client):
        self.gemini_client = gemini_client
        self.firestore_client = firestore_client
        logger.info("✅ CaseAnalyzer initialized")

    def analyze_case(self, case_id: str, analysis_type: str = 'comprehensive') -> Dict[str, Any]:
        """Perform comprehensive case analysis"""
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Starting {analysis_type} analysis for case {case_id}")
            
            # Get case data and documents
            case_data = self._get_case_data(case_id)
            documents_data = self._get_case_documents(case_id)
            extracted_texts = self._get_extracted_texts(case_id)
            
            if not case_data:
                raise Exception(f"Case {case_id} not found")
            
            logger.info(f"📊 Analyzing case with {len(documents_data)} documents")
            
            # Initialize results
            results = {
                'caseId': case_id,
                'analysisType': analysis_type,
                'analyzedAt': datetime.utcnow().isoformat(),
                'documentCount': len(documents_data),
                'totalTextLength': sum(len(text) for text in extracted_texts.values()),
                'processingTime': 0.0
            }
            
            # Perform different levels of analysis
            if analysis_type in ['comprehensive', 'full']:
                results.update(self._comprehensive_analysis(case_data, documents_data, extracted_texts))
            elif analysis_type == 'quick':
                results.update(self._quick_analysis(case_data, documents_data, extracted_texts))
            elif analysis_type == 'summary':
                results.update(self._summary_analysis(case_data, documents_data, extracted_texts))
            
            # Calculate confidence and processing time
            results['processingTime'] = time.time() - start_time
            results['confidence'] = self._calculate_confidence(results)
            
            logger.info(f"✅ Case analysis completed in {results['processingTime']:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"❌ Case analysis failed for {case_id}: {e}")
            return {
                'caseId': case_id,
                'analysisType': analysis_type,
                'error': str(e),
                'processingTime': time.time() - start_time,
                'confidence': 0.0
            }

    def _get_case_data(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get case data from Firestore"""
        try:
            case_ref = self.firestore_client.collection('cases').document(case_id)
            case_doc = case_ref.get()
            
            if not case_doc.exists:
                return None
            
            return case_doc.to_dict()
            
        except Exception as e:
            logger.error(f"Error getting case data: {e}")
            return None

    def _get_case_documents(self, case_id: str) -> List[Dict[str, Any]]:
        """Get all non-deleted documents for a specific case from Firestore."""
        try:
            logger.info(f"📄 Fetching documents for case ID: {case_id}")

            # Firestore doesn't reliably support '!=' queries, so we filter manually
            docs_query = self.firestore_client.collection("documents").where("caseId", "==", case_id)
            documents = []

            for doc in docs_query.get():
                doc_data = doc.to_dict()
                if not doc_data:
                    continue

                # Skip logically deleted documents
                if doc_data.get("status") == "deleted":
                    continue

                # Add Firestore document ID
                doc_data["id"] = doc.id
                documents.append(doc_data)

            logger.info(f"✅ Retrieved {len(documents)} active documents for case {case_id}")
            return documents

        except Exception as e:
            logger.error(f"❌ Failed to get case documents for {case_id}: {e}", exc_info=True)
            # Re-raise the exception instead of swallowing it
            raise RuntimeError(f"Error retrieving documents for case {case_id}: {e}") from e


    def _get_extracted_texts(self, case_id: str) -> Dict[str, str]:
        """Get extracted texts for all case documents"""
        try:
            # Get extracted documents for this case
            extracted_query = self.firestore_client.collection('extracted_documents')\
                .where('caseId', '==', case_id)
            
            extracted_texts = {}
            for doc in extracted_query.get():
                doc_data = doc.to_dict()
                document_id = doc_data.get('documentId')
                text = doc_data.get('text', '')
                
                if document_id and text:
                    extracted_texts[document_id] = text
            
            return extracted_texts
            
        except Exception as e:
            logger.error(f"Error getting extracted texts: {e}")
            return {}

    def _comprehensive_analysis(self, case_data: Dict, documents_data: List, extracted_texts: Dict) -> Dict[str, Any]:
        """Perform comprehensive case analysis"""
        try:
            results = {}
            
            # 1. Executive Summary
            results['executiveSummary'] = self._generate_executive_summary(case_data, documents_data, extracted_texts)
            
            # 2. Key Findings
            results['keyFindings'] = self._extract_key_findings(extracted_texts)
            
            # 3. Strengths and Weaknesses Analysis
            results['strengthsWeaknesses'] = self._analyze_strengths_weaknesses(extracted_texts)
            
            # 4. Legal Issues Identification
            results['legalIssues'] = self._identify_legal_issues(extracted_texts)
            
            # 5. Document Analysis Summary
            results['documentAnalysis'] = self._analyze_documents_summary(documents_data, extracted_texts)
            
            # 6. Timeline Analysis
            results['timeline'] = self._extract_timeline(extracted_texts, case_data)
            
            # 7. Risk Assessment
            results['riskAssessment'] = self._assess_risks(extracted_texts, case_data)
            
            # 8. Strategic Recommendations
            results['recommendations'] = self._generate_recommendations(case_data, extracted_texts)
            
            # 9. Strategic Advice
            results['strategicAdvice'] = self._generate_strategic_advice(case_data, extracted_texts)
            
            return results
            
        except Exception as e:
            logger.error(f"Comprehensive analysis error: {e}")
            return {'error': str(e)}

    def _quick_analysis(self, case_data: Dict, documents_data: List, extracted_texts: Dict) -> Dict[str, Any]:
        """Perform quick case analysis"""
        try:
            # Combine all texts for analysis
            combined_text = self._combine_texts(extracted_texts)
            
            results = {
                'executiveSummary': self._generate_quick_summary(case_data, combined_text),
                'keyFindings': self._extract_key_points(combined_text)[:5],  # Top 5 only
                'documentCount': len(documents_data),
                'totalWordCount': len(combined_text.split()) if combined_text else 0
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Quick analysis error: {e}")
            return {'error': str(e)}

    def _summary_analysis(self, case_data: Dict, documents_data: List, extracted_texts: Dict) -> Dict[str, Any]:
        """Perform summary-only case analysis"""
        try:
            combined_text = self._combine_texts(extracted_texts)
            
            results = {
                'executiveSummary': self._generate_executive_summary(case_data, documents_data, extracted_texts),
                'documentSummary': f"Case contains {len(documents_data)} documents with {len(combined_text.split()) if combined_text else 0} total words.",
                'basicStats': {
                    'documentCount': len(documents_data),
                    'totalTextLength': len(combined_text) if combined_text else 0,
                    'averageDocumentSize': sum(len(text) for text in extracted_texts.values()) / max(len(extracted_texts), 1)
                }
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Summary analysis error: {e}")
            return {'error': str(e)}

    def _generate_executive_summary(self, case_data: Dict, documents_data: List, extracted_texts: Dict) -> str:
        """Generate executive summary using AI"""
        try:
            case_title = case_data.get('title', 'Unknown Case')
            case_type = case_data.get('type', 'general')
            case_description = case_data.get('description', '')
            
            # Combine key excerpts from documents
            combined_text = self._combine_texts(extracted_texts, max_length=6000)
            
            prompt = f"""
            Please provide an executive summary for this legal case:

            Case Information:
            - Title: {case_title}
            - Type: {case_type}
            - Description: {case_description}
            - Number of Documents: {len(documents_data)}

            Key Document Content:
            {combined_text}

            Please provide a comprehensive executive summary (3-4 paragraphs) that includes:
            1. Case overview and background
            2. Key issues and matters involved
            3. Current status and important findings
            4. Overall assessment and implications

            Keep it professional and suitable for legal professionals.
            """
            
            summary = self.gemini_client.analyze_document(prompt)
            return summary if summary else "Executive summary could not be generated due to AI service limitations."
            
        except Exception as e:
            logger.error(f"Executive summary generation error: {e}")
            return f"Executive summary generation failed: {str(e)}"

    def _extract_key_findings(self, extracted_texts: Dict) -> List[str]:
        """Extract key findings from case documents"""
        try:
            combined_text = self._combine_texts(extracted_texts, max_length=8000)
            
            prompt = f"""
            Based on the following legal case documents, please identify the top 7-10 key findings.
            Focus on factual findings, important discoveries, critical evidence, and significant legal points.

            Documents:
            {combined_text}

            Please list the key findings as numbered points, focusing on:
            - Important facts established
            - Critical evidence discovered
            - Significant legal precedents or issues
            - Key witness testimonies or statements
            - Important dates, agreements, or events
            - Financial or damages information
            - Regulatory or compliance findings

            Format as a numbered list with concise, professional language.
            """
            
            response = self.gemini_client.analyze_document(prompt)
            
            if response:
                # Parse the response into a list
                findings = []
                lines = response.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                        finding = line.split('.', 1)[-1].strip() if '.' in line else line[1:].strip()
                        if finding:
                            findings.append(finding)
                
                return findings[:10]  # Limit to 10
            
            return []
            
        except Exception as e:
            logger.error(f"Key findings extraction error: {e}")
            return []

    def _analyze_strengths_weaknesses(self, extracted_texts: Dict) -> Dict[str, List[str]]:
        """Analyze case strengths and weaknesses"""
        try:
            combined_text = self._combine_texts(extracted_texts, max_length=8000)
            
            prompt = f"""
            As a legal expert, please analyze the strengths and weaknesses of this case based on the documents provided.

            Case Documents:
            {combined_text}

            Please provide:
            1. STRENGTHS: 4-6 key strengths or advantages in this case
            2. WEAKNESSES: 4-6 key weaknesses, vulnerabilities, or challenges

            Focus on:
            - Evidence quality and availability
            - Legal precedents and case law support
            - Witness credibility and testimony
            - Documentation completeness
            - Procedural advantages/disadvantages
            - Financial considerations
            - Timeline and statute of limitations issues

            Format your response as:
            STRENGTHS:
            1. [strength]
            2. [strength]
            ...

            WEAKNESSES:
            1. [weakness]
            2. [weakness]
            ...
            """
            
            response = self.gemini_client.analyze_document(prompt)
            
            if response:
                strengths = []
                weaknesses = []
                current_section = None
                
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    
                    if 'STRENGTHS' in line.upper():
                        current_section = 'strengths'
                        continue
                    elif 'WEAKNESSES' in line.upper():
                        current_section = 'weaknesses'
                        continue
                    
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                        item = line.split('.', 1)[-1].strip() if '.' in line else line[1:].strip()
                        if item:
                            if current_section == 'strengths':
                                strengths.append(item)
                            elif current_section == 'weaknesses':
                                weaknesses.append(item)
                
                return {
                    'strengths': strengths[:6],
                    'weaknesses': weaknesses[:6]
                }
            
            return {'strengths': [], 'weaknesses': []}
            
        except Exception as e:
            logger.error(f"Strengths/weaknesses analysis error: {e}")
            return {'strengths': [], 'weaknesses': []}

    def _identify_legal_issues(self, extracted_texts: Dict) -> List[Dict[str, Any]]:
        """Identify legal issues in the case"""
        try:
            combined_text = self._combine_texts(extracted_texts, max_length=8000)
            
            prompt = f"""
            Please identify the key legal issues present in this case based on the documents provided.

            Case Documents:
            {combined_text}

            For each legal issue identified, please provide:
            1. Issue name/title
            2. Brief description
            3. Severity level (High/Medium/Low)
            4. Key implications

            Focus on:
            - Contract disputes
            - Liability issues
            - Regulatory compliance
            - Intellectual property matters
            - Employment law issues
            - Constitutional questions
            - Procedural issues
            - Jurisdictional concerns

            Format as:
            ISSUE 1: [Title]
            Description: [Description]
            Severity: [High/Medium/Low]
            Implications: [Key implications]

            ISSUE 2: [Title]
            ...
            """
            
            response = self.gemini_client.analyze_document(prompt)
            
            if response:
                issues = []
                current_issue = {}
                
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    
                    if line.startswith('ISSUE '):
                        if current_issue:
                            issues.append(current_issue)
                        
                        title = line.split(':', 1)[-1].strip() if ':' in line else line
                        current_issue = {'title': title}
                    
                    elif line.startswith('Description:'):
                        current_issue['description'] = line.split(':', 1)[-1].strip()
                    
                    elif line.startswith('Severity:'):
                        severity = line.split(':', 1)[-1].strip()
                        current_issue['severity'] = severity.lower()
                    
                    elif line.startswith('Implications:'):
                        current_issue['implications'] = line.split(':', 1)[-1].strip()
                
                if current_issue:
                    issues.append(current_issue)
                
                return issues[:8]  # Limit to 8 issues
            
            return []
            
        except Exception as e:
            logger.error(f"Legal issues identification error: {e}")
            return []

    def _analyze_documents_summary(self, documents_data: List, extracted_texts: Dict) -> Dict[str, Any]:
        """Create summary of document analysis"""
        try:
            total_docs = len(documents_data)
            total_text_length = sum(len(text) for text in extracted_texts.values())
            
            # Document type breakdown
            doc_types = {}
            for doc in documents_data:
                content_type = doc.get('contentType', 'unknown')
                category = content_type.split('/')[0] if '/' in content_type else content_type
                doc_types[category] = doc_types.get(category, 0) + 1
            
            # Document size analysis
            doc_sizes = [len(text) for text in extracted_texts.values()]
            
            analysis = {
                'totalDocuments': total_docs,
                'documentsWithText': len(extracted_texts),
                'totalTextLength': total_text_length,
                'averageDocumentSize': total_text_length / max(len(extracted_texts), 1),
                'documentTypes': doc_types,
                'sizeStatistics': {
                    'largest': max(doc_sizes) if doc_sizes else 0,
                    'smallest': min(doc_sizes) if doc_sizes else 0,
                    'median': sorted(doc_sizes)[len(doc_sizes)//2] if doc_sizes else 0
                }
            }
            
            # Most relevant documents (by size and content)
            relevant_docs = []
            for doc in documents_data:
                doc_id = doc.get('id')
                if doc_id in extracted_texts:
                    text_length = len(extracted_texts[doc_id])
                    relevant_docs.append({
                        'filename': doc.get('filename', 'Unknown'),
                        'textLength': text_length,
                        'uploadedAt': doc.get('uploadedAt'),
                        'relevanceScore': min(1.0, text_length / 10000)  # Simple relevance scoring
                    })
            
            # Sort by relevance and take top 5
            relevant_docs.sort(key=lambda x: x['relevanceScore'], reverse=True)
            analysis['topDocuments'] = relevant_docs[:5]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Document analysis summary error: {e}")
            return {}

    def _extract_timeline(self, extracted_texts: Dict, case_data: Dict) -> List[Dict[str, Any]]:
        """Extract timeline events from case documents"""
        try:
            combined_text = self._combine_texts(extracted_texts, max_length=8000)
            
            prompt = f"""
            Please extract a chronological timeline of important events from this legal case.

            Case Information:
            - Title: {case_data.get('title', 'Unknown')}
            - Created: {case_data.get('createdAt', 'Unknown')}

            Documents:
            {combined_text}

            Please identify key dates and events, focusing on:
            - Contract signing dates
            - Important meetings or communications
            - Deadline dates
            - Filing dates
            - Incident dates
            - Settlement discussions
            - Court proceedings

            Format as:
            DATE: [Date]
            EVENT: [Description of event]
            SIGNIFICANCE: [Why this event is important]

            ORDER BY: Chronological order (earliest first)
            LIMIT: Top 10 most significant events
            """
            
            response = self.gemini_client.analyze_document(prompt)
            
            if response:
                timeline_events = []
                current_event = {}
                
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    
                    if line.startswith('DATE:'):
                        if current_event:
                            timeline_events.append(current_event)
                        
                        date = line.split(':', 1)[-1].strip()
                        current_event = {'date': date}
                    
                    elif line.startswith('EVENT:'):
                        current_event['event'] = line.split(':', 1)[-1].strip()
                    
                    elif line.startswith('SIGNIFICANCE:'):
                        current_event['significance'] = line.split(':', 1)[-1].strip()
                
                if current_event:
                    timeline_events.append(current_event)
                
                return timeline_events[:10]
            
            return []
            
        except Exception as e:
            logger.error(f"Timeline extraction error: {e}")
            return []

    def _assess_risks(self, extracted_texts: Dict, case_data: Dict) -> Dict[str, Any]:
        """Assess risks associated with the case"""
        try:
            combined_text = self._combine_texts(extracted_texts, max_length=8000)
            
            prompt = f"""
            Please assess the legal and business risks associated with this case.

            Case Type: {case_data.get('type', 'general')}
            Case Documents:
            {combined_text}

            Please provide a risk assessment including:

            1. FINANCIAL RISKS (potential costs, damages, penalties)
            2. LEGAL RISKS (adverse judgments, precedents, sanctions)
            3. OPERATIONAL RISKS (business disruption, compliance issues)
            4. REPUTATIONAL RISKS (public relations, brand impact)

            For each risk category, provide:
            - Risk level (High/Medium/Low)
            - Key risk factors
            - Potential impact
            - Mitigation suggestions

            Format as structured analysis with clear categories.
            """
            
            response = self.gemini_client.analyze_document(prompt)
            
            if response:
                # Parse the structured response
                risk_assessment = {
                    'overallRiskLevel': 'Medium',  # Default
                    'riskCategories': {
                        'financial': {'level': 'Medium', 'factors': [], 'impact': '', 'mitigation': ''},
                        'legal': {'level': 'Medium', 'factors': [], 'impact': '', 'mitigation': ''},
                        'operational': {'level': 'Low', 'factors': [], 'impact': '', 'mitigation': ''},
                        'reputational': {'level': 'Low', 'factors': [], 'impact': '', 'mitigation': ''}
                    },
                    'keyRiskFactors': [],
                    'mitigationStrategies': [],
                    'fullAssessment': response
                }
                
                # Extract key risk factors from response
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and ('risk' in line.lower() or 'factor' in line.lower()):
                        if len(line) < 200:  # Reasonable length for a risk factor
                            risk_assessment['keyRiskFactors'].append(line)
                
                risk_assessment['keyRiskFactors'] = risk_assessment['keyRiskFactors'][:8]
                
                return risk_assessment
            
            return {'overallRiskLevel': 'Unknown', 'riskCategories': {}}
            
        except Exception as e:
            logger.error(f"Risk assessment error: {e}")
            return {'error': str(e)}

    def _generate_recommendations(self, case_data: Dict, extracted_texts: Dict) -> List[Dict[str, Any]]:
        """Generate strategic recommendations"""
        try:
            combined_text = self._combine_texts(extracted_texts, max_length=8000)
            
            prompt = f"""
            Based on this legal case analysis, please provide strategic recommendations for the legal team.

            Case Information:
            - Title: {case_data.get('title', 'Unknown')}
            - Type: {case_data.get('type', 'general')}
            - Priority: {case_data.get('priority', 'medium')}

            Case Content:
            {combined_text}

            Please provide 5-8 actionable recommendations covering:
            1. Immediate action items
            2. Evidence gathering priorities
            3. Legal strategy considerations
            4. Risk mitigation steps
            5. Settlement considerations (if applicable)
            6. Procedural recommendations
            7. Resource allocation suggestions

            For each recommendation, provide:
            - Action: What needs to be done
            - Priority: High/Medium/Low
            - Timeline: When it should be completed
            - Rationale: Why this is important

            Format as structured recommendations.
            """
            
            response = self.gemini_client.analyze_document(prompt)
            
            if response:
                recommendations = []
                current_rec = {}
                
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    
                    if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.')) or line.startswith('RECOMMENDATION'):
                        if current_rec:
                            recommendations.append(current_rec)
                        
                        action = line.split(':', 1)[-1].strip() if ':' in line else line
                        current_rec = {'action': action, 'priority': 'Medium', 'timeline': 'TBD', 'rationale': ''}
                    
                    elif line.startswith('Action:'):
                        current_rec['action'] = line.split(':', 1)[-1].strip()
                    elif line.startswith('Priority:'):
                        current_rec['priority'] = line.split(':', 1)[-1].strip()
                    elif line.startswith('Timeline:'):
                        current_rec['timeline'] = line.split(':', 1)[-1].strip()
                    elif line.startswith('Rationale:'):
                        current_rec['rationale'] = line.split(':', 1)[-1].strip()
                
                if current_rec:
                    recommendations.append(current_rec)
                
                return recommendations[:8]
            
            return []
            
        except Exception as e:
            logger.error(f"Recommendations generation error: {e}")
            return []

    def _generate_strategic_advice(self, case_data: Dict, extracted_texts: Dict) -> str:
        """Generate high-level strategic advice"""
        try:
            combined_text = self._combine_texts(extracted_texts, max_length=6000)
            
            prompt = f"""
            As a senior legal strategist, please provide high-level strategic advice for this case.

            Case Overview:
            - Title: {case_data.get('title', 'Unknown')}
            - Type: {case_data.get('type', 'general')}
            - Priority: {case_data.get('priority', 'medium')}

            Case Analysis:
            {combined_text}

            Please provide strategic advice covering:
            1. Overall case strategy and approach
            2. Key success factors and objectives
            3. Potential settlement vs. litigation strategy
            4. Resource allocation and team structure recommendations
            5. Timeline and milestone planning
            6. Communication and stakeholder management

            Provide 2-3 paragraphs of comprehensive strategic guidance suitable for senior legal professionals.
            """
            
            advice = self.gemini_client.analyze_document(prompt)
            return advice if advice else "Strategic advice could not be generated due to AI service limitations."
            
        except Exception as e:
            logger.error(f"Strategic advice generation error: {e}")
            return f"Strategic advice generation failed: {str(e)}"

    def _combine_texts(self, extracted_texts: Dict, max_length: int = 10000) -> str:
        """Combine extracted texts with length limit"""
        combined = ""
        current_length = 0
        
        for doc_id, text in extracted_texts.items():
            if current_length + len(text) <= max_length:
                combined += f"\n--- Document {doc_id} ---\n{text}\n"
                current_length += len(text)
            else:
                # Add partial text to reach max_length
                remaining = max_length - current_length
                if remaining > 100:
                    combined += f"\n--- Document {doc_id} (partial) ---\n{text[:remaining]}...\n"
                break
        
        return combined.strip()

    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from combined text"""
        try:
            points = self.gemini_client.extract_key_points(text, max_points=10)
            return points if points else []
        except Exception as e:
            logger.error(f"Key points extraction error: {e}")
            return []

    def _generate_quick_summary(self, case_data: Dict, combined_text: str) -> str:
        """Generate quick summary"""
        try:
            case_title = case_data.get('title', 'Unknown Case')
            summary = self.gemini_client.summarize_text(combined_text, max_length=800)
            
            if summary:
                return f"Case: {case_title}\n\nSummary: {summary}"
            else:
                return f"Case: {case_title}\n\nQuick summary could not be generated."
                
        except Exception as e:
            logger.error(f"Quick summary generation error: {e}")
            return f"Quick summary generation failed: {str(e)}"

    def _calculate_confidence(self, results: Dict[str, Any]) -> float:
        """Calculate overall confidence score"""
        try:
            confidence = 0.3  # Base confidence
            
            # Increase confidence based on available analysis
            if results.get('executiveSummary'):
                confidence += 0.2
            
            if results.get('keyFindings') and len(results['keyFindings']) > 0:
                confidence += 0.1
            
            if results.get('strengthsWeaknesses'):
                confidence += 0.1
            
            if results.get('legalIssues') and len(results['legalIssues']) > 0:
                confidence += 0.1
            
            if results.get('recommendations') and len(results['recommendations']) > 0:
                confidence += 0.1
            
            if results.get('riskAssessment'):
                confidence += 0.1
            
            # Adjust based on document count and text length
            doc_count = results.get('documentCount', 0)
            text_length = results.get('totalTextLength', 0)
            
            if doc_count >= 5:
                confidence += 0.05
            if text_length > 10000:
                confidence += 0.05
            
            return min(1.0, max(0.0, confidence))
            
        except Exception:
            return 0.5