# Legal Case AI - Main Terraform Configuration
# Created: 2025-11-01 09:59:10 UTC
# Author: Zahemassg

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.4"
    }
  }

  # Backend configuration for state management
  backend "gcs" {
    bucket = "legal-case-ai-terraform-state"
    prefix = "terraform/state"
  }
}

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Random string for unique resource naming
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# Local values for resource naming
locals {
  project_name = "legal-case-ai"
  suffix       = random_string.suffix.result
  
  # Common labels
  common_labels = {
    project     = local.project_name
    environment = var.environment
    managed_by  = "terraform"
    created_by  = "zahemassg"
    created_at  = "2025-11-01"
  }

  # Service names
  services = {
    main_api         = "main-api"
    document_upload  = "document-upload-service"
    extraction      = "text-extraction-service"
    analysis        = "case-analysis-service"
    ai_agent        = "ai-agent-service"
    pdf_generator   = "pdf-generator-service"
    email_service   = "email-service"
  }
}

# Enable required Google Cloud APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "pubsub.googleapis.com",
    "eventarc.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "aiplatform.googleapis.com",
    "documentai.googleapis.com",
    "vision.googleapis.com",
    "translate.googleapis.com",
    "discoveryengine.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudtrace.googleapis.com",
    "cloudprofiler.googleapis.com",
    "cloudscheduler.googleapis.com"
  ])

  project = var.project_id
  service = each.key

  disable_dependent_services = false
  disable_on_destroy        = false
}

# Create Artifact Registry for container images
resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "${local.project_name}-images"
  description   = "Container images for Legal Case AI services"
  format        = "DOCKER"
  
  labels = local.common_labels

  depends_on = [google_project_service.apis]
}

# Create Cloud Scheduler job for cleanup tasks
resource "google_cloud_scheduler_job" "cleanup" {
  name     = "legal-case-ai-cleanup"
  schedule = "0 2 * * *" # Daily at 2 AM
  region   = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${local.services.main_api}-${random_string.suffix.result}-${var.region}-${var.project_id}.a.run.app/admin/cleanup"
    
    headers = {
      "Content-Type" = "application/json"
      "X-API-Key"    = var.internal_api_key
    }
    
    body = base64encode(jsonencode({
      "task" = "daily_cleanup"
      "days_old" = 30
    }))
  }

  depends_on = [google_project_service.apis]
}

# Output important information
output "project_id" {
  description = "The project ID"
  value       = var.project_id
}

output "region" {
  description = "The region"
  value       = var.region
}

output "artifact_registry_url" {
  description = "Artifact Registry repository URL"
  value       = google_artifact_registry_repository.main.name
}

output "services_urls" {
  description = "URLs of deployed Cloud Run services"
  value = {
    main_api        = module.cloud_run.service_urls["main-api"]
    document_upload = module.cloud_run.service_urls["document-upload-service"]
    extraction     = module.cloud_run.service_urls["text-extraction-service"]
    analysis       = module.cloud_run.service_urls["case-analysis-service"]
    ai_agent       = module.cloud_run.service_urls["ai-agent-service"]
    pdf_generator  = module.cloud_run.service_urls["pdf-generator-service"]
    email_service  = module.cloud_run.service_urls["email-service"]
  }
}

output "storage_buckets" {
  description = "Storage bucket names"
  value = {
    documents = module.storage.document_bucket_name
    reports   = module.storage.reports_bucket_name
    backups   = module.storage.backups_bucket_name
  }
}

output "firestore_database" {
  description = "Firestore database information"
  value = {
    name     = module.firestore.database_name
    location = module.firestore.database_location
  }
}

output "pubsub_topics" {
  description = "Pub/Sub topic names"
  value = {
    document_uploaded = google_pubsub_topic.document_uploaded.name
    extraction_complete = google_pubsub_topic.extraction_complete.name
    analysis_complete = google_pubsub_topic.analysis_complete.name
    email_notifications = google_pubsub_topic.email_notifications.name
  }
}

# Create Pub/Sub topics
resource "google_pubsub_topic" "document_uploaded" {
  name = "document-uploaded"
  
  labels = local.common_labels
  
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "extraction_complete" {
  name = "extraction-complete"
  
  labels = local.common_labels
  
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "analysis_complete" {
  name = "analysis-complete"
  
  labels = local.common_labels
  
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "email_notifications" {
  name = "email-notifications"
  
  labels = local.common_labels
  
  depends_on = [google_project_service.apis]
}

# Create subscriptions for each service
resource "google_pubsub_subscription" "document_processing" {
  name  = "document-processing-subscription"
  topic = google_pubsub_topic.document_uploaded.name

  ack_deadline_seconds = 300
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_subscription" "case_analysis" {
  name  = "case-analysis-subscription"
  topic = google_pubsub_topic.extraction_complete.name

  ack_deadline_seconds = 600 # 10 minutes for analysis
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 3
  }
}

resource "google_pubsub_subscription" "pdf_generation" {
  name  = "pdf-generation-subscription"
  topic = google_pubsub_topic.analysis_complete.name

  ack_deadline_seconds = 300
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

resource "google_pubsub_subscription" "email_notification" {
  name  = "email-notification-subscription"
  topic = google_pubsub_topic.email_notifications.name

  ack_deadline_seconds = 60
  
  retry_policy {
    minimum_backoff = "5s"
    maximum_backoff = "300s"
  }
}

# Dead letter topic for failed messages
resource "google_pubsub_topic" "dead_letter" {
  name = "dead-letter-topic"
  
  labels = local.common_labels
}

# Include modules
module "firestore" {
  source = "./firestore.tf"
  
  project_id = var.project_id
  region     = var.region
  labels     = local.common_labels
}

module "storage" {
  source = "./storage.tf"
  
  project_id    = var.project_id
  region        = var.region
  suffix        = local.suffix
  labels        = local.common_labels
  force_destroy = var.environment == "development"
}

module "cloud_run" {
  source = "./cloud_run.tf"
  
  project_id           = var.project_id
  region              = var.region
  suffix              = local.suffix
  labels              = local.common_labels
  services            = local.services
  artifact_registry   = google_artifact_registry_repository.main.name
  internal_api_key    = var.internal_api_key
  firebase_config     = var.firebase_config
  sendgrid_api_key    = var.sendgrid_api_key
  google_ai_api_key   = var.google_ai_api_key
  
  depends_on = [
    google_project_service.apis,
    module.firestore,
    module.storage
  ]
}

module "iam" {
  source = "./iam.tf"
  
  project_id     = var.project_id
  service_suffix = local.suffix
  services       = local.services
}