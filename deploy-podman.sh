#!/bin/bash
set -e

echo "SOUL LATTICE v4 - Podman Deployment Ritual"
echo "================================================"

# Required environment variables
: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN must be set}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID must be set}"

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
# NOTE: --allow-unauthenticated is intentional — authentication is enforced at
# the Cloudflare Worker layer (JWT validation). The Cloud Run URL is stored as
# an encrypted Cloudflare Worker secret and is never made public. Do not expose
# the BACKEND_URL in logs, URLs, or documentation.
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_TAG} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --concurrency 80 \
    --max-instances 1 \
    --min-instances 1 \
    --execution-environment gen2 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"

# Capture the stable Cloud Run service URL (more reliable than parsing deploy output)
cd ..
CLOUD_RUN_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --platform managed \
    --format 'value(status.url)')

echo "Cloud Run URL: ${CLOUD_RUN_URL}"

# Inject the backend URL into the Cloudflare Worker as an encrypted secret.
# Pass via stdin so the value never appears in process arguments or shell history.
echo "${CLOUD_RUN_URL}" | npx wrangler secret put BACKEND_URL --env production

echo "Building React SPA..."
npm run build

echo "Deploying Cloudflare Worker + SPA..."
npx wrangler deploy --env production

echo ""
echo "Deployment complete!"
echo ""
echo "Frontend URL: https://yennefer.quest"
echo "API status:   https://yennefer.quest/api/state"
echo "SSE stream:   https://yennefer.quest/api/events"
echo ""
echo "Test the stream (requires a valid Cloudflare Access session):"
echo "curl -N https://yennefer.quest/api/events"
