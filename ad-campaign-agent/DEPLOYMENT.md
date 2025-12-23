# Deployment Guide

This guide covers deploying the Ad Campaign Agent to Google Cloud. Choose the deployment option that fits your use case.

## Deployment Options

| Option | Best For | Web UI | Session Management | Scaling |
|--------|----------|--------|-------------------|---------|
| **Cloud Run** | Development, demos, Web UI access | Yes (`/dev-ui`) | Manual (in-memory) | Configurable |
| **Agent Engine** | Production, API access | No (API only) | Managed by Vertex AI | Automatic |

---

## Prerequisites

### Required Tools

```bash
# Verify installations
gcloud --version    # Google Cloud SDK
adk --version       # ADK CLI (pip install google-adk)
python3 --version   # Python 3.11+
```

### GCP Authentication

```bash
# Login and set project
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com \
  maps-backend.googleapis.com
```

---

## Initial Setup (One-Time)

### 1. Create GCS Bucket

```bash
# Create bucket for assets
gcloud storage buckets create gs://YOUR_BUCKET_NAME \
  --location=us-central1 \
  --uniform-bucket-level-access
```

### 2. Upload Product Images

Product images must be in GCS for video generation to work:

```bash
# Using the setup script (recommended)
./scripts/setup_gcp.sh

# Or manually upload
gcloud storage cp path/to/images/* gs://YOUR_BUCKET_NAME/product-images/
```

### 3. Verify Setup

```bash
# List uploaded images
gcloud storage ls gs://YOUR_BUCKET_NAME/product-images/
```

### 4. Grant GCS Permissions for Agent Engine (Required)

Agent Engine uses a dedicated service account that needs write access to GCS for storing generated videos and thumbnails.

```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')

# Grant storage.objectAdmin to the Reasoning Engine Service Agent
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

> **Note:** The `deploy_ae_inline.py` script automatically grants this permission after deployment. You only need to run this manually if you see 403 errors when writing to GCS.

---

## Cloud Run Deployment

Cloud Run provides a web UI at `/dev-ui` for interactive testing.

### Quick Deploy

```bash
# Set environment variables
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GCS_BUCKET="your-bucket-name"
export GOOGLE_MAPS_API_KEY="your-maps-key"  # Optional

# Deploy
./scripts/deploy.sh
```

### Deploy Script Options

```bash
./scripts/deploy.sh [OPTIONS]

Options:
  --trace       Enable Cloud Trace for observability
  --private     Require authentication (no public access)
  --dry-run     Show command without executing
  --help        Show help message
```

### What Gets Deployed

The script packages the `app/` folder and deploys it with:

- ADK Web UI enabled (`--with_ui`)
- GCS for artifact storage
- 2GB memory, 2 CPU (for video processing)
- 600s timeout (for long video generation)
- Public access by default

### Post-Deployment

```bash
# Get service URL
gcloud run services describe ad-campaign-agent \
  --region=us-central1 \
  --format='value(status.url)'

# View logs
gcloud run services logs read ad-campaign-agent \
  --region=us-central1 --limit=50
```

### Access Points

After deployment:

- **Web UI**: `https://your-service-url/dev-ui`
- **API**: `https://your-service-url`

---

## Agent Engine Deployment

Agent Engine is Google Cloud's managed service for production AI agents.

### Benefits

- **Managed Sessions**: Automatic session and state management
- **Memory Bank**: Persistent memory across conversations
- **Auto-Scaling**: No container management needed
- **Query API**: Programmatic access

### Agent Engine Environment Variables

