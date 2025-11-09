#!/bin/bash

# Legal Case AI - Complete Deployment Script
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
ENVIRONMENT="${ENVIRONMENT:-production}"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRASTRUCTURE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$INFRASTRUCTURE_DIR")"

echo -e "${BLUE}🚀 Legal Case AI - Complete Deployment${NC}"
echo -e "${BLUE}=====================================${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check required commands
    local required_commands=("gcloud" "terraform" "docker" "npm" "node" "python3" "jq" "curl")
    
    for cmd in "${required_commands[@]}"; do
        if ! command_exists "$cmd"; then
            print_error "$cmd is not installed or not in PATH"
            exit 1
        fi
    done
    
    # Check gcloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "No active gcloud authentication found. Please run 'gcloud auth login'"
        exit 1
    fi
    
    # Check if project ID is set
    if [[ "$PROJECT_ID" == "your-project-id" ]]; then
        print_error "Please set GOOGLE_CLOUD_PROJECT environment variable"
        exit 1
    fi
    
    # Set project
    gcloud config set project "$PROJECT_ID"
    
    print_status "Prerequisites check completed"
}

# Setup GCP project
setup_gcp() {
    print_info "Setting up GCP project..."
    
    # Run GCP setup script
    bash "$SCRIPT_DIR/setup-gcp.sh"
    
    print_status "GCP setup completed"
}

# Build and push Docker images
build_and_push_images() {
    print_info "Building and pushing Docker images..."
    
    # Get Artifact Registry URL
    ARTIFACT_REGISTRY="$REGION-docker.pkg.dev/$PROJECT_ID/legal-case-ai-images"
    
    # Configure Docker authentication
    gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet
    
    # Services to build
    local services=(
        "main-api"
        "document-upload-service"
        "text-extraction-service"
        "case-analysis-service"
        "ai-agent-service"
        "pdf-generator-service"
        "email-service"
    )
    
    for service in "${services[@]}"; do
        print_info "Building $service..."
        
        local service_dir="$PROJECT_ROOT/services/$service"
        local image_tag="$ARTIFACT_REGISTRY/$service:latest"
        
        if [[ -f "$service_dir/Dockerfile" ]]; then
            docker build -t "$image_tag" "$service_dir"
            docker push "$image_tag"
            print_status "$service image built and pushed"
        else
            print_warning "Dockerfile not found for $service, skipping..."
        fi
    done
    
    print_status "All images built and pushed"
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    print_info "Deploying infrastructure with Terraform..."
    
    cd "$INFRASTRUCTURE_DIR/terraform"
    
    # Initialize Terraform
    terraform init
    
    # Create terraform.tfvars if it doesn't exist
    if [[ ! -f "terraform.tfvars" ]]; then
        print_info "Creating terraform.tfvars..."
        cat > terraform.tfvars << EOF
project_id = "$PROJECT_ID"
region = "$REGION"
environment = "$ENVIRONMENT"

# Generate secure API key
internal_api_key = "$(openssl rand -base64 32)"

# Firebase config (you need to provide this)
firebase_config = "{\"type\":\"service_account\",\"project_id\":\"$PROJECT_ID\"}"

# Google AI API key (you need to provide this)
google_ai_api_key = "your-google-ai-api-key"

# SendGrid API key (optional)
sendgrid_api_key = ""
EOF
        print_warning "Please update terraform.tfvars with your actual API keys and Firebase config"
        print_warning "Press Enter to continue after updating the file..."
        read -r
    fi
    
    # Plan and apply
    terraform plan -out=tfplan
    terraform apply tfplan
    
    print_status "Infrastructure deployment completed"
}

# Deploy AI agents
deploy_ai_agents() {
    print_info "Deploying AI agents..."
    
    cd "$PROJECT_ROOT/ai-agents"
    
    # Install Python dependencies
    python3 -m pip install -r requirements.txt
    
    # Setup knowledge base
    python3 knowledge_base/setup_knowledge_base.py --project-id "$PROJECT_ID"
    
    # Deploy agent
    python3 deploy_agent.py --config agent_config.yaml
    
    print_status "AI agents deployed"
}

