# Cloud Storage Configuration

# Documents bucket - stores uploaded legal documents
resource "google_storage_bucket" "documents" {
  name          = "${var.project_id}-legal-documents-${var.suffix}"
  location      = var.region
  storage_class = var.storage_class
  
  # Enable versioning for document history
  versioning {
    enabled = true
  }
  
  # Lifecycle management
  lifecycle_rule {
    condition {
      age = var.storage_bucket_lifecycle_age
    }
    action {
      type = "Delete"
    }
  }
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
  
  # CORS configuration for file uploads
  cors {
    origin          = var.cors_origins
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  # Uniform bucket-level access
  uniform_bucket_level_access = true
  
  # Public access prevention
  public_access_prevention = "enforced"
  
  labels = var.labels
  
  force_destroy = var.force_destroy
}

# Reports bucket - stores generated PDF reports
resource "google_storage_bucket" "reports" {
  name          = "${var.project_id}-legal-reports-${var.suffix}"
  location      = var.region
  storage_class = var.storage_class
  
  # Lifecycle management for reports
  lifecycle_rule {
    condition {
      age = 180 # Keep reports for 6 months
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }
  
  lifecycle_rule {
    condition {
      age = 365 # Delete after 1 year
    }
    action {
      type = "Delete"
    }
  }
  
  # CORS for report downloads
  cors {
    origin          = var.cors_origins
    method          = ["GET", "HEAD"]
    response_header = ["Content-Type", "Content-Disposition"]
    max_age_seconds = 3600
  }
  
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  
  labels = var.labels
  
  force_destroy = var.force_destroy
}

# Backups bucket - stores database and system backups
resource "google_storage_bucket" "backups" {
  name          = "${var.project_id}-legal-backups-${var.suffix}"
  location      = var.region
  storage_class = "COLDLINE" # Cost-effective for backups
  
  # Versioning for backup history
  versioning {
    enabled = true
  }
  
  # Lifecycle management for backups
  lifecycle_rule {
    condition {
      age = var.backup_retention_days
    }
    action {
      type = "Delete"
    }
  }
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }
  
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  
  labels = merge(var.labels, {
    purpose = "backups"
  })
  
  force_destroy = var.force_destroy
}

# Temporary processing bucket - for intermediate file processing
resource "google_storage_bucket" "temp_processing" {
  name          = "${var.project_id}-legal-temp-${var.suffix}"
  location      = var.region
  storage_class = "STANDARD"
  
  # Short lifecycle for temporary files
  lifecycle_rule {
    condition {
      age = 7 # Delete after 7 days
    }
    action {
      type = "Delete"
    }
  }
  
  lifecycle_rule {
    condition {
      age = 1 # Move to nearline after 1 day
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }
  
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  
  labels = merge(var.labels, {
    purpose = "temporary"
  })
  
  force_destroy = true # Always allow deletion of temp files
}

# Eventarc trigger for document uploads
resource "google_eventarc_trigger" "document_upload" {
  name     = "document-upload-trigger"
  location = var.region
  project  = var.project_id

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }

  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.documents.name
  }

  destination {
    cloud_run_service {
      service = "document-upload-service-${var.suffix}"
      region  = var.region
      path    = "/webhook/storage"
    }
  }

  service_account = google_service_account.eventarc.email

  depends_on = [
    google_project_service.apis,
    google_project_iam_member.eventarc_sa
  ]
}

# Service account for Eventarc
resource "google_service_account" "eventarc" {
  account_id   = "eventarc-sa-${var.suffix}"
  display_name = "Eventarc Service Account"
  description  = "Service account for Eventarc triggers"
}

# IAM binding for Eventarc service account
resource "google_project_iam_member" "eventarc_sa" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}

resource "google_project_iam_member" "eventarc_sa_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}

# IAM bindings for storage access
resource "google_storage_bucket_iam_member" "documents_read" {
  bucket = google_storage_bucket.documents.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:service-${data.google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "documents_write" {
  bucket = google_storage_bucket.documents.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:service-${data.google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "reports_write" {
  bucket = google_storage_bucket.reports.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:service-${data.google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "backups_write" {
  bucket = google_storage_bucket.backups.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:service-${data.google_project.project.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

# Data source for project information
data "google_project" "project" {
  project_id = var.project_id
}

# Notification configuration for bucket events
resource "google_storage_notification" "document_notification" {
  bucket         = google_storage_bucket.documents.name
  payload_format = "JSON_API_V1"
  topic          = var.pubsub_topic_document_uploaded
  event_types    = ["OBJECT_FINALIZE", "OBJECT_DELETE"]
  
  depends_on = [google_pubsub_topic_iam_member.publisher]
}

resource "google_pubsub_topic_iam_member" "publisher" {
  topic  = var.pubsub_topic_document_uploaded
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${data.google_project.project.number}@gs-project-accounts.iam.gserviceaccount.com"
}

# Outputs
output "document_bucket_name" {
  description = "Name of the documents bucket"
  value       = google_storage_bucket.documents.name
}

output "document_bucket_url" {
  description = "URL of the documents bucket"
  value       = google_storage_bucket.documents.url
}

output "reports_bucket_name" {
  description = "Name of the reports bucket"
  value       = google_storage_bucket.reports.name
}

output "reports_bucket_url" {
  description = "URL of the reports bucket"
  value       = google_storage_bucket.reports.url
}

output "backups_bucket_name" {
  description = "Name of the backups bucket"
  value       = google_storage_bucket.backups.name
}

output "temp_processing_bucket_name" {
  description = "Name of the temporary processing bucket"
  value       = google_storage_bucket.temp_processing.name
}