> **Important:** Agent Engine has known issues with environment variables - they may not propagate correctly at runtime even when passed via `env_vars` parameter (see [ADK issue #3208](https://github.com/google/adk-python/issues/3208) and [#3628](https://github.com/google/adk-python/issues/3628)).

We use a custom `GlobalAdkApp` class that **force-sets critical env vars** in `set_up()` after Agent Engine's initialization:

**Currently managed env vars:**

| Variable | Value | Purpose |
|----------|-------|---------|
| `GOOGLE_CLOUD_LOCATION` | `global` | Required for Gemini 3 models |
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` | Required for Veo video byte extraction |

**How it works:**
1. Agent Engine deploys to `us-central1` and may override/ignore env vars
2. `GlobalAdkApp.set_up()` runs after `super().set_up()`
3. Critical env vars are force-set via `os.environ["VAR"] = "value"`
4. Your tools now read the correct values at runtime

**Adding a new environment variable:**

To add a new env var that must be available at runtime in Agent Engine:

1. **Add to `env_vars` in `scripts/deploy_ae_inline.py`** (line ~304):
   ```python
   env_vars = {
       "GOOGLE_GENAI_USE_VERTEXAI": "TRUE",
       "GEMINI_MODEL_LOCATION": "global",
       "GCS_BUCKET": args.bucket,
       "YOUR_NEW_VAR": "your_value",  # Add here
   }
   ```

2. **Force-set in `app/agent_engine_app.py`** `set_up()` method:
   ```python
   def set_up(self) -> None:
       super().set_up()
       # ... existing env var restores ...

       # Force-set your new env var
       os.environ["YOUR_NEW_VAR"] = os.environ.get("YOUR_NEW_VAR", "default_value")
       print(f"[GlobalAdkApp.set_up] YOUR_NEW_VAR = {os.environ.get('YOUR_NEW_VAR')}")
   ```

3. **Add debug logging** at module level for visibility:
   ```python
   print(f"[GlobalAdkApp] YOUR_NEW_VAR (at import) = {os.environ.get('YOUR_NEW_VAR', 'NOT SET')}")
   ```

4. **Redeploy** with `make deploy-ae-global`

**Key files:**
- `app/agent_engine_app.py` - Custom `GlobalAdkApp` class with env var force-setting
- `scripts/deploy_ae_inline.py` - Passes env vars during deployment

### Deployment Options

| Method | Command | Gemini 3 Support |
|--------|---------|------------------|
| **Python SDK (Recommended)** | `make deploy-ae-global` | **Yes** (via GlobalAdkApp workaround) |
| **CLI** | `make deploy-ae` | Yes (via GlobalAdkApp workaround) |

> **Note:** Both methods now support Gemini 3 models thanks to the `GlobalAdkApp` workaround.

### Quick Deploy (Global Region - Recommended)

For Gemini 3 models, use the Python SDK "inline deployment":

```bash
# Deploy with global region (Gemini 3 support)
make deploy-ae-global

# With Cloud Trace
make deploy-ae-global-trace

# Preview only
make deploy-ae-global-dry-run
```

### Quick Deploy (CLI - Legacy)

```bash
# Deploy to Agent Engine (us-central1)
./scripts/deploy_ae.sh

# With Cloud Trace
./scripts/deploy_ae.sh --trace

# Preview only
./scripts/deploy_ae.sh --dry-run
```

### Deploy Script Options

```bash
./scripts/deploy_ae.sh [OPTIONS]

Options:
  --dry-run              Show command without executing
  --trace                Enable Cloud Trace
  --update               Update existing deployment
  --agent-engine-id=ID   Specify Agent Engine ID to update
  --help                 Show help message
```

### Query Your Agent

**Python (Global Region):**

```python
import vertexai
from vertexai import agent_engines

# Use "global" for Gemini 3 models, or "us-central1" for legacy
vertexai.init(project="your-project-id", location="global")
agent = agent_engines.get("YOUR_AGENT_ENGINE_ID")

# Single query
response = agent.query(input="List all campaigns")
print(response)

# Streaming
for chunk in agent.stream_query(input="Show campaign metrics"):
    print(chunk, end="")
```

**REST API (Global Region):**

```bash
TOKEN=$(gcloud auth print-access-token)

# For global region deployment
curl -X POST \
  "https://global-aiplatform.googleapis.com/v1/projects/YOUR_PROJECT/locations/global/reasoningEngines/YOUR_AGENT_ID:query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": "List all campaigns"}'

# For us-central1 region deployment
curl -X POST \
  "https://us-central1-aiplatform.googleapis.com/v1/projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/YOUR_AGENT_ID:query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": "List all campaigns"}'
```

### Manage Deployments

```bash
# List deployed agents
gcloud ai reasoning-engines list --region=us-central1

# Update existing deployment
./scripts/deploy_ae.sh --agent-engine-id=YOUR_AGENT_ID

