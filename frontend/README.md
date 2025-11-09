legal-case-ai-gcp/
│
├── README.md
├── .gitignore
├── architecture-diagram.png
│
├── frontend/                                    # React + Vite Frontend
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/
│   │   │   ├── auth/
│   │   │   │   ├── Login.jsx
│   │   │   │   └── ProtectedRoute.jsx
│   │   │   ├── cases/
│   │   │   │   ├── CaseList.jsx
│   │   │   │   ├── CaseCard.jsx
│   │   │   │   └── CreateCaseDialog.jsx
│   │   │   ├── documents/
│   │   │   │   ├── DocumentList.jsx
│   │   │   │   ├── DocumentUpload.jsx
│   │   │   │   ├── DocumentPreview.jsx
│   │   │   │   └── DocumentAnalysis.jsx
│   │   │   ├── analysis/
│   │   │   │   ├── CaseAnalysisView.jsx
│   │   │   │   └── AnalysisExport.jsx
│   │   │   └── chat/
│   │   │       ├── AIAgentChat.jsx
│   │   │       └── ChatMessage.jsx
│   │   ├── pages/
│   │   │   ├── HomePage.jsx
│   │   │   ├── CasesPage.jsx
│   │   │   ├── DocumentsPage.jsx
│   │   │   └── AIAgentPage.jsx
│   │   ├── services/
│   │   │   ├── api.js
│   │   │   ├── firebase.js
│   │   │   └── websocket.js
│   │   ├── utils/
│   │   │   ├── pdfGenerator.js
│   │   │   └── helpers.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   ├── firebase.json
│   ├── .firebaserc
│   └── Dockerfile                              # Optional: for Cloud Run hosting
│
├── services/                                    # Cloud Run Microservices
│   │
│   ├── case-service/                           # Cases CRUD API
│   │   ├── src/
│   │   │   ├── index.js
│   │   │   ├── routes/
│   │   │   │   └── cases.js
│   │   │   ├── controllers/
│   │   │   │   └── caseController.js
│   │   │   └── middleware/
│   │   │       └── auth.js
│   │   ├── package.json
│   │   ├── Dockerfile
│   │   └── .dockerignore
│   │
│   ├── document-service/                       # Document Upload & Management
│   │   ├── src/
│   │   │   ├── index.js
│   │   │   ├── routes/
│   │   │   │   └── documents.js
│   │   │   ├── controllers/
│   │   │   │   ├── uploadController.js
│   │   │   │   └── previewController.js
│   │   │   └── services/
│   │   │       └── storageService.js
│   │   ├── package.json
│   │   ├── Dockerfile
│   │   └── .dockerignore
│   │
│   ├── extraction-service/                     # Document Text Extraction
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── extractor.py
│   │   │   └── firestore_client.py
│   │   ├── requirements.txt
│   │ 
│   ├── document-analysis-service/              # Single Document AI Analysis
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── analyzer.py
│   │   │   └── gemini_client.py
│   │   ├── requirements.txt
│   ├── case-analysis-service/                  # Full Case AI Analysis
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── case_analyzer.py
│   │   │   └── gemini_client.py
│   │   ├── requirements.txt
│   │   
│   │
│   ├── ai-agent-service/                       # Multi-Agent Chat System
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── orchestrator.py
│   │   │   ├── agents/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── evidence_agent.py
│   │   │   │   ├── summary_agent.py
│   │   │   │   ├── draft_agent.py
│   │   │   │   └── general_agent.py
│   │   │   ├── tools/
│   │   │   │   ├── search_tool.py
│   │   │   │   └── document_tool.py
│   │   │   └── websocket_handler.py
│   │   ├── requirements.txt
│   ├── pdf-generator-service/                  # PDF Report Generation
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── pdf_generator.py
│   │   │   └── templates/
│   │   │       └── analysis_template.html
│   │   ├── requirements.txt
│   │
│   └── email-service/                          # Email Notifications
│       ├── src/
│       │   ├── index.js
│       │   ├── emailSender.js
│       │   └── templates/
│       │       └── analysis-email.html
│       ├── package.json
│
├── ai-agents/                                   # Vertex AI Agent (ADK) Setup
│   ├── agent_config.yaml
│   ├── deploy_agent.py
│   ├── agent_tools.py
│   ├── knowledge_base/
│   │   ├── setup_knowledge_base.py
│   │   └── sample_legal_docs/
│   └── requirements.txt
│
├── infrastructure/                              # IaC & Deployment
│   ├── terraform/                              # Optional: Terraform
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── firestore.tf
│   │   ├── storage.tf
│   │   ├── cloud_run.tf
│   │   └── iam.tf
│   ├── scripts/
│   │   ├── deploy-all.sh
│   │   ├── setup-gcp.sh
│   │   ├── enable-apis.sh
│   │   └── setup-firestore.sh
│   └── eventarc/
│       └── storage-triggers.yaml
│
├── shared/                                      # Shared libraries
│   ├── nodejs/
│   │   ├── firestore-client.js
│   │   └── auth-middleware.js
│   └── python/
│       ├── firestore_client.py
│       └── auth_middleware.py
│
├── config/                                      # Configuration files
│   ├── firestore.rules
│   ├── storage.rules
│   ├── env.example
│   └── service-urls.json
│
│
└── cloudbuild.yaml                             # CI/CD Pipeline