#!/bin/bash

# Legal Case AI - GCP Project Setup Script
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
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-project-id}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
ZONE="${GOOGLE_CLOUD_ZONE:-us-central1-a}"
BILLING_ACCOUNT="${BILLING_ACCOUNT_ID:-}"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}🔧 Legal Case AI - GCP Project Setup${NC}"
echo -e "${BLUE}====================================${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Zone: $ZONE"
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

# Check if gcloud is installed and authenticated
check_gcloud() {
    print_info "Checking gcloud configuration..."
    
    if ! command -v gcloud >/dev/null 2>&1; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "No active gcloud authentication found."
        print_info "Please run: gcloud auth login"
        exit 1
    fi
    
    # Get current project
    local current_project=$(gcloud config get-value project 2>/dev/null || echo "")
    
    if [[ -z "$current_project" ]] || [[ "$current_project" != "$PROJECT_ID" ]]; then
        print_info "Setting project to $PROJECT_ID"
        gcloud config set project "$PROJECT_ID"
    fi
    
    print_status "gcloud configuration verified"
}

# Create or verify project
setup_project() {
    print_info "Setting up GCP project..."
    
    # Check if project exists
    if gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
        print_status "Project $PROJECT_ID already exists"
    else
        print_info "Creating project $PROJECT_ID..."
        
        if [[ -n "$BILLING_ACCOUNT" ]]; then
            gcloud projects create "$PROJECT_ID" \
                --name="Legal Case AI" \
                --labels="environment=production,project=legal-case-ai,created-by=zahemassg"
            
            # Link billing account
            gcloud billing projects link "$PROJECT_ID" \
                --billing-account="$BILLING_ACCOUNT"
                
            print_status "Project created and billing linked"
        else
            gcloud projects create "$PROJECT_ID" \
                --name="Legal Case AI" \
                --labels="environment=production,project=legal-case-ai,created-by=zahemassg"
                
            print_warning "Project created but no billing account linked"
            print_warning "Please link a billing account: gcloud billing projects link $PROJECT_ID --billing-account=YOUR_BILLING_ACCOUNT"
        fi
    fi
    
    # Set current project
    gcloud config set project "$PROJECT_ID"
    
    print_status "Project setup completed"
}

# Set default region and zone
set_defaults() {
    print_info "Setting default region and zone..."
    
    gcloud config set compute/region "$REGION"
    gcloud config set compute/zone "$ZONE"
    gcloud config set run/region "$REGION"
    gcloud config set functions/region "$REGION"
    gcloud config set artifacts/location "$REGION"
    
    print_status "Default locations configured"
}

# Enable required APIs
enable_apis() {
    print_info "Enabling required Google Cloud APIs..."
    
    bash "$SCRIPT_DIR/enable-apis.sh"
    
    print_status "APIs enabled successfully"
}

# Create Artifact Registry
setup_artifact_registry() {
    print_info "Setting up Artifact Registry..."
    
    local repository_name="legal-case-ai-images"
    
    # Check if repository exists
    if gcloud artifacts repositories describe "$repository_name" --location="$REGION" >/dev/null 2>&1; then
        print_status "Artifact Registry repository already exists"
    else
        print_info "Creating Artifact Registry repository..."
        
        gcloud artifacts repositories create "$repository_name" \
            --repository-format=docker \
            --location="$REGION" \
            --description="Container images for Legal Case AI services" \
            --labels="project=legal-case-ai,environment=production"
        
        print_status "Artifact Registry repository created"
    fi
    
    # Configure Docker authentication
    gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
    
    print_status "Artifact Registry setup completed"
}

# Setup Cloud Storage for Terraform state
setup_terraform_state_bucket() {
    print_info "Setting up Terraform state bucket..."
    
    local bucket_name="${PROJECT_ID}-terraform-state"
    
    # Check if bucket exists
    if gsutil ls -b "gs://$bucket_name" >/dev/null 2>&1; then
        print_status "Terraform state bucket already exists"
    else
        print_info "Creating Terraform state bucket..."
        
        gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$bucket_name"
        
        # Enable versioning
        gsutil versioning set on "gs://$bucket_name"
        
        # Set lifecycle policy for old versions
        cat > /tmp/lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {
          "type": "Delete"
        },
        "condition": {
          "age": 30,
          "isLive": false
        }
      }
    ]
  }
}
EOF
        
        gsutil lifecycle set /tmp/lifecycle.json "gs://$bucket_name"
        rm /tmp/lifecycle.json
        
        print_status "Terraform state bucket created"
    fi
}

# Setup Firebase (if not already done)
setup_firebase() {
    print_info "Checking Firebase setup..."
    
    # Check if Firebase is already enabled
    if gcloud firebase projects list --filter="projectId:$PROJECT_ID" --format="value(projectId)" | grep -q "$PROJECT_ID"; then
        print_status "Firebase is already enabled for this project"
    else
        print_info "Enabling Firebase for project..."
        
        # Add Firebase to project
        gcloud firebase projects addfirebase "$PROJECT_ID"
        
        print_status "Firebase enabled"
    fi
    
    # Check if Firestore is enabled
    if gcloud firestore databases describe --database="(default)" >/dev/null 2>&1; then
        print_status "Firestore database already exists"
    else
        print_warning "Firestore database not found. It will be created during Terraform deployment."
    fi
}

