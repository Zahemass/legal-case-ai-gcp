#!/bin/bash

# Legal Case AI - Enable Required Google Cloud APIs
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

echo -e "${BLUE}🔌 Legal Case AI - Enable Google Cloud APIs${NC}"
echo -e "${BLUE}===========================================${NC}"
echo "Project ID: $PROJECT_ID"
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

# Check if project is set
if [[ -z "$PROJECT_ID" ]] || [[ "$PROJECT_ID" == "your-project-id" ]]; then
    print_error "Project ID is not set. Please set GOOGLE_CLOUD_PROJECT or run 'gcloud config set project PROJECT_ID'"
    exit 1
fi

# Required APIs for Legal Case AI
declare -A REQUIRED_APIS=(
    # Core Infrastructure APIs
    ["cloudbuild.googleapis.com"]="Cloud Build API"
    ["run.googleapis.com"]="Cloud Run API"
    ["eventarc.googleapis.com"]="Eventarc API"
    ["pubsub.googleapis.com"]="Cloud Pub/Sub API"
    
    # Storage and Database APIs
    ["storage.googleapis.com"]="Cloud Storage API"
    ["firestore.googleapis.com"]="Cloud Firestore API"
    ["firebase.googleapis.com"]="Firebase Management API"
    
    # Container and Artifact APIs
    ["artifactregistry.googleapis.com"]="Artifact Registry API"
    ["containerregistry.googleapis.com"]="Container Registry API"
    
    # AI/ML APIs
    ["aiplatform.googleapis.com"]="Vertex AI API"
    ["documentai.googleapis.com"]="Document AI API"
    ["vision.googleapis.com"]="Cloud Vision API"
    ["translate.googleapis.com"]="Cloud Translation API"
    ["discoveryengine.googleapis.com"]="Discovery Engine API"
    ["generativelanguage.googleapis.com"]="Generative Language API"
    
    # Security and Identity APIs
    ["iam.googleapis.com"]="Identity and Access Management API"
    ["iamcredentials.googleapis.com"]="IAM Service Account Credentials API"
    ["secretmanager.googleapis.com"]="Secret Manager API"
    
    # Monitoring and Logging APIs
    ["logging.googleapis.com"]="Cloud Logging API"
    ["monitoring.googleapis.com"]="Cloud Monitoring API"
    ["cloudtrace.googleapis.com"]="Cloud Trace API"
    ["cloudprofiler.googleapis.com"]="Cloud Profiler API"
    ["clouderrorreporting.googleapis.com"]="Error Reporting API"
    
    # Networking and Compute APIs
    ["compute.googleapis.com"]="Compute Engine API"
    ["dns.googleapis.com"]="Cloud DNS API"
    ["servicenetworking.googleapis.com"]="Service Networking API"
    
    # Scheduler and Functions APIs  
    ["cloudscheduler.googleapis.com"]="Cloud Scheduler API"
    ["cloudfunctions.googleapis.com"]="Cloud Functions API"
    
    # Additional APIs
    ["serviceusage.googleapis.com"]="Service Usage API"
    ["cloudresourcemanager.googleapis.com"]="Cloud Resource Manager API"
    ["servicemanagement.googleapis.com"]="Service Management API"
    
    # Firebase specific APIs
    ["firebasehosting.googleapis.com"]="Firebase Hosting API"
    ["firebasestorage.googleapis.com"]="Firebase Storage API"
    
    # Email and Communication
    ["gmail.googleapis.com"]="Gmail API (optional for email integration)"
)

# Function to check if API is enabled
is_api_enabled() {
    local api="$1"
    gcloud services list --enabled --filter="name:$api" --format="value(name)" 2>/dev/null | grep -q "^$api$"
}

# Function to enable API with retry
enable_api_with_retry() {
    local api="$1"
    local description="$2"
    local max_attempts=3
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        print_info "Enabling $description ($api) - Attempt $attempt/$max_attempts"
        
        if gcloud services enable "$api" --project="$PROJECT_ID" 2>/dev/null; then
            print_status "$description enabled successfully"
            return 0
        else
            if [[ $attempt -eq $max_attempts ]]; then
                print_error "Failed to enable $description after $max_attempts attempts"
                return 1
            else
                print_warning "Attempt $attempt failed, retrying in 5 seconds..."
                sleep 5
                ((attempt++))
            fi
        fi
    done
}

