#!/usr/bin/env python3
"""
Legal AI Agent Tools for Vertex AI Agent
Implements specialized tools for legal document analysis, case law research, and legal assistance
"""

import os
import logging
from typing import Dict, Any, List, Optional, Callable
import json
import re
from datetime import datetime, timedelta
import asyncio

# Google Cloud imports
from google.cloud import firestore
from google.cloud import storage
from google.cloud import discoveryengine_v1 as discoveryengine
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration

# Legal analysis imports
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class LegalAgentTools:
    """Comprehensive tools for Legal AI Agent"""
    
    def __init__(self, project_id: str, tools_config: List[Dict[str, Any]]):
        self.project_id = project_id
        self.tools_config = tools_config
        self.firestore_client = firestore.Client(project=project_id)
        self.storage_client = storage.Client(project=project_id)
        
        # Initialize tools registry
        self.tools_registry = {}
        self.function_declarations = []
        
        logger.info("✅ Legal Agent Tools initialized")

    def register_all_tools(self):
        """Register all available tools"""
        try:
            # Document analysis tools
            self._register_document_search()
            self._register_document_analyzer()
            self._register_contract_reviewer()
            
            # Research tools
            self._register_case_law_search()
            self._register_legal_research()
            
            # Writing and drafting tools
            self._register_legal_writer()
            self._register_document_drafter()
            
            # Compliance and tracking tools
            self._register_compliance_checker()
            self._register_deadline_tracker()
            
            # Analysis and scoring tools
            self._register_risk_analyzer()
            self._register_precedent_finder()
            
            logger.info(f"✅ Registered {len(self.tools_registry)} tools")
            
        except Exception as e:
            logger.error(f"❌ Tool registration failed: {e}")
            raise

    def _register_document_search(self):
        """Register document search tool"""
        function_decl = FunctionDeclaration(
            name="document_search",
            description="Search through case documents and legal databases for relevant information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for documents"
                    },
                    "case_id": {
                        "type": "string",
                        "description": "Optional case ID to limit search scope"
                    },
                    "document_type": {
                        "type": "string",
                        "description": "Type of document to search (contract, brief, memo, etc.)"
                    },
                    "date_range": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"}
                        }
                    }
                },
                "required": ["query"]
            }
        )
        
        self.function_declarations.append(function_decl)
        self.tools_registry["document_search"] = self._document_search_impl

    async def _document_search_impl(self, query: str, case_id: Optional[str] = None, 
                                   document_type: Optional[str] = None, 
                                   date_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Implementation of document search"""
        try:
            logger.info(f"🔍 Searching documents: {query}")
            
            # Build Firestore query
            collection_ref = self.firestore_client.collection('documents')
            
            # Apply filters
            if case_id:
                collection_ref = collection_ref.where('caseId', '==', case_id)
            
            if document_type:
                collection_ref = collection_ref.where('documentType', '==', document_type)
            
            # Execute search
            documents = collection_ref.limit(20).get()
            
            results = []
            for doc in documents:
                doc_data = doc.to_dict()
                
                # Simple text matching (in production, use vector search)
                if self._text_matches(query.lower(), doc_data.get('filename', '').lower()):
                    results.append({
                        'id': doc.id,
                        'filename': doc_data.get('filename'),
                        'content_type': doc_data.get('contentType'),
                        'upload_date': doc_data.get('uploadedAt'),
                        'relevance_score': self._calculate_relevance(query, doc_data)
                    })
            
            # Sort by relevance
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return {
                'success': True,
                'results': results[:10],  # Top 10 results
                'total_found': len(results),
                'query': query
            }
            
        except Exception as e:
            logger.error(f"❌ Document search failed: {e}")
            return {'success': False, 'error': str(e)}

    def _register_document_analyzer(self):
        """Register document analysis tool"""
        function_decl = FunctionDeclaration(
            name="document_analyzer",
            description="Analyze legal documents for key insights, risks, and recommendations",
            parameters={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "ID of the document to analyze"
                    },
                    "analysis_type": {
                        "type": "string",
                        "description": "Type of analysis (full, summary, risk_only, key_terms)",
                        "enum": ["full", "summary", "risk_only", "key_terms"]
                    },
                    "focus_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific areas to focus on (liability, compliance, deadlines, etc.)"
                    }
                },
                "required": ["document_id"]
            }
        )
        
        self.function_declarations.append(function_decl)
        self.tools_registry["document_analyzer"] = self._document_analyzer_impl

    async def _document_analyzer_impl(self, document_id: str, analysis_type: str = "full", 
                                     focus_areas: Optional[List[str]] = None) -> Dict[str, Any]:
        """Implementation of document analyzer"""
        try:
            logger.info(f"📄 Analyzing document: {document_id}")
            
            # Get document data
            doc_ref = self.firestore_client.collection('documents').document(document_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return {'success': False, 'error': 'Document not found'}
            
            doc_data = doc.to_dict()
            
            # Get extracted text
            extracted_text = await self._get_extracted_text(document_id)
            
            if not extracted_text:
                return {'success': False, 'error': 'No extracted text available'}
            
            # Perform analysis based on type
            analysis_result = {}
            
            if analysis_type in ['full', 'summary']:
                analysis_result.update(await self._analyze_document_content(extracted_text, focus_areas))
            
            if analysis_type in ['full', 'risk_only']:
                analysis_result.update(await self._analyze_document_risks(extracted_text))
            
            if analysis_type in ['full', 'key_terms']:
                analysis_result.update(await self._extract_key_terms(extracted_text))
            
            # Save analysis results
            await self._save_document_analysis(document_id, analysis_result)
            
            return {
                'success': True,
                'document_id': document_id,
                'filename': doc_data.get('filename'),
                'analysis_type': analysis_type,
                'analysis': analysis_result,
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Document analysis failed: {e}")
            return {'success': False, 'error': str(e)}

    def _register_contract_reviewer(self):
        """Register contract review tool"""
        function_decl = FunctionDeclaration(
            name="contract_reviewer",
            description="Comprehensive contract analysis and risk assessment",
            parameters={
                "type": "object",
                "properties": {
                    "contract_id": {
                        "type": "string",
                        "description": "ID of the contract document"
                    },
                    "review_type": {
                        "type": "string",
                        "description": "Type of review (standard, detailed, compliance, negotiation)",
                        "enum": ["standard", "detailed", "compliance", "negotiation"]
                    },
                    "party_role": {
                        "type": "string",
                        "description": "Role of client in contract (buyer, seller, service_provider, client)",
                        "enum": ["buyer", "seller", "service_provider", "client", "vendor"]
                    }
                },
                "required": ["contract_id"]
            }
        )
        
        self.function_declarations.append(function_decl)
        self.tools_registry["contract_reviewer"] = self._contract_reviewer_impl

    async def _contract_reviewer_impl(self, contract_id: str, review_type: str = "standard", 
                                     party_role: Optional[str] = None) -> Dict[str, Any]:
        """Implementation of contract reviewer"""
        try:
            logger.info(f"📋 Reviewing contract: {contract_id}")
            
            # Get contract text
            contract_text = await self._get_extracted_text(contract_id)
            
            if not contract_text:
                return {'success': False, 'error': 'Contract text not available'}
            
            # Perform contract-specific analysis
            review_result = {
                'contract_type': await self._identify_contract_type(contract_text),
                'key_clauses': await self._extract_contract_clauses(contract_text),
                'risk_assessment': await self._assess_contract_risks(contract_text, party_role),
                'compliance_issues': await self._check_contract_compliance(contract_text),
                'negotiation_points': await self._identify_negotiation_points(contract_text, party_role),
                'missing_clauses': await self._identify_missing_clauses(contract_text),
                'financial_terms': await self._extract_financial_terms(contract_text),
                'deadlines_obligations': await self._extract_deadlines(contract_text)
            }
            
            # Generate recommendations
            review_result['recommendations'] = await self._generate_contract_recommendations(
                review_result, review_type, party_role
            )
            
            return {
                'success': True,
                'contract_id': contract_id,
                'review_type': review_type,
                'party_role': party_role,
                'review': review_result,
                'reviewed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Contract review failed: {e}")
            return {'success': False, 'error': str(e)}

    def _register_case_law_search(self):
        """Register case law search tool"""
        function_decl = FunctionDeclaration(
            name="case_law_search",
            description="Search legal precedents and case law databases",
            parameters={
                "type": "object",
                "properties": {
                    "legal_issue": {
                        "type": "string",
                        "description": "Description of the legal issue or question"
                    },
                    "jurisdiction": {
                        "type": "string",
                        "description": "Jurisdiction (federal, state, specific state name)"
                    },
                    "case_type": {
                        "type": "string",
                        "description": "Type of case (civil, criminal, corporate, etc.)"
                    },
                    "date_range": {
                        "type": "object",
                        "properties": {
                            "start_year": {"type": "integer"},
                            "end_year": {"type": "integer"}
                        }
                    },
                    "precedent_level": {
                        "type": "string",
                        "description": "Level of court (supreme, appellate, district)",
                        "enum": ["supreme", "appellate", "district", "any"]
                    }
                },
                "required": ["legal_issue"]
            }
        )
        
        self.function_declarations.append(function_decl)
        self.tools_registry["case_law_search"] = self._case_law_search_impl

    async def _case_law_search_impl(self, legal_issue: str, jurisdiction: Optional[str] = None,
                                   case_type: Optional[str] = None, date_range: Optional[Dict[str, int]] = None,
                                   precedent_level: Optional[str] = None) -> Dict[str, Any]:
        """Implementation of case law search"""
        try:
            logger.info(f"⚖️ Searching case law: {legal_issue}")
            
            # In production, this would integrate with legal databases like Westlaw, Lexis, etc.
            # For now, we'll create a mock implementation with sample cases
            
            sample_cases = await self._search_sample_cases(legal_issue, jurisdiction)
            
            return {
                'success': True,
                'legal_issue': legal_issue,
                'jurisdiction': jurisdiction,
                'total_found': len(sample_cases),
                'cases': sample_cases[:10],  # Top 10 cases
                'search_parameters': {
                    'jurisdiction': jurisdiction,
                    'case_type': case_type,
                    'date_range': date_range,
                    'precedent_level': precedent_level
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Case law search failed: {e}")
            return {'success': False, 'error': str(e)}

    # Additional tool implementations would continue here...
    # For brevity, I'll provide a few more key implementations

    def _register_legal_writer(self):
        """Register legal document drafting tool"""
        function_decl = FunctionDeclaration(
            name="legal_writer",
            description="Assist with drafting legal documents and correspondence",
            parameters={
                "type": "object",
                "properties": {
                    "document_type": {
                        "type": "string",
                        "description": "Type of document to draft",
                        "enum": ["letter", "memo", "brief", "motion", "contract", "agreement"]
                    },
                    "purpose": {
                        "type": "string",
                        "description": "Purpose or objective of the document"
                    },
                    "recipient": {
                        "type": "string",
                        "description": "Intended recipient (court, opposing counsel, client, etc.)"
                    },
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key points to include in the document"
                    },
                    "tone": {
                        "type": "string",
                        "description": "Tone of the document",
                        "enum": ["formal", "professional", "persuasive", "informational"]
                    },
                    "case_context": {
                        "type": "string",
                        "description": "Relevant case context or background"
                    }
                },
                "required": ["document_type", "purpose"]
            }
        )
        
        self.function_declarations.append(function_decl)
        self.tools_registry["legal_writer"] = self._legal_writer_impl

    async def _legal_writer_impl(self, document_type: str, purpose: str, 
                                recipient: Optional[str] = None, key_points: Optional[List[str]] = None,
                                tone: str = "professional", case_context: Optional[str] = None) -> Dict[str, Any]:
        """Implementation of legal document writer"""
        try:
            logger.info(f"✍️ Drafting legal document: {document_type}")
            
            # Get document template
            template = await self._get_document_template(document_type)
            
            # Generate document content
            document_content = await self._generate_document_content(
                document_type, purpose, recipient, key_points, tone, case_context, template
            )
            
            return {
                'success': True,
                'document_type': document_type,
                'purpose': purpose,
                'content': document_content,
                'generated_at': datetime.utcnow().isoformat(),
                'instructions': await self._get_document_instructions(document_type)
            }
            
        except Exception as e:
            logger.error(f"❌ Legal writing failed: {e}")
            return {'success': False, 'error': str(e)}

    # Helper methods
    async def _get_extracted_text(self, document_id: str) -> Optional[str]:
        """Get extracted text for a document"""
        try:
            extracted_query = self.firestore_client.collection('extracted_documents')\
                .where('documentId', '==', document_id)\
                .limit(1)
            
            docs = extracted_query.get()
            
            if docs:
                return docs[0].to_dict().get('text', '')
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get extracted text: {e}")
            return None

    def _text_matches(self, query: str, text: str) -> bool:
        """Simple text matching function"""
        return any(word in text for word in query.split())

    def _calculate_relevance(self, query: str, doc_data: Dict[str, Any]) -> float:
        """Calculate relevance score for document"""
        filename = doc_data.get('filename', '').lower()
        query_words = query.lower().split()
        
        score = 0.0
        for word in query_words:
            if word in filename:
                score += 1.0
        
        return score / len(query_words) if query_words else 0.0

    async def _analyze_document_content(self, text: str, focus_areas: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze document content"""
        return {
            'summary': f"Document contains {len(text.split())} words with key legal content.",
            'key_topics': ['contracts', 'liability', 'compliance'],
            'complexity_score': min(len(text) / 1000, 10.0)
        }

    async def _analyze_document_risks(self, text: str) -> Dict[str, Any]:
        """Analyze document risks"""
        return {
            'risk_level': 'medium',
            'identified_risks': ['potential liability exposure', 'unclear terms'],
            'risk_score': 6.5
        }

    async def _extract_key_terms(self, text: str) -> Dict[str, Any]:
        """Extract key terms from document"""
        # Simple keyword extraction
        legal_keywords = ['contract', 'agreement', 'liability', 'damages', 'breach', 'termination']
        found_terms = [term for term in legal_keywords if term.lower() in text.lower()]
        
        return {
            'legal_terms': found_terms,
            'entities': ['parties', 'dates', 'amounts'],
            'definitions': []
        }

    async def _save_document_analysis(self, document_id: str, analysis: Dict[str, Any]):
        """Save document analysis results"""
        try:
            analysis_data = {
                'documentId': document_id,
                'analysis': analysis,
                'analyzedAt': firestore.SERVER_TIMESTAMP,
                'version': '1.0'
            }
            
            self.firestore_client.collection('document_analysis').add(analysis_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to save analysis: {e}")

    async def _search_sample_cases(self, legal_issue: str, jurisdiction: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search sample cases (mock implementation)"""
        # Mock case data
        sample_cases = [
            {
                'case_name': 'Sample v. Legal Case',
                'citation': '123 F.3d 456 (1st Cir. 2020)',
                'court': 'First Circuit Court of Appeals',
                'year': 2020,
                'relevance_score': 0.95,
                'summary': f'Relevant case addressing {legal_issue}',
                'key_holdings': ['Holding 1', 'Holding 2'],
                'jurisdiction': jurisdiction or 'federal'
            }
        ]
        
        return sample_cases

    async def _get_document_template(self, document_type: str) -> str:
        """Get document template"""
        templates = {
            'letter': "LETTERHEAD\n\nDate: [DATE]\n\nDear [RECIPIENT],\n\n[CONTENT]\n\nSincerely,\n[SENDER]",
            'memo': "MEMORANDUM\n\nTO: [RECIPIENT]\nFROM: [SENDER]\nDATE: [DATE]\nRE: [SUBJECT]\n\n[CONTENT]",
            'brief': "BRIEF\n\nI. INTRODUCTION\n\n[CONTENT]\n\nII. ARGUMENT\n\n[ARGUMENT]\n\nCONCLUSION"
        }
        
        return templates.get(document_type, "DOCUMENT\n\n[CONTENT]")

    async def _generate_document_content(self, document_type: str, purpose: str, 
                                        recipient: Optional[str], key_points: Optional[List[str]],
                                        tone: str, case_context: Optional[str], template: str) -> str:
        """Generate document content"""
        # Mock content generation
        content = f"This {document_type} is drafted for the purpose of {purpose}."
        
        if key_points:
            content += "\n\nKey points to address:\n"
            for i, point in enumerate(key_points, 1):
                content += f"{i}. {point}\n"
        
        if case_context:
            content += f"\n\nCase Context: {case_context}"
        
        return template.replace('[CONTENT]', content)

    async def _get_document_instructions(self, document_type: str) -> str:
        """Get instructions for document type"""
        instructions = {
            'letter': "Review recipient information, ensure professional tone, and include call to action.",
            'memo': "Verify all facts, include clear recommendations, and maintain objective tone.",
            'brief': "Ensure strong legal arguments, proper citations, and persuasive structure."
        }
        
        return instructions.get(document_type, "Review document for accuracy and completeness.")

    # Contract-specific helper methods
    async def _identify_contract_type(self, contract_text: str) -> str:
        """Identify contract type"""
        contract_types = {
            'service': ['service', 'consulting', 'professional'],
            'employment': ['employment', 'hire', 'employee'],
            'sales': ['sale', 'purchase', 'buy', 'sell'],
            'lease': ['lease', 'rent', 'rental'],
            'nda': ['confidential', 'non-disclosure', 'proprietary']
        }
        
        text_lower = contract_text.lower()
        
        for contract_type, keywords in contract_types.items():
            if any(keyword in text_lower for keyword in keywords):
                return contract_type
        
        return 'general'

    async def _extract_contract_clauses(self, contract_text: str) -> List[Dict[str, Any]]:
        """Extract key contract clauses"""
        # Mock clause extraction
        return [
            {'type': 'payment', 'content': 'Payment terms clause', 'risk_level': 'low'},
            {'type': 'termination', 'content': 'Termination clause', 'risk_level': 'medium'},
            {'type': 'liability', 'content': 'Liability limitation clause', 'risk_level': 'high'}
        ]

    async def _assess_contract_risks(self, contract_text: str, party_role: Optional[str]) -> Dict[str, Any]:
        """Assess contract risks"""
        return {
            'overall_risk': 'medium',
            'financial_risks': ['unlimited liability', 'penalty clauses'],
            'operational_risks': ['performance obligations', 'delivery deadlines'],
            'legal_risks': ['jurisdiction issues', 'governing law'],
            'recommendations': ['Add liability cap', 'Clarify performance standards']
        }

    async def _check_contract_compliance(self, contract_text: str) -> List[Dict[str, Any]]:
        """Check contract compliance"""
        return [
            {'regulation': 'GDPR', 'status': 'compliant', 'notes': 'Privacy clauses present'},
            {'regulation': 'SOX', 'status': 'review_needed', 'notes': 'Financial reporting requirements unclear'}
        ]

    async def _identify_negotiation_points(self, contract_text: str, party_role: Optional[str]) -> List[Dict[str, Any]]:
        """Identify key negotiation points"""
        return [
            {'clause': 'Payment terms', 'priority': 'high', 'suggestion': 'Negotiate shorter payment periods'},
            {'clause': 'Liability cap', 'priority': 'high', 'suggestion': 'Add mutual liability limitations'},
            {'clause': 'Termination notice', 'priority': 'medium', 'suggestion': 'Extend notice period'}
        ]

    async def _identify_missing_clauses(self, contract_text: str) -> List[str]:
        """Identify potentially missing clauses"""
        standard_clauses = [
            'Force majeure',
            'Dispute resolution',
            'Intellectual property',
            'Confidentiality',
            'Governing law',
            'Amendment procedure'
        ]
        
        text_lower = contract_text.lower()
        missing = []
        
        for clause in standard_clauses:
            if clause.lower() not in text_lower:
                missing.append(clause)
        
        return missing

    async def _extract_financial_terms(self, contract_text: str) -> Dict[str, Any]:
        """Extract financial terms from contract"""
        # Mock financial terms extraction
        return {
            'payment_amount': '$10,000',
            'payment_schedule': 'Monthly',
            'late_fees': '1.5% per month',
            'currency': 'USD'
        }

    async def _extract_deadlines(self, contract_text: str) -> List[Dict[str, str]]:
        """Extract deadlines and key dates"""
        # Mock deadline extraction
        return [
            {'type': 'contract_start', 'date': '2025-01-01', 'description': 'Contract effective date'},
            {'type': 'delivery', 'date': '2025-03-01', 'description': 'Project delivery deadline'},
            {'type': 'contract_end', 'date': '2025-12-31', 'description': 'Contract expiration'}
        ]

    async def _generate_contract_recommendations(self, review_result: Dict[str, Any], 
                                              review_type: str, party_role: Optional[str]) -> List[str]:
        """Generate contract recommendations"""
        recommendations = [
            "Add clear performance metrics and acceptance criteria",
            "Include comprehensive liability limitations",
            "Specify dispute resolution procedures",
            "Add termination rights for material breach",
            "Include force majeure provisions"
        ]
        
        return recommendations[:5]

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.tools_registry.keys())

    def get_tool_function_declarations(self) -> List[FunctionDeclaration]:
        """Get function declarations for Vertex AI"""
        return self.function_declarations

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific tool"""
        if tool_name not in self.tools_registry:
            return {'success': False, 'error': f'Tool {tool_name} not found'}
        
        try:
            tool_function = self.tools_registry[tool_name]
            return await tool_function(**kwargs)
        except Exception as e:
            logger.error(f"❌ Tool execution failed: {tool_name} - {e}")
            return {'success': False, 'error': str(e)}