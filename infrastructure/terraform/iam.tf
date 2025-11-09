# IAM Configuration for Legal Case AI

# Service account for main API
resource "google_service_account" "main_api" {
  account_id   = "main-api-sa-${var.service_suffix}"
  display_name = "Main API Service Account"
  description  = "Service account for main API service"
}

# Service accounts for individual services
resource "google_service_account" "services" {
  for_each = var.services
  
  account_id   = "${each.key}-sa-${var.service_suffix}"
  display_name = "${title(replace(each.key, "-", " "))} Service Account"
  description  = "Service account for ${each.key} service"
}

# Firestore access for all services
resource "google_project_iam_member" "firestore_user" {
  for_each = var.services
  
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.services[each.key].email}"
}

# Cloud Storage access
resource "google_project_iam_member" "storage_object_admin" {
  for_each = var.services
  
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.services[each.key].email}"
}

# Pub/Sub access
resource "google_project_iam_member" "pubsub_editor" {
  for_each = var.services
  
  project = var.project_id
  role    = "roles/pubsub.editor"
  member  = "serviceAccount:${google_service_account.services[each.key].email}"
}

# Document AI access for extraction service
resource "google_project_iam_member" "documentai_user" {
  project = var.project_id
  role    = "roles/documentai.apiUser"
  member  = "serviceAccount:${google_service_account.services["text-extraction-service"].email}"
}

# Vertex AI access for analysis and AI agent services
resource "google_project_iam_member" "aiplatform_user" {
  for_each = toset(["case-analysis-service", "ai-agent-service"])
  
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.services[each.value].email}"
}

# Cloud Run invoker for internal service communication
resource "google_project_iam_member" "run_invoker" {
  for_each = var.services
  
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.services[each.key].email}"
}

# Cloud Logging access
resource "google_project_iam_member" "logging_writer" {
  for_each = var.services
  
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.services[each.key].email}"
}

# Cloud Monitoring access
resource "google_project_iam_member" "monitoring_writer" {
  for_each = var.services
  
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.services[each.key].email}"
}

# Cloud Trace access
resource "google_project_iam_member" "trace_agent" {
  for_each = var.services
  
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.services[each.key].email}"
}

# Secret Manager access
resource "google_project_iam_member" "secret_accessor" {
  for_each = var.services
  
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.services[each.key].email}"
}

# Cloud Build service account for deployment
resource "google_service_account" "cloud_build" {
  account_id   = "cloud-build-sa-${var.service_suffix}"
  display_name = "Cloud Build Service Account"
  description  = "Service account for Cloud Build deployment pipeline"
}

resource "google_project_iam_member" "cloud_build_editor" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.editor"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "cloud_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

resource "google_project_iam_member" "service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.cloud_build.email}"
}

# Custom role for enhanced service operations
resource "google_project_iam_custom_role" "legal_ai_service" {
  role_id     = "legalAiService"
  title       = "Legal AI Service Role"
  description = "Custom role for Legal AI services with specific permissions"
  
  permissions = [
    "firestore.documents.create",
    "firestore.documents.delete",
    "firestore.documents.get",
    "firestore.documents.list",
    "firestore.documents.update",
    "firestore.documents.write",
    "storage.objects.create",
    "storage.objects.delete",
    "storage.objects.get",
    "storage.objects.list",
    "storage.objects.update",
    "pubsub.topics.publish",
    "pubsub.subscriptions.consume",
    "pubsub.messages.ack",
    "secretmanager.versions.access",
    "logging.logEntries.create",
    "monitoring.timeSeries.create",
    "cloudtrace.traces.patch"
  ]
}

# Bind custom role to service accounts
resource "google_project_iam_member" "legal_ai_service_role" {
  for_each = var.services
  
  project = var.project_id
  role    = google_project_iam_custom_role.legal_ai_service.name
  member  = "serviceAccount:${google_service_account.services[each.key].email}"
}

# Workload Identity for GKE (if using Kubernetes in the future)
resource "google_service_account_iam_member" "workload_identity" {
  for_each = var.services
  
  service_account_id = google_service_account.services[each.key].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[legal-ai/${each.key}]"
}

# Firebase Admin SDK service account
resource "google_service_account" "firebase_admin" {
  account_id   = "firebase-admin-sa-${var.service_suffix}"
  display_name = "Firebase Admin Service Account"
  description  = "Service account for Firebase Admin SDK operations"
}

resource "google_project_iam_member" "firebase_admin" {
  project = var.project_id
  role    = "roles/firebase.admin"
  member  = "serviceAccount:${google_service_account.firebase_admin.email}"
}

# Output service account emails
output "service_account_emails" {
  description = "Email addresses of service accounts"
  value = {
    for name, sa in google_service_account.services :
    name => sa.email
  }
}

output "main_api_service_account" {
  description = "Main API service account email"
  value       = google_service_account.main_api.email
}

output "cloud_build_service_account" {
  description = "Cloud Build service account email"
  value       = google_service_account.cloud_build.email
}

output "firebase_admin_service_account" {
  description = "Firebase Admin service account email"
  value       = google_service_account.firebase_admin.email
}