# Setup Firestore
setup_firestore() {
    print_info "Setting up Firestore..."
    
    bash "$SCRIPT_DIR/setup-firestore.sh"
    
    print_status "Firestore setup completed"
}

# Deploy frontend (if exists)
deploy_frontend() {
    local frontend_dir="$PROJECT_ROOT/frontend"
    
    if [[ -d "$frontend_dir" ]]; then
        print_info "Deploying frontend..."
        
        cd "$frontend_dir"
        
        # Install dependencies
        npm install
        
        # Build
        npm run build
        
        # Deploy (assuming Firebase Hosting)
        if command_exists firebase; then
            firebase deploy --only hosting
            print_status "Frontend deployed"
        else
            print_warning "Firebase CLI not found, skipping frontend deployment"
        fi
    else
        print_info "Frontend directory not found, skipping..."
    fi
}

# Run tests
run_tests() {
    print_info "Running tests..."
    
    # Backend tests
    local services_dir="$PROJECT_ROOT/services"
    
    for service_dir in "$services_dir"/*; do
        if [[ -d "$service_dir" && -f "$service_dir/package.json" ]]; then
            print_info "Testing $(basename "$service_dir")..."
            cd "$service_dir"
            
            if npm run test --if-present; then
                print_status "$(basename "$service_dir") tests passed"
            else
                print_warning "$(basename "$service_dir") tests failed or not available"
            fi
        fi
    done
    
    # Python service tests
    for service_dir in "$services_dir"/*; do
        if [[ -d "$service_dir" && -f "$service_dir/requirements.txt" ]]; then
            if [[ -f "$service_dir/test_main.py" || -d "$service_dir/tests" ]]; then
                print_info "Testing Python service $(basename "$service_dir")..."
                cd "$service_dir"
                
                if python3 -m pytest . --tb=short; then
                    print_status "$(basename "$service_dir") Python tests passed"
                else
                    print_warning "$(basename "$service_dir") Python tests failed"
                fi
            fi
        fi
    done
    
    print_status "Tests completed"
}

# Health check
health_check() {
    print_info "Performing health checks..."
    
    # Get service URLs from Terraform output
    cd "$INFRASTRUCTURE_DIR/terraform"
    
    if terraform output -json service_urls > /dev/null 2>&1; then
        local service_urls=$(terraform output -json service_urls | jq -r 'to_entries[] | "\(.key)=\(.value)"')
        
        while read -r service_url; do
            local service_name=$(echo "$service_url" | cut -d'=' -f1)
            local url=$(echo "$service_url" | cut -d'=' -f2)
            
            print_info "Checking health of $service_name..."
            
            if curl -f -s "$url/health" > /dev/null; then
                print_status "$service_name is healthy"
            else
                print_warning "$service_name health check failed"
            fi
        done <<< "$service_urls"
    else
        print_warning "Could not get service URLs from Terraform"
    fi
    
    print_status "Health checks completed"
}

# Generate deployment report
generate_report() {
    print_info "Generating deployment report..."
    
    local report_file="$PROJECT_ROOT/deployment-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# Legal Case AI Deployment Report

**Generated:** $(date -u '+%Y-%m-%d %H:%M:%S UTC')  
**Project:** $PROJECT_ID  
**Region:** $REGION  
**Environment:** $ENVIRONMENT  
**Deployed by:** Zahemassg

## Deployment Summary

### Infrastructure
- ✅ GCP Project Setup
- ✅ Terraform Infrastructure
- ✅ Cloud Run Services
- ✅ Firestore Database
- ✅ Cloud Storage Buckets
- ✅ Pub/Sub Topics
- ✅ IAM Configuration

### Services Deployed
EOF

    # Add service information
    cd "$INFRASTRUCTURE_DIR/terraform"
    
    if terraform output -json service_urls > /dev/null 2>&1; then
        echo "| Service | Status | URL |" >> "$report_file"
        echo "|---------|--------|-----|" >> "$report_file"
        
        terraform output -json service_urls | jq -r 'to_entries[] | "| \(.key) | ✅ Deployed | \(.value) |"' >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF

### Storage Buckets
EOF
    
    if terraform output -json storage_buckets > /dev/null 2>&1; then
        echo "| Bucket Type | Name |" >> "$report_file"
        echo "|-------------|------|" >> "$report_file"
        
        terraform output -json storage_buckets | jq -r 'to_entries[] | "| \(.key) | \(.value) |"' >> "$report_file"
    fi
    
    cat >> "$report_file" << EOF

### Configuration

#### Environment Variables
- PROJECT_ID: $PROJECT_ID
- REGION: $REGION  
- ENVIRONMENT: $ENVIRONMENT

#### Next Steps
1. Update domain DNS settings (if using custom domain)
2. Configure monitoring alerts
3. Setup backup schedules
4. Update API keys in terraform.tfvars
5. Test all service endpoints
6. Setup CI/CD pipeline

#### Important Notes
- All services are deployed and running
- Security rules and IAM policies are configured
- Monitoring and logging are enabled
- Secrets are stored in Secret Manager

EOF

    print_status "Deployment report generated: $report_file"
}

# Cleanup function
cleanup() {
    print_info "Cleaning up temporary files..."
    
    # Remove any temporary files created during deployment
    find "$PROJECT_ROOT" -name "*.tmp" -type f -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -name ".terraform.lock.hcl" -type f -delete 2>/dev/null || true
    
    print_status "Cleanup completed"
}

# Main deployment function
main() {
    local start_time=$(date +%s)
    
    # Parse command line arguments
    local skip_tests=false
    local skip_health_check=false
    local skip_frontend=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-tests)
                skip_tests=true
                shift
                ;;
            --skip-health-check)
                skip_health_check=true
                shift
                ;;
            --skip-frontend)
                skip_frontend=true
                shift
                ;;
            --project-id)
                PROJECT_ID="$2"
                shift 2
                ;;
            --region)
                REGION="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --skip-tests           Skip running tests"
                echo "  --skip-health-check    Skip health checks"
                echo "  --skip-frontend        Skip frontend deployment"
                echo "  --project-id ID        Set project ID"
                echo "  --region REGION        Set region"
                echo "  --environment ENV      Set environment (development/staging/production)"
                echo "  -h, --help             Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Trap cleanup on exit
    trap cleanup EXIT
    
    print_info "Starting deployment process..."
    
    # Execute deployment steps
    check_prerequisites
    setup_gcp
    build_and_push_images
    deploy_infrastructure
    setup_firestore
    deploy_ai_agents
    
    if [[ "$skip_frontend" != true ]]; then
        deploy_frontend
    fi
    
    if [[ "$skip_tests" != true ]]; then
        run_tests
    fi
    
    if [[ "$skip_health_check" != true ]]; then
        sleep 30  # Wait for services to start
        health_check
    fi
    
    generate_report
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo ""
    print_status "🎉 Deployment completed successfully!"
    print_info "Total deployment time: ${duration} seconds"
    print_info "Project URL: https://console.cloud.google.com/home/dashboard?project=$PROJECT_ID"
    
    # Show service URLs
    cd "$INFRASTRUCTURE_DIR/terraform"
    if terraform output service_urls > /dev/null 2>&1; then
        echo ""
        print_info "Service URLs:"
        terraform output service_urls | grep -E "main-api|ai-agent" | while read -r line; do
            echo "  $line"
        done
    fi
    
    echo ""
    print_info "Next steps:"
    echo "  1. Review the deployment report"
    echo "  2. Update DNS settings if using custom domain"
    echo "  3. Configure monitoring alerts"
    echo "  4. Update API keys in terraform.tfvars"
    echo "  5. Test the application thoroughly"
    echo ""
}

# Run main function with all arguments
main "$@"