# Function to enable APIs in batches
enable_apis_batch() {
    local batch_size=5
    local apis=("$@")
    local total=${#apis[@]}
    local processed=0
    
    print_info "Enabling $total APIs in batches of $batch_size..."
    
    while [[ $processed -lt $total ]]; do
        local batch_apis=()
        local batch_end=$((processed + batch_size))
        
        if [[ $batch_end -gt $total ]]; then
            batch_end=$total
        fi
        
        # Prepare batch
        for ((i=processed; i<batch_end; i++)); do
            batch_apis+=("${apis[$i]}")
        done
        
        # Enable batch
        print_info "Processing batch: ${batch_apis[*]}"
        
        if gcloud services enable "${batch_apis[@]}" --project="$PROJECT_ID" 2>/dev/null; then
            for api in "${batch_apis[@]}"; do
                print_status "${REQUIRED_APIS[$api]} enabled"
            done
        else
            print_warning "Batch enable failed, trying individually..."
            for api in "${batch_apis[@]}"; do
                enable_api_with_retry "$api" "${REQUIRED_APIS[$api]}"
            done
        fi
        
        processed=$batch_end
        
        # Small delay between batches
        if [[ $processed -lt $total ]]; then
            sleep 2
        fi
    done
}

# Main execution
main() {
    local start_time=$(date +%s)
    
    print_info "Checking current API status..."
    
    # Check which APIs are already enabled
    local enabled_apis=()
    local disabled_apis=()
    
    for api in "${!REQUIRED_APIS[@]}"; do
        if is_api_enabled "$api"; then
            enabled_apis+=("$api")
            print_status "${REQUIRED_APIS[$api]} already enabled"
        else
            disabled_apis+=("$api")
        fi
    done
    
    echo ""
    print_info "Summary: ${#enabled_apis[@]} APIs already enabled, ${#disabled_apis[@]} APIs need to be enabled"
    echo ""
    
    if [[ ${#disabled_apis[@]} -eq 0 ]]; then
        print_status "All required APIs are already enabled!"
        return 0
    fi
    
    print_info "Enabling ${#disabled_apis[@]} APIs..."
    
    # Try batch enable first (more efficient)
    print_info "Attempting batch enable..."
    
    if gcloud services enable "${disabled_apis[@]}" --project="$PROJECT_ID" 2>/dev/null; then
        print_status "All APIs enabled successfully in batch!"
    else
        print_warning "Batch enable failed, enabling individually..."
        enable_apis_batch "${disabled_apis[@]}"
    fi
    
    # Verify all APIs are enabled
    echo ""
    print_info "Verifying API status..."
    
    local failed_apis=()
    for api in "${!REQUIRED_APIS[@]}"; do
        if is_api_enabled "$api"; then
            print_status "${REQUIRED_APIS[$api]} ✓"
        else
            failed_apis+=("$api")
            print_error "${REQUIRED_APIS[$api]} ✗"
        fi
    done
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo ""
    if [[ ${#failed_apis[@]} -eq 0 ]]; then
        print_status "🎉 All APIs enabled successfully!"
        print_info "Total APIs enabled: ${#REQUIRED_APIS[@]}"
        print_info "Time taken: ${duration} seconds"
        
        echo ""
        print_info "Next steps:"
        echo "  • APIs may take a few minutes to propagate"
        echo "  • You can now proceed with infrastructure deployment"
        echo "  • Monitor API usage in Cloud Console: https://console.cloud.google.com/apis/dashboard?project=$PROJECT_ID"
        
    else
        print_error "Failed to enable ${#failed_apis[@]} APIs"
        print_warning "Failed APIs:"
        for api in "${failed_apis[@]}"; do
            echo "  - $api (${REQUIRED_APIS[$api]})"
        done
        
        echo ""
        print_info "You can try to enable failed APIs manually:"
        for api in "${failed_apis[@]}"; do
            echo "  gcloud services enable $api --project=$PROJECT_ID"
        done
        
        exit 1
    fi
}

# Run main function
main "$@"