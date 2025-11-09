# Variables for Legal Case AI Terraform Configuration

variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
  
  validation {
    condition     = length(var.project_id) > 0
    error_message = "Project ID must not be empty."
  }
}

variable "region" {
  description = "The Google Cloud region"
  type        = string
  default     = "us-central1"
  
  validation {
    condition = can(regex("^[a-z]+-[a-z]+[0-9]$", var.region))
    error_message = "Region must be a valid Google Cloud region."
  }
}

variable "zone" {
  description = "The Google Cloud zone"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "production"
  
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

# Secret variables
variable "internal_api_key" {
  description = "Internal API key for service-to-service communication"
  type        = string
  sensitive   = true
}

variable "firebase_config" {
  description = "Firebase configuration JSON"
  type        = string
  sensitive   = true
}

variable "sendgrid_api_key" {
  description = "SendGrid API key for email service"
  type        = string
  sensitive   = true
  default     = ""
}

variable "google_ai_api_key" {
  description = "Google AI API key for Gemini"
  type        = string
  sensitive   = true
}

# Service configuration
variable "min_instances" {
  description = "Minimum number of instances for Cloud Run services"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of instances for Cloud Run services"
  type        = number
  default     = 100
}

variable "cpu_limit" {
  description = "CPU limit for Cloud Run services"
  type        = string
  default     = "2"
}

variable "memory_limit" {
  description = "Memory limit for Cloud Run services"
  type        = string
  default     = "4Gi"
}

variable "concurrency" {
  description = "Maximum concurrent requests per instance"
  type        = number
  default     = 80
}

variable "timeout" {
  description = "Request timeout in seconds"
  type        = number
  default     = 300
}

# Storage configuration
variable "storage_class" {
  description = "Storage class for buckets"
  type        = string
  default     = "STANDARD"
  
  validation {
    condition = contains([
      "STANDARD", "NEARLINE", "COLDLINE", "ARCHIVE"
    ], var.storage_class)
    error_message = "Storage class must be STANDARD, NEARLINE, COLDLINE, or ARCHIVE."
  }
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 90
}

# Firestore configuration
variable "firestore_location" {
  description = "Firestore database location"
  type        = string
  default     = "nam5" # North America multi-region
}

# Monitoring and logging
variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
}

variable "enable_monitoring" {
  description = "Enable Cloud Monitoring"
  type        = bool
  default     = true
}

variable "enable_tracing" {
  description = "Enable Cloud Trace"
  type        = bool
  default     = true
}

# Security settings
variable "allow_unauthenticated" {
  description = "Allow unauthenticated access to services"
  type        = bool
  default     = false
}

variable "cors_origins" {
  description = "Allowed CORS origins"
  type        = list(string)
  default     = ["https://legalcaseai.com", "https://app.legalcaseai.com"]
}

# AI/ML Configuration
variable "enable_vertex_ai" {
  description = "Enable Vertex AI services"
  type        = bool
  default     = true
}

variable "enable_document_ai" {
  description = "Enable Document AI"
  type        = bool
  default     = true
}

variable "enable_discovery_engine" {
  description = "Enable Discovery Engine for search"
  type        = bool
  default     = true
}

# Resource limits
variable "storage_bucket_lifecycle_age" {
  description = "Age in days for storage lifecycle"
  type        = number
  default     = 365
}

variable "pubsub_message_retention" {
  description = "Pub/Sub message retention duration"
  type        = string
  default     = "604800s" # 7 days
}

# Development settings
variable "enable_debug_logging" {
  description = "Enable debug logging"
  type        = bool
  default     = false
}

variable "skip_delete_protection" {
  description = "Skip delete protection (for development)"
  type        = bool
  default     = false
}