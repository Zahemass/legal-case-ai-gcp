# Cloud Run Services Configuration

# Service definitions with their specific configurations
locals {
  service_configs = {
    main-api = {
      image         = "${var.artifact_registry}/${local.services.main_api}:latest"
      port          = 3000
      cpu           = "2"
      memory        = "4Gi"
      min_instances = var.environment == "production" ? 1 : 0
      max_instances = 20
      timeout       = 300
      concurrency   = 80
    }
    
    document-upload-service = {
      image         = "${var.artifact_registry}/${local.services.document_upload}:latest"
      port          = 8080
      cpu           = "2"
      memory        = "4Gi"
      min_instances = 0
      max_instances = 10
      timeout       = 600 # 10 minutes for large uploads
      concurrency   = 20
    }
    
    text-extraction-service = {
      image         = "${var.artifact_registry}/${local.services.extraction}:latest"
      port          = 8080
      cpu           = "4"
      memory        = "8Gi"
      min_instances = 0
      max_instances = 5
      timeout       = 900 # 15 minutes for extraction
      concurrency   = 5
    }
    
    case-analysis-service = {
      image         = "${var.artifact_registry}/${local.services.analysis}:latest"
      port          = 8080
      cpu           = "4"
      memory        = "8Gi"
      min_instances = 0
      max_instances = 3
      timeout       = 1800 # 30 minutes for analysis
      concurrency   = 2
    }
    
    ai-agent-service = {
      image         = "${var.artifact_registry}/${local.services.ai_agent}:latest"
      port          = 8080
      cpu           = "2"
      memory        = "4Gi"
      min_instances = var.environment == "production" ? 1 : 0
      max_instances = 10
      timeout       = 300
      concurrency   = 50
    }
    
    pdf-generator-service = {
      image         = "${var.artifact_registry}/${local.services.pdf_generator}:latest"
      port          = 8080
      cpu           = "2"
      memory        = "4Gi"
      min_instances = 0
      max_instances = 5
      timeout       = 600 # 10 minutes for PDF generation
      concurrency   = 10
    }
    
    email-service = {
      image         = "${var.artifact_registry}/${local.services.email_service}:latest"
      port          = 8080
      cpu           = "1"
      memory        = "2Gi"
      min_instances = 0
      max_instances = 10
      timeout       = 60
      concurrency   = 100
    }
  }
}

# Create Cloud Run services
resource "google_cloud_run_v2_service" "services" {
  for_each = local.service_configs
  
  name     = "${each.key}-${var.suffix}"
  location = var.region
  
  deletion_protection = var.environment == "production" ? true : false
  
  template {
    # Scaling configuration
    scaling {
      min_instance_count = each.value.min_instances
      max_instance_count = each.value.max_instances
    }
    
    # Service account
    service_account = google_service_account.cloud_run[each.key].email
    
    # Timeout
    timeout = "${each.value.timeout}s"
    
    containers {
      image = each.value.image
      
      # Resource limits
      resources {
        limits = {
          cpu    = each.value.cpu
          memory = each.value.memory
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }
      
      # Port configuration
      ports {
        container_port = each.value.port
        name          = "http1"
      }
      
      # Environment variables
      dynamic "env" {
        for_each = local.common_env_vars
        content {
          name  = env.key
          value = env.value
        }
      }
      
      # Service-specific environment variables
      dynamic "env" {
        for_each = local.service_env_vars[each.key]
        content {
          name  = env.key
          value = env.value
        }
      }
      
      # Secret environment variables
      dynamic "env" {
        for_each = local.secret_env_vars
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.secrets[env.value.secret].secret_id
              version = "latest"
            }
          }
        }
      }
      
      # Health check
      startup_probe {
        http_get {
          path = "/health"
          port = each.value.port
          http_headers {
            name  = "User-Agent"
            value = "GoogleHC/1.0"
          }
        }
        initial_delay_seconds = 10
        timeout_seconds      = 5
        period_seconds       = 5
        failure_threshold    = 3
      }
      
      liveness_probe {
        http_get {
          path = "/health"
          port = each.value.port
        }
        initial_delay_seconds = 30
        timeout_seconds      = 5
        period_seconds       = 10
        failure_threshold    = 3
      }
    }
    
    # Max concurrent requests per instance
    max_instance_request_concurrency = each.value.concurrency
    
    # Execution environment
    execution_environment = "EXECUTION_ENVIRONMENT_GEN2"
    
    # Labels
    labels = merge(var.labels, {
      service = each.key
    })
  }
  
  # Traffic configuration
  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
  
  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_version.secrets
  ]
}

