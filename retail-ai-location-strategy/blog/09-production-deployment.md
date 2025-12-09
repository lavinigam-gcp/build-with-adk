# Part 9: Production Deployment

By the end of this part, your agent will be deployed to production with a live URL.

**Options**:
- Cloud Run with IAP authentication
- Vertex AI Agent Engine (managed)

---

## From Local to Production

Your agent works beautifully on `localhost:8501`. You've tested it, validated the output quality, and demonstrated it to your team. But now comes the question that matters: how do you get this into the hands of actual users?

The jump from local development to production isn't just about running the same code somewhere else. Production deployment transforms your agent from a demo into a real product. It means your sales team can run location analyses without pinging you on Slack. It means stakeholders in different time zones can access insights when you're asleep. It means the agent scales to handle ten requests at once when the quarterly planning rush hits.

Production deployment provides:

| Capability | Why It Matters |
|------------|----------------|
| **Scalability** | Handle multiple users simultaneously without degradation |
| **Security** | IAP authentication ensures only authorized users access the agent |
| **Reliability** | Auto-scaling and health checks keep the agent running 24/7 |
| **Accessibility** | A public URL that works from anywhere, not just your laptop |

---

## Deployment Options

| Option | Best For | Complexity |
|--------|----------|------------|
| **Cloud Run** | Quick deployment, full control | Medium |
| **Agent Engine** | Managed service, enterprise | Low |

---

## Option A: Cloud Run Deployment

### Prerequisites

1. Google Cloud project with billing enabled
2. gcloud CLI installed and authenticated
3. Required APIs enabled (Cloud Run, Artifact Registry)

```bash
# Update gcloud
gcloud components update

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Authenticate
gcloud auth application-default login
```

### Quick Deploy with Make

The project includes a Makefile target for deployment:

```bash
make deploy IAP=true
```

This command:
1. Builds a container image
2. Pushes to Artifact Registry
3. Deploys to Cloud Run
4. Enables IAP authentication

### What Gets Deployed

```
┌─────────────────────────────────────────────────────┐
│                   Cloud Run                          │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐     ┌─────────────────────────┐   │
│  │   ADK Web   │────▶│  Retail Location Agent  │   │
│  │   Server    │     │  (Your complete agent)  │   │
│  └─────────────┘     └─────────────────────────┘   │
│         ▲                                           │
│         │                                           │
│  ┌──────┴──────┐                                   │
│  │     IAP     │  ← Identity-Aware Proxy           │
│  └─────────────┘                                   │
└─────────────────────────────────────────────────────┘
                ▲
                │
         HTTPS request
                │
         ┌──────┴──────┐
         │   Users     │
         └─────────────┘
```

### Granting Access

After deployment, grant users access:

```bash
# Grant a specific user
gcloud run services add-iam-policy-binding retail-location-strategy \
  --member="user:someone@example.com" \
  --role="roles/run.invoker" \
  --region=us-central1

# Grant a group
gcloud run services add-iam-policy-binding retail-location-strategy \
  --member="group:team@example.com" \
  --role="roles/run.invoker" \
  --region=us-central1
```

