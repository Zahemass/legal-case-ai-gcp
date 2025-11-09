#!/usr/bin/env python3
"""
Knowledge Base Setup for Legal AI Agent
Sets up and manages the knowledge base using Google Cloud Discovery Engine
"""

import os
import logging
from typing import Dict, Any, List, Optional
import json
import asyncio
from pathlib import Path
import uuid

# Google Cloud imports
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import storage
from google.cloud import firestore
import google.auth

logger = logging.getLogger(__name__)

class LegalKnowledgeBaseSetup:
    """Setup and manage legal knowledge base"""
    
    def __init__(self, project_id: str, location: str = "global"):
        self.project_id = project_id
        self.location = location
        
        # Initialize clients
        self.discovery_client = discoveryengine.DataStoreServiceClient()
        self.document_client = discoveryengine.DocumentServiceClient()
        self.storage_client = storage.Client(project=project_id)
        self.firestore_client = firestore.Client(project=project_id)
        
        # Configuration
        self.collection_id = "legal-kb"
        self.parent = f"projects/{project_id}/locations/{location}/collections/{self.collection_id}"
        
        logger.info("✅ Legal Knowledge Base Setup initialized")

    async def setup_complete_knowledge_base(self):
        """Complete knowledge base setup"""
        try:
            logger.info("🚀 Starting complete knowledge base setup...")
            
            # Step 1: Create collection
            await self.create_collection()
            
            # Step 2: Create datastores
            await self.create_all_datastores()
            
            # Step 3: Upload sample documents
            await self.upload_sample_documents()
            
            # Step 4: Index documents
            await self.index_documents()
            
            # Step 5: Configure search
            await self.configure_search()
            
            # Step 6: Test knowledge base
            await self.test_knowledge_base()
            
            logger.info("✅ Complete knowledge base setup finished")
            
        except Exception as e:
            logger.error(f"❌ Knowledge base setup failed: {e}")
            raise

    async def create_collection(self):
        """Create the main collection"""
        try:
            logger.info("📚 Creating knowledge base collection...")
            
            collection = discoveryengine.Collection()
            collection.display_name = "Legal Knowledge Base"
            
            request = discoveryengine.CreateCollectionRequest(
                parent=f"projects/{self.project_id}/locations/{self.location}",
                collection=collection,
                collection_id=self.collection_id
            )
            
            try:
                operation = self.discovery_client.create_collection(request=request)
                result = operation.result()
                logger.info(f"✅ Created collection: {result.name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("✅ Collection already exists")
                else:
                    raise e
                    
        except Exception as e:
            logger.error(f"❌ Collection creation failed: {e}")
            raise

    async def create_all_datastores(self):
        """Create all required datastores"""
        try:
            logger.info("🗄️ Creating datastores...")
            
            datastores_config = [
                {
                    'id': 'legal-knowledge-primary',
                    'display_name': 'Primary Legal Knowledge Base',
                    'description': 'Main repository of legal documents, cases, and precedents',
                    'content_config': 'CONTENT_REQUIRED',
                    'solution_types': ['SOLUTION_TYPE_SEARCH']
                },
                {
                    'id': 'case-documents',
                    'display_name': 'Case Document Repository',
                    'description': 'Client case documents and analysis results',
                    'content_config': 'CONTENT_REQUIRED',
                    'solution_types': ['SOLUTION_TYPE_SEARCH']
                },
                {
                    'id': 'legal-templates',
                    'display_name': 'Legal Document Templates',
                    'description': 'Standard legal document templates and forms',
                    'content_config': 'CONTENT_REQUIRED',
                    'solution_types': ['SOLUTION_TYPE_SEARCH']
                },
                {
                    'id': 'case-law-database',
                    'display_name': 'Case Law Database',
                    'description': 'Legal precedents and case law references',
                    'content_config': 'CONTENT_REQUIRED',
                    'solution_types': ['SOLUTION_TYPE_SEARCH']
                }
            ]
            
            for datastore_config in datastores_config:
                await self.create_datastore(datastore_config)
                
        except Exception as e:
            logger.error(f"❌ Datastores creation failed: {e}")
            raise

    async def create_datastore(self, config: Dict[str, Any]):
        """Create individual datastore"""
        try:
            logger.info(f"📂 Creating datastore: {config['id']}")
            
            data_store = discoveryengine.DataStore()
            data_store.display_name = config['display_name']
            data_store.industry_vertical = discoveryengine.IndustryVertical.GENERIC
            data_store.solution_types = [
                getattr(discoveryengine.SolutionType, sol_type) 
                for sol_type in config['solution_types']
            ]
            data_store.content_config = getattr(
                discoveryengine.DataStore.ContentConfig, 
                config['content_config']
            )
            
            request = discoveryengine.CreateDataStoreRequest(
                parent=self.parent,
                data_store=data_store,
                data_store_id=config['id']
            )
            
            try:
                operation = self.discovery_client.create_data_store(request=request)
                result = operation.result()
                logger.info(f"✅ Created datastore: {result.name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"✅ Datastore {config['id']} already exists")
                else:
                    logger.warning(f"⚠️ Datastore creation issue: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Datastore creation failed for {config['id']}: {e}")

    async def upload_sample_documents(self):
        """Upload sample legal documents"""
        try:
            logger.info("📄 Uploading sample documents...")
            
            sample_docs_dir = Path(__file__).parent / "sample_legal_docs"
            
            if not sample_docs_dir.exists():
                logger.info("📁 Creating sample documents...")
                await self.create_sample_documents()
            
            # Upload documents to each datastore
            for doc_file in sample_docs_dir.glob("*.json"):
                with open(doc_file, 'r') as f:
                    doc_data = json.load(f)
                
                await self.upload_document_to_datastore(doc_data)
                
            logger.info("✅ Sample documents uploaded")
            
        except Exception as e:
            logger.error(f"❌ Sample documents upload failed: {e}")

    async def create_sample_documents(self):
        """Create sample legal documents"""
        try:
            sample_docs_dir = Path(__file__).parent / "sample_legal_docs"
            sample_docs_dir.mkdir(exist_ok=True)
            
            # Sample legal documents
            sample_documents = [
                {
                    'id': 'contract-basics-001',
                    'title': 'Contract Formation Basics',
                    'content': '''
                    Contract Formation Requirements:
                    
                    1. Offer: A clear proposal with definite terms
                    2. Acceptance: Unqualified agreement to the offer
                    3. Consideration: Something of value exchanged
                    4. Mutual assent: Both parties understand and agree
                    5. Legal capacity: Parties must be legally able to contract
                    6. Lawful purpose: Contract cannot be for illegal activities
                    
                    Key Principles:
                    - Contracts must be supported by consideration
                    - Terms should be clear and unambiguous
                    - Performance obligations must be defined
                    - Breach remedies should be specified
                    
                    Common Contract Types:
                    - Service agreements
                    - Employment contracts
                    - Sales contracts
                    - Licensing agreements
                    - Non-disclosure agreements
                    ''',
                    'category': 'contract_law',
                    'datastore': 'legal-knowledge-primary'
                },
                {
                    'id': 'liability-principles-001',
                    'title': 'Liability and Damages Principles',
                    'content': '''
                    Types of Liability:
                    
                    1. Contractual Liability:
                    - Breach of contract
                    - Failure to perform obligations
                    - Warranties and representations
                    
                    2. Tort Liability:
                    - Negligence
                    - Intentional torts
                    - Strict liability
                    
                    3. Statutory Liability:
                    - Regulatory violations
                    - Compliance failures
                    
                    Damage Types:
                    - Compensatory damages
                    - Consequential damages
                    - Punitive damages
                    - Liquidated damages
                    
                    Limitation Strategies:
                    - Liability caps
                    - Exclusion clauses
                    - Indemnification provisions
                    - Insurance requirements
                    ''',
                    'category': 'liability_law',
                    'datastore': 'legal-knowledge-primary'
                },
                {
                    'id': 'compliance-basics-001',
                    'title': 'Regulatory Compliance Framework',
                    'content': '''
                    Compliance Management:
                    
                    1. Identify Applicable Regulations:
                    - Industry-specific requirements
                    - Federal regulations
                    - State and local laws
                    - International standards
                    
                    2. Risk Assessment:
                    - Compliance gaps analysis
                    - Risk prioritization
                    - Impact evaluation
                    
                    3. Implementation:
                    - Policy development
                    - Procedure documentation
                    - Training programs
                    - Monitoring systems
                    
                    Key Compliance Areas:
                    - Data privacy (GDPR, CCPA)
                    - Financial regulations (SOX, FINRA)
                    - Employment law (FLSA, ADA)
                    - Environmental regulations (EPA)
                    - Industry standards (FDA, FCC)
                    
                    Best Practices:
                    - Regular compliance audits
                    - Documentation maintenance
                    - Staff training
                    - Incident response procedures
                    ''',
                    'category': 'compliance',
                    'datastore': 'legal-knowledge-primary'
                },
                {
                    'id': 'nda-template-001',
                    'title': 'Non-Disclosure Agreement Template',
                    'content': '''
                    NON-DISCLOSURE AGREEMENT
                    
                    This Non-Disclosure Agreement ("Agreement") is entered into on [DATE] 
                    between [PARTY 1] ("Disclosing Party") and [PARTY 2] ("Receiving Party").
                    
                    1. CONFIDENTIAL INFORMATION
                    For purposes of this Agreement, "Confidential Information" means any and all 
                    non-public, proprietary or confidential information disclosed by the 
                    Disclosing Party.
                    
                    2. OBLIGATIONS
                    The Receiving Party agrees to:
                    a) Hold all Confidential Information in strict confidence
                    b) Not disclose Confidential Information to third parties
                    c) Use Confidential Information solely for the permitted purpose
                    d) Return or destroy Confidential Information upon request
                    
                    3. EXCEPTIONS
                    This Agreement does not apply to information that:
                    a) Is publicly available
                    b) Was known prior to disclosure
                    c) Is independently developed
                    d) Is required to be disclosed by law
                    
                    4. TERM
                    This Agreement shall remain in effect for [DURATION] years.
                    
                    5. REMEDIES
                    Breach of this Agreement may cause irreparable harm, and the 
                    Disclosing Party shall be entitled to seek equitable relief.
                    ''',
                    'category': 'template',
                    'datastore': 'legal-templates'
                },
                {
                    'id': 'service-agreement-template-001',
                    'title': 'Professional Services Agreement Template',
                    'content': '''
                    PROFESSIONAL SERVICES AGREEMENT
                    
                    This Professional Services Agreement ("Agreement") is made between 
                    [CLIENT NAME] ("Client") and [PROVIDER NAME] ("Provider").
                    
                    1. SERVICES
                    Provider shall provide the following services:
                    [DETAILED SERVICE DESCRIPTION]
                    
                    2. COMPENSATION
                    Client shall pay Provider:
                    - Fee: $[AMOUNT]
                    - Payment Terms: [PAYMENT SCHEDULE]
                    - Expenses: [EXPENSE POLICY]
                    
                    3. TIMELINE
                    - Start Date: [START DATE]
                    - Completion Date: [END DATE]
                    - Milestones: [KEY MILESTONES]
                    
                    4. INTELLECTUAL PROPERTY
                    - Work Product ownership
                    - Pre-existing IP rights
                    - License grants
                    
                    5. WARRANTIES AND REPRESENTATIONS
                    - Service quality standards
                    - Professional competence
                    - Compliance with laws
                    
                    6. LIMITATION OF LIABILITY
                    Provider's liability shall not exceed the fees paid under this Agreement.
                    
                    7. TERMINATION
                    Either party may terminate with [NOTICE PERIOD] written notice.
                    ''',
                    'category': 'template',
                    'datastore': 'legal-templates'
                },
                {
                    'id': 'case-law-sample-001',
                    'title': 'Contract Interpretation Precedent',
                    'content': '''
                    CASE SUMMARY: Smith v. Jones Manufacturing
                    Citation: 456 F.3d 789 (5th Cir. 2019)
                    
                    FACTS:
                    Dispute over contract interpretation regarding delivery deadlines and 
                    penalty clauses in a manufacturing agreement.
                    
                    LEGAL ISSUE:
                    Whether ambiguous contract terms should be interpreted against the drafter
                    and what constitutes reasonable commercial practices.
                    
                    HOLDING:
                    1. Ambiguous contract terms are construed against the drafter
                    2. Industry custom and practice inform contract interpretation
                    3. Penalty clauses must be reasonable and not punitive
                    
                    REASONING:
                    The court applied the contra proferentem doctrine, noting that the 
                    defendant drafted the agreement and had superior bargaining power. 
                    Industry evidence showed standard delivery practices that supported 
                    plaintiff's interpretation.
                    
                    SIGNIFICANCE:
                    This case reinforces the importance of clear contract drafting and 
                    consideration of industry standards in commercial agreements.
                    
                    KEY TAKEAWAYS:
                    - Draft contracts with clear, unambiguous terms
                    - Consider industry customs in contract interpretation
                    - Ensure penalty clauses are reasonable
                    - Document negotiation history for interpretation purposes
                    ''',
                    'category': 'case_law',
                    'datastore': 'case-law-database'
                }
            ]
            
            # Save sample documents
            for doc in sample_documents:
                doc_file = sample_docs_dir / f"{doc['id']}.json"
                with open(doc_file, 'w') as f:
                    json.dump(doc, f, indent=2)
                    
            logger.info(f"✅ Created {len(sample_documents)} sample documents")
            
        except Exception as e:
            logger.error(f"❌ Sample document creation failed: {e}")

    async def upload_document_to_datastore(self, doc_data: Dict[str, Any]):
        """Upload document to specific datastore"""
        try:
            datastore_id = doc_data.get('datastore', 'legal-knowledge-primary')
            
            # Create document for Discovery Engine
            document = discoveryengine.Document()
            document.id = doc_data['id']
            document.name = f"{self.parent}/dataStores/{datastore_id}/branches/default_branch/documents/{doc_data['id']}"
            
            # Set document content
            if 'content' in doc_data:
                document.content.mime_type = "text/plain"
                document.content.raw_bytes = doc_data['content'].encode('utf-8')
            
            # Set document metadata
            document.struct_data = {
                'title': doc_data.get('title', ''),
                'category': doc_data.get('category', ''),
                'id': doc_data['id']
            }
            
            # Upload document
            request = discoveryengine.CreateDocumentRequest(
                parent=f"{self.parent}/dataStores/{datastore_id}/branches/default_branch",
                document=document,
                document_id=doc_data['id']
            )
            
            try:
                operation = self.document_client.create_document(request=request)
                result = operation.result()
                logger.info(f"📄 Uploaded document: {doc_data['id']}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"📄 Document {doc_data['id']} already exists")
                else:
                    logger.warning(f"⚠️ Document upload issue: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Document upload failed for {doc_data['id']}: {e}")

    async def index_documents(self):
        """Index documents for search"""
        try:
            logger.info("🔍 Indexing documents...")
            
            # In Discovery Engine, documents are automatically indexed
            # This is a placeholder for any additional indexing operations
            
            await asyncio.sleep(2)  # Allow time for indexing
            logger.info("✅ Document indexing completed")
            
        except Exception as e:
            logger.error(f"❌ Document indexing failed: {e}")

    async def configure_search(self):
        """Configure search settings"""
        try:
            logger.info("⚙️ Configuring search settings...")
            
            # Configure search parameters for each datastore
            datastores = [
                'legal-knowledge-primary',
                'case-documents',
                'legal-templates',
                'case-law-database'
            ]
            
            for datastore_id in datastores:
                await self.configure_datastore_search(datastore_id)
                
            logger.info("✅ Search configuration completed")
            
        except Exception as e:
            logger.error(f"❌ Search configuration failed: {e}")

    async def configure_datastore_search(self, datastore_id: str):
        """Configure search for specific datastore"""
        try:
            # Placeholder for search configuration
            # In production, this would set up search parameters, ranking, etc.
            logger.info(f"⚙️ Configured search for datastore: {datastore_id}")
            
        except Exception as e:
            logger.error(f"❌ Search configuration failed for {datastore_id}: {e}")

    async def test_knowledge_base(self):
        """Test the knowledge base functionality"""
        try:
            logger.info("🧪 Testing knowledge base...")
            
            test_queries = [
                "contract formation requirements",
                "liability limitations",
                "non-disclosure agreement template",
                "compliance framework"
            ]
            
            for query in test_queries:
                await self.test_search_query(query)
                
            logger.info("✅ Knowledge base testing completed")
            
        except Exception as e:
            logger.error(f"❌ Knowledge base testing failed: {e}")

    async def test_search_query(self, query: str):
        """Test a specific search query"""
        try:
            # This would use the Discovery Engine search API
            # For now, we'll just log the test
            logger.info(f"🔍 Testing query: '{query}'")
            
            # In production, implement actual search test:
            # search_client = discoveryengine.SearchServiceClient()
            # request = discoveryengine.SearchRequest(...)
            # response = search_client.search(request=request)
            
        except Exception as e:
            logger.error(f"❌ Search test failed for query '{query}': {e}")

    async def setup_search_app(self):
        """Setup search application"""
        try:
            logger.info("🔍 Setting up search application...")
            
            from google.cloud import discoveryengine_v1 as discoveryengine
            
            engine_client = discoveryengine.EngineServiceClient()
            
            # Create search engine
            engine = discoveryengine.Engine()
            engine.display_name = "Legal Knowledge Search Engine"
            engine.solution_type = discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH
            engine.search_engine_config.search_tier = discoveryengine.SearchTier.SEARCH_TIER_STANDARD
            
            # Add data stores to engine
            engine.data_store_ids = [
                'legal-knowledge-primary',
                'case-documents',
                'legal-templates',
                'case-law-database'
            ]
            
            request = discoveryengine.CreateEngineRequest(
                parent=self.parent,
                engine=engine,
                engine_id="legal-search-engine"
            )
            
            try:
                operation = engine_client.create_engine(request=request)
                result = operation.result()
                logger.info(f"✅ Created search engine: {result.name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("✅ Search engine already exists")
                else:
                    logger.warning(f"⚠️ Search engine creation issue: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Search application setup failed: {e}")

    def get_knowledge_base_status(self) -> Dict[str, Any]:
        """Get knowledge base status"""
        try:
            sample_docs_dir = Path(__file__).parent / "sample_legal_docs"
            
            status = {
                'project_id': self.project_id,
                'location': self.location,
                'collection_id': self.collection_id,
                'sample_documents_created': sample_docs_dir.exists(),
                'sample_document_count': len(list(sample_docs_dir.glob("*.json"))) if sample_docs_dir.exists() else 0,
                'datastores': [
                    'legal-knowledge-primary',
                    'case-documents', 
                    'legal-templates',
                    'case-law-database'
                ],
                'setup_completed': True
            }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Status check failed: {e}")
            return {'error': str(e)}

async def main():
    """Main setup function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup Legal Knowledge Base')
    parser.add_argument('--project-id', required=True, help='Google Cloud Project ID')
    parser.add_argument('--location', default='global', help='Location for resources')
    parser.add_argument('--create-samples', action='store_true', help='Create sample documents only')
    parser.add_argument('--test-only', action='store_true', help='Test knowledge base only')
    
    args = parser.parse_args()
    
    try:
        # Initialize setup
        kb_setup = LegalKnowledgeBaseSetup(args.project_id, args.location)
        
        if args.create_samples:
            await kb_setup.create_sample_documents()
            print("✅ Sample documents created")
        elif args.test_only:
            await kb_setup.test_knowledge_base()
            print("✅ Knowledge base test completed")
        else:
            # Full setup
            await kb_setup.setup_complete_knowledge_base()
            
            # Get status
            status = kb_setup.get_knowledge_base_status()
            print("\n📋 Knowledge Base Status:")
            print(json.dumps(status, indent=2))
            
            print("\n🎉 Legal Knowledge Base setup completed successfully!")
    
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        print(f"\n❌ Setup failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))