# Setup IAM service accounts
setup_service_accounts() {
    print_info "Setting up service accounts..."
    
    # Terraform service account
    local terraform_sa="terraform-sa@${PROJECT_ID}.iam.gserviceaccount.com"
    
    if gcloud iam service-accounts describe "$terraform_sa" >/dev/null 2>&1; then
        print_status "Terraform service account already exists"
    else
        print_info "Creating Terraform service account..."
        
        gcloud iam service-accounts create terraform-sa \
            --display-name="Terraform Service Account" \
            --description="Service account for Terraform deployments"
        
        # Grant necessary roles
        local roles=(
            "roles/owner"
            "roles/iam.serviceAccountAdmin"
            "roles/resourcemanager.projectIamAdmin"
        )
        
        for role in "${roles[@]}"; do
            gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:$terraform_sa" \
                --role="$role"
        done
        
        print_status "Terraform service account created and configured"
    fi
    
    # Cloud Build service account
    local cloudbuild_sa="${PROJECT_ID}@cloudbuild.gserviceaccount.com"
    
    # Grant additional roles to Cloud Build service account
    local cloudbuild_roles=(
        "roles/run.admin"
        "roles/iam.serviceAccountUser"
        "roles/artifactregistry.admin"
    )
    
    for role in "${cloudbuild_roles[@]}"; do
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$cloudbuild_sa" \
            --role="$role" \
            --quiet
    done
    
    print_status "Service accounts configured"
}

# Create Cloud Build trigger (optional)
setup_cloud_build() {
    print_info "Setting up Cloud Build..."
    
    # Check if Cloud Build API is enabled (should be from enable_apis)
    local trigger_name="legal-case-ai-deploy"
    
    # Check if trigger exists
    if gcloud builds triggers describe "$trigger_name" >/dev/null 2>&1; then
        print_status "Cloud Build trigger already exists"
    else
        print_info "You can manually create a Cloud Build trigger later for CI/CD"
        print_info "Trigger name suggestion: $trigger_name"
    fi
    
    print_status "Cloud Build setup completed"
}

# Setup monitoring and alerting
setup_monitoring() {
    print_info "Setting up monitoring..."
    
    # Create notification channels (optional)
    print_info "Monitoring APIs enabled. You can configure alerting policies in the Console."
    print_info "Recommended: Set up alerts for service health, error rates, and resource usage"
    
    print_status "Monitoring setup completed"
}

# Verify setup
verify_setup() {
    print_info "Verifying GCP setup..."
    
    # Check project
    local current_project=$(gcloud config get-value project)
    if [[ "$current_project" != "$PROJECT_ID" ]]; then
        print_error "Project configuration mismatch"
        exit 1
    fi
    
    # Check APIs (sample)
    local required_apis=(
        "cloudbuild.googleapis.com"
        "run.googleapis.com"
        "firestore.googleapis.com"
    )
    
    for api in "${required_apis[@]}"; do
        if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            print_status "$api is enabled"
        else
            print_warning "$api may not be enabled"
        fi
    done
    
    # Check Artifact Registry
    if gcloud artifacts repositories list --location="$REGION" --format="value(name)" | grep -q "legal-case-ai-images"; then
        print_status "Artifact Registry repository exists"
    else
        print_warning "Artifact Registry repository not found"
    fi
    
    print_status "Setup verification completed"
}

# Display summary
display_summary() {
    echo ""
    echo -e "${GREEN}🎉 GCP Project Setup Complete!${NC}"
    echo -e "${GREEN}==============================${NC}"
    echo ""
    echo -e "${BLUE}Project Information:${NC}"
    echo "  Project ID: $PROJECT_ID"
    echo "  Region: $REGION"
    echo "  Zone: $ZONE"
    echo ""
    echo -e "${BLUE}What was configured:${NC}"
    echo "  ✅ Project created/verified"
    echo "  ✅ Required APIs enabled"
    echo "  ✅ Artifact Registry repository"
    echo "  ✅ Terraform state bucket"
    echo "  ✅ Firebase project"
    echo "  ✅ Service accounts"
    echo "  ✅ Default regions set"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Run: bash infrastructure/scripts/deploy-all.sh"
    echo "  2. Or deploy infrastructure: cd infrastructure/terraform && terraform init && terraform apply"
    echo "  3. Monitor deployment in Cloud Console: https://console.cloud.google.com/home/dashboard?project=$PROJECT_ID"
    echo ""
    echo -e "${YELLOW}Important:${NC}"
    echo "  • Make sure billing is enabled for the project"
    echo "  • Update API keys in terraform.tfvars before deploying"
    echo "  • Review IAM permissions for production use"
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
            --zone)
                ZONE="$2"
                shift 2
                ;;
            --billing-account)
                BILLING_ACCOUNT="$2"
                shift 2
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --project-id ID         Set project ID"
                echo "  --region REGION         Set region (default: us-central1)"
                echo "  --zone ZONE            Set zone (default: us-central1-a)"
                echo "  --billing-account ID    Set billing account ID"
                echo "  -h, --help             Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Validate project ID
    if [[ "$PROJECT_ID" == "your-project-id" ]]; then
        print_error "Please set a valid project ID"
        print_info "Usage: $0 --project-id YOUR_PROJECT_ID"
        exit 1
    fi
    
    # Execute setup steps
    check_gcloud
    setup_project
    set_defaults
    enable_apis
    setup_artifact_registry
    setup_terraform_state_bucket
    setup_firebase
    setup_service_accounts
    setup_cloud_build
    setup_monitoring
    verify_setup
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    display_summary
    
    print_info "Setup completed in ${duration} seconds"
}

# Run main function with all arguments
main "$@"