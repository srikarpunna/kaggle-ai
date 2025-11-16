#!/bin/bash
# ElderCare Agent - Google Cloud Run Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ElderCare Agent - Cloud Run Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-eldercare-agent}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="eldercare-agent"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Check if required tools are installed
command -v gcloud >/dev/null 2>&1 || {
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
}

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${YELLOW}Warning: GEMINI_API_KEY not set${NC}"
    read -p "Enter your Gemini API Key: " GEMINI_API_KEY
fi

echo -e "${GREEN}[1/6] Setting up Google Cloud project...${NC}"
gcloud config set project $PROJECT_ID

echo -e "${GREEN}[2/6] Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

echo -e "${GREEN}[3/6] Building Docker image...${NC}"
cd ../..
gcloud builds submit --tag $IMAGE_NAME

echo -e "${GREEN}[4/6] Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    --set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY" \
    --set-env-vars "FLASK_ENV=production"

echo -e "${GREEN}[5/6] Getting service URL...${NC}"
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo -e "${GREEN}[6/6] Deployment complete!${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Service URL: ${YELLOW}$SERVICE_URL${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Test your deployment:"
echo -e "  ${YELLOW}curl $SERVICE_URL/health${NC}"
echo -e "  ${YELLOW}open $SERVICE_URL${NC}"
echo ""
echo -e "View logs:"
echo -e "  ${YELLOW}gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit 50${NC}"
echo ""
echo -e "Update deployment:"
echo -e "  ${YELLOW}./deploy.sh${NC}"
echo ""
