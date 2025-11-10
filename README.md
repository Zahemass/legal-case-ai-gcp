````🚀 Legal AI - Complete Setup Guide

## 🎯 Project Overview
**Legal AI** is a next-generation legal case management and analysis platform powered by **Google Cloud Platform (GCP)** and **Gemini AI**.  
It enables law firms and legal teams to efficiently manage cases, analyze documents, and interact with intelligent AI agents — all within a secure, serverless GCP environment.

Legal AI leverages **Cloud Run microservices**, **Vertex AI (Gemini)**, and **Pub/Sub event pipelines** to provide real-time, AI-driven legal insights, document summarization, and automated workflows.

---

## 📋 Prerequisites

### 🧰 Required Tools
- Node.js **v18+** and npm
- Python **3.10+**
- Google Cloud SDK (`gcloud`) installed and authenticated
- Git for version control
- Docker (for containerizing and deploying services)
- Terraform (optional, for Infrastructure as Code)

---

## ☁️ Google Cloud Services Used

| Service | Purpose |
|----------|----------|
| **Firebase Authentication** | User sign-in and access control |
| **Firestore** | Case and document metadata storage |
| **Cloud Storage (GCS)** | Legal document storage |
| **Cloud Run** | Serverless containerized APIs and AI services |
| **Pub/Sub** | Asynchronous communication between microservices |
| **Vertex AI (Gemini)** | AI document analysis and reasoning |
| **Cloud Functions / Eventarc** | Trigger analysis when new documents are uploaded |
| **Cloud Logging & Monitoring** | Observability and centralized logs |
| **Cloud Build** | CI/CD for automatic deployment |
| **Cloud IAM** | Secure service-to-service authentication |

---

## 🛠️ Project Setup

### 1️⃣ Clone and Install Dependencies

```bash
# Clone the repository
git clone https://github.com/Zahemass/legal-case-ai-gcp.git
cd legal-case-ai-gcp
````

### 2️⃣ Setup Environment Variables

Copy the example file and update your GCP credentials:

```bash
cp config/env.example .env
```

Update `.env` with your configuration:

```bash
# GCP Project
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1

# Firebase / Firestore
FIREBASE_API_KEY=XXXXXXXXXXXXXXXXXXXXXXXX
FIREBASE_AUTH_DOMAIN=legal-ai.firebaseapp.com
FIREBASE_PROJECT_ID=legal-ai
FIREBASE_STORAGE_BUCKET=legal-ai.appspot.com
FIREBASE_MESSAGING_SENDER_ID=XXXXXXXXXXXX
FIREBASE_APP_ID=1:XXXXXXXXXXXX:web:XXXXXXXXXXXX

# Cloud Storage
GCS_BUCKET_NAME=legalai-case-documents

# Cloud Run Service URLs
CASE_SERVICE_URL=https://case-service-xxxxxxxx.a.run.app
DOCUMENT_SERVICE_URL=https://document-service-xxxxxxxx.a.run.app
EXTRACTION_SERVICE_URL=https://extraction-service-xxxxxxxx.a.run.app
ANALYSIS_SERVICE_URL=https://analysis-service-xxxxxxxx.a.run.app
AI_AGENT_SERVICE_URL=https://ai-agent-service-xxxxxxxx.a.run.app
PDF_GENERATOR_SERVICE_URL=https://pdf-service-xxxxxxxx.a.run.app
EMAIL_SERVICE_URL=https://email-service-xxxxxxxx.a.run.app

# Vertex AI / Gemini
VERTEX_PROJECT_ID=your-gcp-project-id
VERTEX_LOCATION=us-central1
VERTEX_MODEL=gemini-1.5-pro
VERTEX_KNOWLEDGE_BASE_ID=kb_legal_ai

# Pub/Sub
PUBSUB_TOPIC=document-events
PUBSUB_SUBSCRIPTION=analysis-trigger

# Optional
CLOUD_LOGGING_ENABLED=true
```

---

## ⚙️ Frontend Setup (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

Access the app at **[http://localhost:5173](http://localhost:5173)**

---

## 🧩 Backend Microservices (Cloud Run)

Each backend service is containerized and deployed to Cloud Run.
Structure:

```
services/
 ├── case-service/               # Case CRUD APIs
 ├── document-service/           # Upload & Management
 ├── extraction-service/         # Text extraction (Python)
 ├── document-analysis-service/  # Single doc AI analysis
 ├── case-analysis-service/      # Full case analysis
 ├── ai-agent-service/           # Multi-agent chat system
 ├── pdf-generator-service/      # PDF report generation
 └── email-service/              # Email notifications
```

### Deploy each service

```bash
# From the root directory
gcloud builds submit --tag gcr.io/$GCP_PROJECT_ID/case-service ./services/case-service
gcloud run deploy case-service \
  --image gcr.io/$GCP_PROJECT_ID/case-service \
  --platform managed --region=$GCP_REGION --allow-unauthenticated
```

Repeat the same for all other microservices.

---

## 🤖 AI Agent System

The **AI Agent Orchestrator** intelligently routes user prompts to specialized agents:

* `SummaryAgent` → Case summaries
* `EvidenceAgent` → Extracts key facts
* `DraftAgent` → Generates legal drafts
* `GeneralAgent` → Conversational reasoning

Setup:

```bash
cd ai-agents
pip install -r requirements.txt
python deploy_agent.py
```

---

## 🧱 Infrastructure as Code (Terraform)

To automatically provision Cloud Run, Firestore, Storage, and IAM:

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

This will deploy:

* Cloud Run services
* Firestore database
* Cloud Storage buckets
* Pub/Sub topics
* IAM bindings

---

## ⚡ Event Triggers (Eventarc)

When a document is uploaded to Cloud Storage, Eventarc triggers the extraction service automatically:

```bash
cd infrastructure/eventarc
gcloud eventarc triggers create document-upload-trigger \
  --destination-run-service=extraction-service \
  --event-filters="type=google.cloud.storage.object.v1.finalized" \
  --location=$GCP_REGION
```

---

## 🧠 Running AI Analysis Locally

```bash
cd services/document-analysis-service
pip install -r requirements.txt
python src/main.py
```

Test using:

```bash
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"document_url":"gs://legalai-case-documents/sample.pdf"}'
```

---

## 🧾 Logging & Monitoring

View logs for any Cloud Run service:

```bash
gcloud logs read run.googleapis.com%2Fcase-service --project=$GCP_PROJECT_ID
```

---

## 🚀 Deployment Script

Automated full deployment:

```bash
bash infrastructure/scripts/deploy-all.sh
```

## 📄 License

**MIT License** – see `LICENSE` file for details.

---

**Built with ❤️ using Google Cloud, Vertex AI, and Modern Web Technologies**

```


