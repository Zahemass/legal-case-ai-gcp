# Firestore Database Configuration

# Create Firestore database
resource "google_firestore_database" "main" {
  project                           = var.project_id
  name                             = "(default)"
  location_id                      = var.firestore_location
  type                            = "FIRESTORE_NATIVE"
  concurrency_mode                = "OPTIMISTIC"
  app_engine_integration_mode     = "DISABLED"
  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_ENABLED"
  delete_protection_state         = var.skip_delete_protection ? "DELETE_PROTECTION_DISABLED" : "DELETE_PROTECTION_ENABLED"

  depends_on = [google_project_service.apis]
}

# Create Firestore indexes for efficient queries
resource "google_firestore_index" "cases_user_updated" {
  project    = var.project_id
  database   = google_firestore_database.main.name
  collection = "cases"

  fields {
    field_path = "createdBy"
    order      = "ASCENDING"
  }

  fields {
    field_path = "updatedAt"
    order      = "DESCENDING"
  }

  fields {
    field_path = "status"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "documents_case_uploaded" {
  project    = var.project_id
  database   = google_firestore_database.main.name
  collection = "documents"

  fields {
    field_path = "caseId"
    order      = "ASCENDING"
  }

  fields {
    field_path = "uploadedAt"
    order      = "DESCENDING"
  }

  fields {
    field_path = "status"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "chat_messages_case_timestamp" {
  project    = var.project_id
  database   = google_firestore_database.main.name
  collection = "chat_messages"

  fields {
    field_path = "caseId"
    order      = "ASCENDING"
  }

  fields {
    field_path = "timestamp"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "notifications_user_created" {
  project    = var.project_id
  database   = google_firestore_database.main.name
  collection = "notifications"

  fields {
    field_path = "userId"
    order      = "ASCENDING"
  }

  fields {
    field_path = "createdAt"
    order      = "DESCENDING"
  }

  fields {
    field_path = "isRead"
    order      = "ASCENDING"
  }
}

resource "google_firestore_index" "user_activities_user_timestamp" {
  project    = var.project_id
  database   = google_firestore_database.main.name
  collection = "user_activities"

  fields {
    field_path = "userId"
    order      = "ASCENDING"
  }

  fields {
    field_path = "timestamp"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "document_analysis_case_analyzed" {
  project    = var.project_id
  database   = google_firestore_database.main.name
  collection = "document_analysis"

  fields {
    field_path = "caseId"
    order      = "ASCENDING"
  }

  fields {
    field_path = "analyzedAt"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "case_analysis_case_analyzed" {
  project    = var.project_id
  database   = google_firestore_database.main.name
  collection = "case_analysis"

  fields {
    field_path = "caseId"
    order      = "ASCENDING"
  }

  fields {
    field_path = "analyzedAt"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "extracted_documents_case_created" {
  project    = var.project_id
  database   = google_firestore_database.main.name
  collection = "extracted_documents"

  fields {
    field_path = "caseId"
    order      = "ASCENDING"
  }

  fields {
    field_path = "createdAt"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "pdf_reports_case_generated" {
  project    = var.project_id
  database   = google_firestore_database.main.name
  collection = "pdf_reports"

  fields {
    field_path = "caseId"
    order      = "ASCENDING"
  }

  fields {
    field_path = "generatedAt"
    order      = "DESCENDING"
  }
}

# Create Firestore security rules
resource "google_firestore_document" "security_rules" {
  project     = var.project_id
  database    = google_firestore_database.main.name
  collection  = "security_rules"
  document_id = "rules"

  fields = jsonencode({
    rules = {
      stringValue = file("${path.module}/firestore-security-rules.txt")
    }
    version = {
      stringValue = "1.0"
    }
    updated = {
      timestampValue = timestamp()
    }
  })
}

# Output Firestore information
output "database_name" {
  description = "Firestore database name"
  value       = google_firestore_database.main.name
}

output "database_location" {
  description = "Firestore database location"
  value       = google_firestore_database.main.location_id
}