# Delete deployment
gcloud ai reasoning-engines delete YOUR_AGENT_ID --region=us-central1
```

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID |
| `GCS_BUCKET` | GCS bucket for assets |

### Optional

| Variable | Description |
|----------|-------------|
| `GOOGLE_MAPS_API_KEY` | For static map generation |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI region (default: `global`) |

### Auto-Configured by Deploy Scripts

| Variable | Value | Purpose |
|----------|-------|---------|
| `GOOGLE_GENAI_USE_VERTEXAI` | `True` | Use Vertex AI |
| `K_SERVICE` | (Cloud Run sets this) | Detect Cloud Run environment |
| `GOOGLE_CLOUD_AGENT_ENGINE_ID` | (Agent Engine sets this) | Detect Agent Engine environment |

---

## Storage Structure

```plaintext
gs://YOUR_BUCKET/
├── product-images/        # Source product images (22 items)
│   ├── blue-floral-maxi-dress.jpg
│   ├── elegant-black-cocktail-dress.jpg
│   └── ...
├── seed-images/           # Legacy location (deprecated)
└── generated/             # Generated videos and thumbnails
    ├── campaign_1_ad_5.mp4
    ├── campaign_1_ad_5_thumb.png
    └── ...
```

---

## Troubleshooting

### Common Issues

**Model Not Found (404)**

```text
Publisher Model `gemini-3-pro-preview` was not found
```

Fix: Ensure `GOOGLE_CLOUD_LOCATION=global` (some models require this).

**Permission Denied on `/app/agents/`**

```text
PermissionError: [Errno 13] Permission denied: '/app/agents/.adk'
```

Fix: Deploy scripts now use `--artifact_service_uri=gs://bucket` for GCS-based artifacts.

**PIL/Pillow Not Found**

```text
No module named 'PIL'
```

Fix: Ensure `requirements.txt` is in the `app/` folder with `Pillow>=10.2.0`.

**Maps API Not Working**

```text
GOOGLE_MAPS_API_KEY environment variable not set
```

Fix: Export `GOOGLE_MAPS_API_KEY` before deploying. AI-generated maps work without this key.

**Video Generation Timeouts**

Veo 3.1 takes 2-3 minutes per video. The deploy script sets a 600s timeout.

**GCS Upload 403 Forbidden (Agent Engine)**

```text
google.api_core.exceptions.Forbidden: 403 POST https://storage.googleapis.com/upload/storage/v1/b/YOUR_BUCKET/o
```

Fix: The Reasoning Engine Service Agent needs `storage.objectAdmin` permission. Run:

```bash
# Get project number
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')

# Grant permission
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

Or use `make setup-ae-permissions` to grant automatically.

### View Logs

```bash
# Cloud Run - real-time
gcloud run services logs tail ad-campaign-agent --region=us-central1

# Cloud Run - recent logs
gcloud run services logs read ad-campaign-agent --region=us-central1 --limit=100

# Cloud Console
open "https://console.cloud.google.com/run/detail/us-central1/ad-campaign-agent/logs"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `app/agent.py` | Agent definitions (root_agent) |
| `app/config.py` | Models, paths, environment detection |
| `app/requirements.txt` | Python dependencies |
| `scripts/deploy.sh` | Cloud Run deployment |
| `scripts/deploy_ae.sh` | Agent Engine deployment (CLI, us-central1) |
| `scripts/deploy_ae_inline.py` | Agent Engine deployment (Python SDK, global region) |
| `scripts/setup_gcp.sh` | GCP resource setup |

---

## Models Used

| Purpose | Model | Region Required |
|---------|-------|-----------------|
| Agent Reasoning | `gemini-3-flash-preview` | `global` |
| Scene Image Generation | `gemini-3-pro-image-preview` | `global` |
| Video Animation | `veo-3.1-generate-preview` | `global` |
| Charts & Maps | `gemini-3-pro-image-preview` | `global` |

> **Important:** All Gemini 3 models require `global` region. Use `make deploy-ae-global` for Agent Engine deployment.

---

## Quick Reference

### Cloud Run (Full Deploy)

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT
./scripts/setup_gcp.sh
export GOOGLE_MAPS_API_KEY="your-key"
./scripts/deploy.sh --trace
```

### Agent Engine (Full Deploy - Global Region)

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT
./scripts/setup_gcp.sh
make deploy-ae-global-trace  # Recommended for Gemini 3
```

### Agent Engine (Legacy - us-central1)

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT
./scripts/setup_gcp.sh
./scripts/deploy_ae.sh --trace
```

### Update Deployment

```bash
# Cloud Run - just redeploy
./scripts/deploy.sh

# Agent Engine - update existing
./scripts/deploy_ae.sh --agent-engine-id=YOUR_ID
```

### Delete Deployment

```bash
# Cloud Run
gcloud run services delete ad-campaign-agent --region=us-central1

# Agent Engine (global region)
gcloud ai reasoning-engines delete YOUR_ID --region=global

# Agent Engine (us-central1 region)
gcloud ai reasoning-engines delete YOUR_ID --region=us-central1
```
