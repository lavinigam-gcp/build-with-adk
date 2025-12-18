# Ad Campaign Agent - Cloud Run Deployment Guide

This guide covers deploying the Ad Campaign Agent to Google Cloud Run.

## Prerequisites

### 1. Required Tools

```bash
# Google Cloud SDK
gcloud --version

# ADK CLI
adk --version

# Python 3.11+
python3 --version
```

### 2. GCP Authentication

```bash
# Login to GCP
gcloud auth login

# Set application default credentials (for local testing)
gcloud auth application-default login

# Set your project
gcloud config set project kaggle-on-gcp
```

## GCP Setup (One-Time)

### 1. Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  maps-backend.googleapis.com \
  --project=kaggle-on-gcp
```

### 2. Create GCS Bucket

```bash
# Create bucket for assets
gcloud storage buckets create gs://kaggle-on-gcp-ad-campaign-assets \
  --project=kaggle-on-gcp \
  --location=us-central1 \
  --uniform-bucket-level-access
```

### 3. Upload Demo Assets

```bash
# Run the setup script (creates bucket and uploads assets)
./scripts/setup_gcp.sh
```

Or manually:
```bash
# Upload seed images
gcloud storage cp selected/* gs://kaggle-on-gcp-ad-campaign-assets/seed-images/

# Upload generated videos (if any)
gcloud storage cp generated/*.mp4 gs://kaggle-on-gcp-ad-campaign-assets/generated/
```

### 4. Verify Assets

```bash
# List seed images
gcloud storage ls gs://kaggle-on-gcp-ad-campaign-assets/seed-images/

# List generated videos
gcloud storage ls gs://kaggle-on-gcp-ad-campaign-assets/generated/
```

## Environment Variables

### Required for Deployment

| Variable | Description | Example |
|----------|-------------|---------|
| `MAPS_API_KEY` | Google Maps API key for location features | `AIzaSy...` |

### Set Before Deploying

```bash
# Google Maps API Key (get from GCP Console > APIs & Services > Credentials)
export MAPS_API_KEY="your-google-maps-api-key"
```

### Auto-Set by Deploy Script

These are automatically configured by `deploy.sh`:

| Variable | Value | Purpose |
|----------|-------|---------|
| `GCS_BUCKET` | `kaggle-on-gcp-ad-campaign-assets` | Asset storage |
| `GOOGLE_GENAI_USE_VERTEXAI` | `True` | Use Vertex AI |
| `GOOGLE_CLOUD_PROJECT` | `kaggle-on-gcp` | GCP project |
| `GOOGLE_CLOUD_LOCATION` | `global` | Vertex AI location |

## Deployment

### Step-by-Step

```bash
# 1. Navigate to agent directory
cd ad-campaign-agent

# 2. Set Maps API Key
export MAPS_API_KEY="your-google-maps-api-key"

# 3. Deploy (with trace for debugging)
./scripts/deploy.sh --trace

# Or deploy without trace
./scripts/deploy.sh
```

### Deploy Script Options

```bash
./scripts/deploy.sh [OPTIONS]

Options:
  --trace       Enable Cloud Trace for observability
  --private     Deploy without public access (requires authentication)
  --dry-run     Show deployment command without executing
  --help        Show help message
```

### What the Deploy Script Does

1. Validates prerequisites (gcloud, adk)
2. Sets environment variables for Cloud Run
3. Configures GCS for artifact storage
4. Deploys with `adk deploy cloud_run`
5. Enables public access (default)
6. Shows service URL when complete

## Post-Deployment

### Verify Deployment

```bash
# Check service status
gcloud run services describe ad-campaign-agent \
  --project=kaggle-on-gcp \
  --region=us-central1

# View logs
gcloud run services logs read ad-campaign-agent \
  --project=kaggle-on-gcp \
  --region=us-central1 \
  --limit=50
```

### Access the Service

After deployment, you'll get URLs like:
- **API**: `https://ad-campaign-agent-xxxxx.us-central1.run.app`
- **Web UI**: `https://ad-campaign-agent-xxxxx.us-central1.run.app/dev-ui`

### Test the Agent

1. Open the Web UI URL in your browser
2. Try: "List all campaigns"
3. Try: "Generate a video ad for campaign 1"
4. Try: "Show campaign locations on a map"

## Troubleshooting

### Common Issues

#### 1. Model Not Found (404)
```
Publisher Model `gemini-3-pro-preview` was not found
```
**Fix**: Ensure `GOOGLE_CLOUD_LOCATION=global` is set (not `us-central1`)

#### 2. Permission Denied on `/app/agents/`
```
PermissionError: [Errno 13] Permission denied: '/app/agents/.adk'
```
**Fix**: Deploy script now uses `--artifact_service_uri=gs://bucket` for GCS artifacts

#### 3. PIL/Pillow Not Found
```
No module named 'PIL'
```
**Fix**: Ensure `requirements.txt` is in the `app/` folder (not just project root)

#### 4. Maps API Not Working
```
GOOGLE_MAPS_API_KEY environment variable not set
```
**Fix**: Export `MAPS_API_KEY` before running deploy.sh

### View Detailed Logs

```bash
# Stream logs in real-time
gcloud run services logs tail ad-campaign-agent \
  --project=kaggle-on-gcp \
  --region=us-central1

# View logs in Cloud Console
open "https://console.cloud.google.com/run/detail/us-central1/ad-campaign-agent/logs?project=kaggle-on-gcp"
```

## Update Deployment

To redeploy after code changes:

```bash
export MAPS_API_KEY="your-google-maps-api-key"
./scripts/deploy.sh --trace
```

## Delete Deployment

```bash
gcloud run services delete ad-campaign-agent \
  --project=kaggle-on-gcp \
  --region=us-central1
```

## Configuration Reference

### Key Files

| File | Purpose |
|------|---------|
| `app/config.py` | App configuration (models, GCS bucket) |
| `app/requirements.txt` | Python dependencies |
| `scripts/deploy.sh` | Deployment script |
| `scripts/setup_gcp.sh` | GCP resource setup |

### Models Used

| Purpose | Model |
|---------|-------|
| Main Agent | `gemini-3-pro-preview` |
| Video Analysis | `gemini-2.5-pro` |
| Image Analysis | `gemini-2.0-flash` |
| Image Generation | `gemini-3-pro-image-preview` |
| Video Generation | `veo-3.1-generate-preview` |

### Storage Structure

```
gs://kaggle-on-gcp-ad-campaign-assets/
├── seed-images/           # Input fashion images
│   ├── dress_*.jpg
│   ├── top_*.jpg
│   └── generated_seed_*.png
└── generated/             # Generated video ads
    └── campaign_*_ad_*.mp4
```

## Quick Reference

```bash
# Full deployment from scratch
gcloud auth login
gcloud auth application-default login
gcloud config set project kaggle-on-gcp
./scripts/setup_gcp.sh
export MAPS_API_KEY="your-key"
./scripts/deploy.sh --trace
```