# Service accounts for Cloud Run services
resource "google_service_account" "cloud_run" {
  for_each = local.service_configs
  
  account_id   = "${each.key}-sa-${var.suffix}"
  display_name = "Service Account for ${each.key}"
  description  = "Service account for Cloud Run service ${each.key}"
}

# IAM policy for Cloud Run services
resource "google_cloud_run_service_iam_member" "public_access" {
  for_each = var.allow_unauthenticated ? local.service_configs : {}
  
  service  = google_cloud_run_v2_service.services[each.key].name
  location = google_cloud_run_v2_service.services[each.key].location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Common environment variables for all services
locals {
  common_env_vars = {
    GOOGLE_CLOUD_PROJECT = var.project_id
    NODE_ENV            = var.environment == "development" ? "development" : "production"
    PORT                = "8080"
    ENVIRONMENT         = var.environment
    STORAGE_BUCKET      = module.storage.document_bucket_name
    REPORTS_BUCKET      = module.storage.reports_bucket_name
    BACKUPS_BUCKET      = module.storage.backups_bucket_name
    LOG_LEVEL          = var.enable_debug_logging ? "debug" : "info"
  }
  
  # Service-specific environment variables
  service_env_vars = {
    main-api = {
      PORT = "3000"
      CORS_ORIGINS = join(",", var.cors_origins)
    }
    
    document-upload-service = {
      MAX_FILE_SIZE = "50MB"
      ALLOWED_MIME_TYPES = "application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
    }
    
    text-extraction-service = {
      MAX_PAGES_PER_DOCUMENT = "100"
      EXTRACTION_TIMEOUT = "900"
    }
    
    case-analysis-service = {
      ANALYSIS_TIMEOUT = "1800"
      MAX_DOCUMENTS_PER_ANALYSIS = "50"
    }
    
    ai-agent-service = {
      MAX_CONCURRENT_CHATS = "100"
      WEBSOCKET_ENABLED = "true"
    }
    
    pdf-generator-service = {
      REPORT_TIMEOUT = "600"
      MAX_REPORT_SIZE = "50MB"
    }
    
    email-service = {
      EMAIL_PROVIDER = "sendgrid"
      FROM_EMAIL = "noreply@legalcaseai.com"
      FROM_NAME = "Legal Case AI"
    }
  }
  
  # Secret environment variables
  secret_env_vars = {
    INTERNAL_API_KEY = {
      secret = "internal-api-key"
    }
    FIREBASE_SERVICE_ACCOUNT_KEY = {
      secret = "firebase-service-account"
    }
    GOOGLE_AI_API_KEY = {
      secret = "google-ai-api-key"
    }
    SENDGRID_API_KEY = {
      secret = "sendgrid-api-key"
    }
  }
}

# Create secrets in Secret Manager
resource "google_secret_manager_secret" "secrets" {
  for_each = {
    internal-api-key        = "Internal API key for service communication"
    firebase-service-account = "Firebase service account key"
    google-ai-api-key      = "Google AI API key for Gemini"
    sendgrid-api-key       = "SendGrid API key for email service"
  }
  
  secret_id = each.key
  
  labels = var.labels
  
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
}

# Create secret versions
resource "google_secret_manager_secret_version" "secrets" {
  for_each = {
    internal-api-key        = var.internal_api_key
    firebase-service-account = var.firebase_config
    google-ai-api-key      = var.google_ai_api_key
    sendgrid-api-key       = var.sendgrid_api_key
  }
  
  secret      = google_secret_manager_secret.secrets[each.key].id
  secret_data = each.value
}

# Grant access to secrets for service accounts
resource "google_secret_manager_secret_iam_member" "secret_access" {
  for_each = {
    for pair in setproduct(keys(local.service_configs), keys(google_secret_manager_secret.secrets)) :
    "${pair[0]}-${pair[1]}" => {
      service = pair[0]
      secret  = pair[1]
    }
  }
  
  secret_id = google_secret_manager_secret.secrets[each.value.secret].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run[each.value.service].email}"
}

# Load balancer for main API (optional)
resource "google_compute_global_address" "main_api_ip" {
  count = var.environment == "production" ? 1 : 0
  name  = "main-api-ip-${var.suffix}"
}

resource "google_compute_managed_ssl_certificate" "main_api_ssl" {
  count = var.environment == "production" ? 1 : 0
  name  = "main-api-ssl-${var.suffix}"

  managed {
    domains = ["api.legalcaseai.com"] # Update with your domain
  }
}

# Output service URLs
output "service_urls" {
  description = "URLs of the deployed Cloud Run services"
  value = {
    for name, service in google_cloud_run_v2_service.services :
    name => service.uri
  }
}

output "service_names" {
  description = "Names of the deployed Cloud Run services"
  value = {
    for name, service in google_cloud_run_v2_service.services :
    name => service.name
  }
}