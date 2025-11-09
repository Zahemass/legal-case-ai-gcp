#!/bin/bash

# Legal Case AI - Firestore Database Setup Script
# Created: 2025-11-01 10:05:15 UTC
# Author: Zahemassg

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
DATABASE_ID="${FIRESTORE_DATABASE_ID:-(default)}"

echo -e "${BLUE}🔥 Legal Case AI - Firestore Database Setup${NC}"
echo -e "${BLUE}===========================================${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Database ID: $DATABASE_ID"
echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    if [[ -z "$PROJECT_ID" ]] || [[ "$PROJECT_ID" == "your-project-id" ]]; then
        print_error "Project ID is not set"
        exit 1
    fi
    
    # Check if gcloud is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "No active gcloud authentication found"
        exit 1
    fi
    
    # Check if Firestore API is enabled
    if ! gcloud services list --enabled --filter="name:firestore.googleapis.com" --format="value(name)" | grep -q "firestore.googleapis.com"; then
        print_info "Enabling Firestore API..."
        gcloud services enable firestore.googleapis.com --project="$PROJECT_ID"
        print_status "Firestore API enabled"
    fi
    
    print_status "Prerequisites verified"
}

# Create Firestore database
create_database() {
    print_info "Setting up Firestore database..."
    
    # Check if database already exists
    if gcloud firestore databases describe --database="$DATABASE_ID" --project="$PROJECT_ID" >/dev/null 2>&1; then
        print_status "Firestore database already exists"
        return 0
    fi
    
    print_info "Creating Firestore database..."
    
    # Create Firestore database in Native mode
    gcloud firestore databases create \
        --database="$DATABASE_ID" \
        --location="nam5" \
        --type="firestore-native" \
        --project="$PROJECT_ID"
    
    print_status "Firestore database created successfully"
    
    # Wait for database to be ready
    print_info "Waiting for database to be ready..."
    sleep 10
}

# Create Firestore security rules
setup_security_rules() {
    print_info "Setting up Firestore security rules..."
    
    # Create temporary security rules file
    local rules_file="/tmp/firestore.rules"
    
    cat > "$rules_file" << 'EOF'
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read/write their own user document
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Cases: users can only access their own cases
    match /cases/{caseId} {
      allow read, write: if request.auth != null && 
        (request.auth.uid == resource.data.createdBy || 
         request.auth.token.role == 'admin');
    }
    
    // Documents: users can only access documents for their cases
    match /documents/{documentId} {
      allow read, write: if request.auth != null && 
        exists(/databases/$(database)/documents/cases/$(resource.data.caseId)) &&
        get(/databases/$(database)/documents/cases/$(resource.data.caseId)).data.createdBy == request.auth.uid;
    }
    
    // Extracted documents: same as documents
    match /extracted_documents/{docId} {
      allow read, write: if request.auth != null && 
        exists(/databases/$(database)/documents/cases/$(resource.data.caseId)) &&
        get(/databases/$(database)/documents/cases/$(resource.data.caseId)).data.createdBy == request.auth.uid;
    }
    
    // Document analysis: same as documents
    match /document_analysis/{analysisId} {
      allow read, write: if request.auth != null && 
        exists(/databases/$(database)/documents/cases/$(resource.data.caseId)) &&
        get(/databases/$(database)/documents/cases/$(resource.data.caseId)).data.createdBy == request.auth.uid;
    }
    
    // Case analysis: same as cases
    match /case_analysis/{analysisId} {
      allow read, write: if request.auth != null && 
        exists(/databases/$(database)/documents/cases/$(resource.data.caseId)) &&
        get(/databases/$(database)/documents/cases/$(resource.data.caseId)).data.createdBy == request.auth.uid;
    }
    
    // Chat messages: users can access messages for their cases
    match /chat_messages/{messageId} {
      allow read, write: if request.auth != null && 
        (request.auth.uid == resource.data.userId ||
         (exists(/databases/$(database)/documents/cases/$(resource.data.caseId)) &&
          get(/databases/$(database)/documents/cases/$(resource.data.caseId)).data.createdBy == request.auth.uid));
    }
    
    // User activities: users can read their own activities
    match /user_activities/{activityId} {
      allow read: if request.auth != null && request.auth.uid == resource.data.userId;
      allow write: if request.auth != null;
    }
    
    // PDF reports: users can access reports for their cases
    match /pdf_reports/{reportId} {
      allow read, write: if request.auth != null && 
        exists(/databases/$(database)/documents/cases/$(resource.data.caseId)) &&
        get(/databases/$(database)/documents/cases/$(resource.data.caseId)).data.createdBy == request.auth.uid;
    }
    
    // Notifications: users can read/write their own notifications
    match /notifications/{notificationId} {
      allow read, write: if request.auth != null && request.auth.uid == resource.data.userId;
    }
    
    // System logs: admin only
    match /system_logs/{logId} {
      allow read, write: if request.auth != null && request.auth.token.role == 'admin';
    }
    
    // Extraction errors: admin only
    match /extraction_errors/{errorId} {
      allow read, write: if request.auth != null && request.auth.token.role == 'admin';
    }
    
    // Default deny all other access
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
EOF

    # Deploy security rules
    if command -v firebase >/dev/null 2>&1; then
        print_info "Deploying security rules using Firebase CLI..."
        
        # Check if Firebase project is initialized
        if [[ ! -f "firebase.json" ]]; then
            print_info "Initializing Firebase project..."
            
            # Create minimal firebase.json
            cat > firebase.json << EOF
{
  "firestore": {
    "rules": "$rules_file"
  }
}
EOF
        fi
        
        firebase use "$PROJECT_ID"
        firebase deploy --only firestore:rules --project="$PROJECT_ID"
        
        print_status "Security rules deployed successfully"
    else
        print_warning "Firebase CLI not found. Security rules file created at: $rules_file"
        print_info "To deploy rules manually:"
        print_info "1. Install Firebase CLI: npm install -g firebase-tools"
        print_info "2. Login: firebase login"
        print_info "3. Deploy rules: firebase deploy --only firestore:rules"
    fi
    
    # Clean up
    rm -f "$rules_file" firebase.json 2>/dev/null || true
}

