#!/bin/bash
set -e

echo "SOUL LATTICE v4 - Podman Deployment Ritual"
echo "================================================"

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
SERVICE_NAME="soul-lattice"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:v4.0.0"

echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Image: ${IMAGE_TAG}"
echo ""

echo "Building container with Podman..."
cd backend
podman build -t ${SERVICE_NAME}:latest -f Containerfile .

echo "Tagging for Google Container Registry..."
podman tag ${SERVICE_NAME}:latest ${IMAGE_TAG}

echo "Pushing to GCR..."
podman push ${IMAGE_TAG}

echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_TAG} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --concurrency 1000 \
    --max-instances 10 \
    --min-instances 1 \
    --execution-environment gen2 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"

echo "Building React cockpit..."
cd ../frontend
npm install
npm run build

echo "Deploying to Firebase Hosting..."
cd ..
firebase deploy --only hosting

echo ""
echo "Deployment complete!"
echo ""
HOSTING_URL=$(firebase hosting:channel:list | grep -o 'https://[^ ]*' | head -1)
echo "Frontend URL: ${HOSTING_URL}"
echo "API Status: ${HOSTING_URL}/api/"
echo "SSE Stream: ${HOSTING_URL}/api/events"
echo ""
echo "Test the stream:"
echo "curl ${HOSTING_URL}/api/events"