See [Manage User Access](https://cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run#manage_user_or_group_access) for details.

---

## Option B: Agent Starter Pack

For production deployments with CI/CD, use the [Agent Starter Pack](https://goo.gle/agent-starter-pack):

```bash
# Install the CLI
pip install --upgrade agent-starter-pack

# Create a deployment-ready project
agent-starter-pack create my-retail-agent -a adk@retail-ai-location-strategy

# Deploy
cd my-retail-agent && make deploy IAP=true
```

### What Agent Starter Pack Provides

| Feature | Description |
|---------|-------------|
| **CI/CD Pipeline** | GitHub Actions / Cloud Build |
| **Infrastructure** | Terraform configurations |
| **Monitoring** | Cloud Monitoring integration |
| **Security** | Secret management, IAP |
| **Multiple Envs** | Dev, staging, production |

See the [Agent Starter Pack Documentation](https://googlecloudplatform.github.io/agent-starter-pack/) for details.

---

## Option C: Vertex AI Agent Engine

Agent Engine provides a fully managed deployment:

```python
# Deploy to Agent Engine
from google.cloud import aiplatform

aiplatform.init(project="your-project", location="us-central1")

# Create agent deployment
agent = aiplatform.Agent(
    display_name="retail-location-strategy",
    # ... configuration
)
agent.deploy()
```

### When to Choose Agent Engine

- Enterprise-scale deployments
- Need managed infrastructure
- Integration with Vertex AI ecosystem
- Multi-model orchestration

---

## Environment Configuration

### AI Studio vs Vertex AI

| Environment | Auth Method | Config |
|-------------|-------------|--------|
| Local (AI Studio) | API Key | `GOOGLE_GENAI_USE_VERTEXAI=FALSE` |
| Production (Vertex AI) | Service Account | `GOOGLE_GENAI_USE_VERTEXAI=TRUE` |

### Production Configuration

For Vertex AI mode:

```bash
# app/.env for production
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
MAPS_API_KEY=your-maps-key
```

### Managing Secrets

Use Google Secret Manager for API keys:

```bash
# Create secret
echo -n "your-maps-api-key" | gcloud secrets create maps-api-key --data-file=-

# Grant access to Cloud Run service account
gcloud secrets add-iam-policy-binding maps-api-key \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

Then reference in Cloud Run:

```yaml
env:
  - name: MAPS_API_KEY
    valueFrom:
      secretKeyRef:
        name: maps-api-key
        key: latest
```

---

## Production Best Practices

### 1. Model Selection for Reliability

```python
# app/config.py

# Production: Use stable models
FAST_MODEL = "gemini-2.5-pro"  # Recommended
PRO_MODEL = "gemini-2.5-pro"

# Not recommended for production:
# FAST_MODEL = "gemini-3-pro-preview"  # May have availability issues
```

### 2. Retry Configuration

```python
# app/config.py
RETRY_INITIAL_DELAY = 5   # seconds
RETRY_ATTEMPTS = 5        # retries
RETRY_MAX_DELAY = 60      # max delay
```

### 3. Monitoring

Set up Cloud Monitoring alerts for:
- Error rates (5xx responses)
- Latency (P95 > 30s)
- Token usage
- API quota exhaustion

### 4. Cost Management

| Component | Cost Driver | Optimization |
|-----------|-------------|--------------|
| Gemini API | Token usage | Use flash models where possible |
| Maps API | API calls | Cache competitor data |
| Cloud Run | CPU/memory | Right-size instances |

---

## Deployment Checklist

Before going live:

- [ ] Tests passing: `make test-agents`
- [ ] Evaluations meet threshold: `make eval`
- [ ] Secrets in Secret Manager
- [ ] IAP configured
- [ ] Users granted access
- [ ] Monitoring alerts set up
- [ ] Cost alerts configured
- [ ] Stable model versions selected

---

## Post-Deployment

### Verify Deployment

```bash
# Get the service URL
gcloud run services describe retail-location-strategy \
  --region=us-central1 \
  --format='value(status.url)'

# Test with curl (requires IAP token)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://your-service-url.run.app/health
```

### View Logs

```bash
# Stream logs
gcloud run logs tail retail-location-strategy --region=us-central1

# View in console
gcloud run services logs retail-location-strategy --region=us-central1
```

---

## What You've Learned

In this part, you:

1. Deployed to Cloud Run with IAP authentication
2. Explored Agent Starter Pack for CI/CD
3. Configured environment for production
4. Set up secrets management
5. Established production best practices

---

## Series Complete!

Congratulations. You've built something real.

Starting from a blank project, you now have a production-deployed multi-agent system that transforms a simple question—"Where should I open a coffee shop?"—into comprehensive market intelligence with reports, infographics, and audio briefings.

**What you built across this series:**

| Part | What You Added | ADK Concepts |
|------|----------------|--------------|
| 1 | Project setup, first agent | Agent structure, `root_agent` export |
| 2 | IntakeAgent | Pydantic schemas, structured output, `output_key` |
| 3 | MarketResearchAgent | Built-in tools, `google_search`, state injection |
| 4 | CompetitorMappingAgent | Custom tools, `ToolContext`, API integration |
| 5 | GapAnalysisAgent | `BuiltInCodeExecutor`, code extraction |
| 6 | StrategyAdvisorAgent | `ThinkingConfig`, extended reasoning, artifacts |
| 7 | ArtifactGeneration | `ParallelAgent`, image/audio generation |
| 8 | Testing | Integration tests, evaluations, quality metrics |
| 9 | Production | Cloud Run, IAP, secrets management |

Each part added a real capability. Each capability builds on the previous. The result is a system that would have taken weeks to build from scratch, now understood component by component.

### What's Next?

The ADK Web UI works for demos, but what if you want a richer experience? Real-time progress visualization, interactive cards, bidirectional state sync?

Check out the [Bonus: AG-UI Frontend](./bonus-ag-ui-frontend.md) for an optional Next.js dashboard that connects to your agent using the AG-UI Protocol.

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `make deploy IAP=true` | Deploy to Cloud Run with IAP |
| `gcloud run services describe ...` | Get service details |
| `gcloud run logs tail ...` | Stream logs |

---

**Code files referenced in this part:**
- [`Makefile`](../Makefile) - Deployment targets
- [`app/config.py`](../app/config.py) - Environment configuration
- [`pyproject.toml`](../pyproject.toml) - Package configuration

**Documentation:**
- [Agent Starter Pack](https://googlecloudplatform.github.io/agent-starter-pack/)
- [Cloud Run Deployment](https://cloud.google.com/run/docs)
- [Identity-Aware Proxy](https://cloud.google.com/iap/docs)

---

<details>
<summary>Image Prompt for This Part</summary>

```json
{
  "image_type": "deployment_architecture",
  "style": {
    "design": "cloud architecture diagram",
    "color_scheme": "Google Cloud colors (blue #4285F4, red #EA4335, yellow #FBBC05, green #34A853) with white background",
    "layout": "left to right with cloud platform",
    "aesthetic": "professional, enterprise"
  },
  "dimensions": {"aspect_ratio": "16:9", "recommended_width": 1100},
  "title": {"text": "Part 9: Production Deployment", "position": "top center"},
  "sections": [
    {
      "id": "local",
      "position": "left",
      "color": "#E8F5E9",
      "components": [
        {"name": "Local Development", "icon": "laptop", "description": "adk web :8501"}
      ]
    },
    {
      "id": "asp",
      "position": "center-left",
      "color": "#4285F4",
      "components": [
        {"name": "Agent Starter Pack", "icon": "template/scaffold", "command": "agent-starter-pack create"}
      ]
    },
    {
      "id": "gcp",
      "position": "center-right",
      "label": "Google Cloud Platform",
      "components": [
        {"name": "Cloud Run", "icon": "Cloud Run logo", "features": ["Serverless", "Auto-scaling"]},
        {"name": "Agent Engine", "icon": "Vertex AI logo", "features": ["Managed", "Enterprise"]}
      ]
    },
    {
      "id": "auth",
      "position": "right",
      "color": "#EA4335",
      "components": [
        {"name": "IAP Authentication", "icon": "shield/lock"},
        {"name": "Production URL", "icon": "globe/link"}
      ]
    }
  ],
  "connections": [
    {"from": "local", "to": "asp", "label": "Template"},
    {"from": "asp", "to": "gcp", "label": "make deploy"},
    {"from": "gcp", "to": "auth", "label": "Secured"}
  ]
}
```

</details>