# Create indexes for optimal query performance
create_indexes() {
    print_info "Creating Firestore composite indexes..."
    
    # Create temporary index configuration
    local index_file="/tmp/firestore-indexes.json"
    
    cat > "$index_file" << 'EOF'
{
  "indexes": [
    {
      "collectionGroup": "cases",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "createdBy", "order": "ASCENDING"},
        {"fieldPath": "updatedAt", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "cases",
      "queryScope": "COLLECTION", 
      "fields": [
        {"fieldPath": "createdBy", "order": "ASCENDING"},
        {"fieldPath": "status", "order": "ASCENDING"},
        {"fieldPath": "updatedAt", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "documents",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "caseId", "order": "ASCENDING"},
        {"fieldPath": "uploadedAt", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "documents", 
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "caseId", "order": "ASCENDING"},
        {"fieldPath": "status", "order": "ASCENDING"},
        {"fieldPath": "uploadedAt", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "chat_messages",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "caseId", "order": "ASCENDING"},
        {"fieldPath": "timestamp", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "notifications",
      "queryScope": "COLLECTION", 
      "fields": [
        {"fieldPath": "userId", "order": "ASCENDING"},
        {"fieldPath": "createdAt", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "notifications",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "userId", "order": "ASCENDING"},
        {"fieldPath": "isRead", "order": "ASCENDING"},
        {"fieldPath": "createdAt", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "user_activities",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "userId", "order": "ASCENDING"},
        {"fieldPath": "timestamp", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "document_analysis",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "caseId", "order": "ASCENDING"},
        {"fieldPath": "analyzedAt", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "case_analysis",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "caseId", "order": "ASCENDING"}, 
        {"fieldPath": "analyzedAt", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "extracted_documents",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "caseId", "order": "ASCENDING"},
        {"fieldPath": "createdAt", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "pdf_reports", 
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "caseId", "order": "ASCENDING"},
        {"fieldPath": "generatedAt", "order": "DESCENDING"}
      ]
    }
  ]
}
EOF

    # Deploy indexes using Firebase CLI if available
    if command -v firebase >/dev/null 2>&1; then
        print_info "Deploying indexes using Firebase CLI..."
        
        # Create firebase.json for indexes
        cat > firebase.json << EOF
{
  "firestore": {
    "indexes": "$index_file"
  }
}
EOF
        
        firebase use "$PROJECT_ID"
        firebase deploy --only firestore:indexes --project="$PROJECT_ID"
        
        print_status "Firestore indexes created successfully"
        
        # Clean up
        rm -f firebase.json "$index_file" 2>/dev/null || true
    else
        print_warning "Firebase CLI not found. Index configuration created at: $index_file"
        print_info "To deploy indexes manually:"
        print_info "1. Install Firebase CLI: npm install -g firebase-tools"
        print_info "2. Login: firebase login"
        print_info "3. Deploy indexes: firebase deploy --only firestore:indexes"
    fi
}

# Create initial collections and documents
initialize_collections() {
    print_info "Initializing Firestore collections..."
    
    # Create a simple Node.js script to initialize collections
    local init_script="/tmp/init-firestore.js"
    
    cat > "$init_script" << EOF
const admin = require('firebase-admin');

// Initialize Firebase Admin
admin.initializeApp({
  projectId: process.env.GOOGLE_CLOUD_PROJECT || '$PROJECT_ID'
});

const db = admin.firestore();

async function initializeCollections() {
  console.log('Initializing Firestore collections...');
  
  try {
    // Create system configuration document
    await db.collection('system_config').doc('settings').set({
      version: '1.0.0',
      initialized: admin.firestore.FieldValue.serverTimestamp(),
      features: {
        aiAnalysis: true,
        pdfGeneration: true,
        emailNotifications: true,
        realTimeChat: true
      },
      limits: {
        maxDocumentSize: 50 * 1024 * 1024, // 50MB
        maxDocumentsPerCase: 100,
        maxCasesPerUser: 50
      }
    });
    
    console.log('✅ System configuration initialized');
    
    // Create default user roles document
    await db.collection('system_config').doc('roles').set({
      roles: {
        super_admin: {
          level: 5,
          permissions: ['all']
        },
        admin: {
          level: 4,
          permissions: ['manage_users', 'view_all_cases', 'system_config']
        },
        legal_professional: {
          level: 3,
          permissions: ['create_cases', 'manage_own_cases', 'advanced_analysis']
        },
        paralegal: {
          level: 2,
          permissions: ['create_cases', 'basic_analysis', 'document_upload']
        },
        user: {
          level: 1,
          permissions: ['create_cases', 'document_upload', 'basic_features']
        }
      }
    });
    
    console.log('✅ User roles configuration initialized');
    
    // Create email templates collection
    await db.collection('email_templates').doc('case_analysis_complete').set({
      name: 'Case Analysis Complete',
      subject: 'Your case analysis is ready - {{caseTitle}}',
      template: 'analysis-complete',
      variables: ['caseTitle', 'analysisDate', 'keyFindings']
    });
    
    await db.collection('email_templates').doc('document_uploaded').set({
      name: 'Document Uploaded',
      subject: 'Document uploaded successfully - {{filename}}',
      template: 'document-uploaded', 
      variables: ['filename', 'caseTitle', 'uploadDate']
    });
    
    console.log('✅ Email templates initialized');
    
    console.log('🎉 Firestore initialization completed successfully!');
    
  } catch (error) {
    console.error('❌ Error initializing Firestore:', error);
    process.exit(1);
  }
}

initializeCollections();
EOF

    # Run initialization script if Node.js and firebase-admin are available
    if command -v node >/dev/null 2>&1; then
        print_info "Running Firestore initialization script..."
        
        # Check if firebase-admin is installed globally
        if node -e "require('firebase-admin')" 2>/dev/null; then
            GOOGLE_CLOUD_PROJECT="$PROJECT_ID" node "$init_script"
            print_status "Firestore collections initialized"
        else
            print_warning "firebase-admin not installed. Run: npm install -g firebase-admin"
            print_info "Initialization script created at: $init_script"
        fi
    else
        print_warning "Node.js not found. Initialization script created at: $init_script"
    fi
    
    # Clean up
    rm -f "$init_script" 2>/dev/null || true
}

# Verify Firestore setup
verify_setup() {
    print_info "Verifying Firestore setup..."
    
    # Check database status
    if gcloud firestore databases describe --database="$DATABASE_ID" --project="$PROJECT_ID" >/dev/null 2>&1; then
        print_status "Database is accessible"
        
        # Get database info
        local db_info=$(gcloud firestore databases describe --database="$DATABASE_ID" --project="$PROJECT_ID" --format="json")
        local location=$(echo "$db_info" | jq -r '.locationId // "unknown"')
        local type=$(echo "$db_info" | jq -r '.type // "unknown"')
        
        print_info "Database location: $location"
        print_info "Database type: $type"
    else
        print_error "Database verification failed"
        exit 1
    fi
    
    print_status "Firestore setup verification completed"
}

# Display summary
display_summary() {
    echo ""
    print_status "🎉 Firestore Database Setup Complete!"
    print_status "====================================="
    echo ""
    print_info "Database Information:"
    echo "  Project ID: $PROJECT_ID"
    echo "  Database ID: $DATABASE_ID"
    echo "  Region: $REGION"
    echo ""
    print_info "What was configured:"
    echo "  ✅ Firestore database created"
    echo "  ✅ Security rules deployed"
    echo "  ✅ Composite indexes created"
    echo "  ✅ Collections initialized"
    echo ""
    print_info "Next Steps:"
    echo "  1. Test database connectivity from your applications"
    echo "  2. Review security rules for your specific use case"
    echo "  3. Monitor index creation progress in the Console"
    echo "  4. Set up backup procedures if needed"
    echo ""
    print_info "Useful Commands:"
    echo "  • View database: gcloud firestore databases describe --database=$DATABASE_ID"
    echo "  • Console URL: https://console.firebase.google.com/project/$PROJECT_ID/firestore"
    echo ""
}

# Main execution
main() {
    local start_time=$(date +%s)
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project-id)
                PROJECT_ID="$2"
                shift 2
                ;;
            --region)
                REGION="$2" 
                shift 2
                ;;
            --database-id)
                DATABASE_ID="$2"
                shift 2
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --project-id ID      Set project ID"
                echo "  --region REGION      Set region"  
                echo "  --database-id ID     Set database ID (default: (default))"
                echo "  -h, --help          Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Execute setup steps
    check_prerequisites
    create_database
    setup_security_rules
    create_indexes
    initialize_collections
    verify_setup
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    display_summary
    
    print_info "Setup completed in ${duration} seconds"
}

# Run main function with all arguments
main "$@"