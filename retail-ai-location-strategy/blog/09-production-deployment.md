# Part 9: Production Deployment

Your agent works beautifully on `localhost:8501`. You've tested it, validated the output quality, and demonstrated it to your team. But now comes the question that matters: how do you get this into the hands of actual users?

The jump from local development to production isn't just about running the same code somewhere else. Production deployment transforms your agent from a demo into a real product. It means your sales team can run location analyses without pinging you on Slack. It means stakeholders in different time zones can access insights when you're asleep. It means the agent scales to handle ten requests at once when the quarterly planning rush hits.

<p align="center">
  <img src="assets/part9_deployment_architecture.jpeg" alt="Part 9: Production Deployment Architecture" width="600">
</p>

---

## Why Production Deployment Matters

Local development gives you a working agent. Production deployment gives you a product. The difference is significant:

| Capability | Why It Matters |
|------------|----------------|
| **Scalability** | Handle multiple users simultaneously without degradation |
| **Security** | IAP authentication ensures only authorized users access the agent |
| **Reliability** | Auto-scaling and health checks keep the agent running 24/7 |
| **Accessibility** | A public URL that works from anywhere, not just your laptop |

This part covers two deployment options: Cloud Run for quick containerized deployment with full control, and Vertex AI Agent Engine for a fully managed enterprise experience.

---

## Deployment Options

| Option | Best For | Complexity |
|--------|----------|------------|
| **Cloud Run** | Quick deployment, full control, cost-effective | Medium |
| **Agent Engine** | Managed service, enterprise scale, Vertex AI integration | Low |

Choose Cloud Run if you want to understand what's happening under the hood and have flexibility in configuration. Choose Agent Engine if you want Google to manage the infrastructure and you're already in the Vertex AI ecosystem.

---

## Option A: Cloud Run Deployment

Cloud Run provides serverless container hosting. You package your agent as a Docker container, push it to Artifact Registry, and Cloud Run handles scaling, HTTPS, and availability.

### Prerequisites

Before deploying, ensure you have:

1. A Google Cloud project with billing enabled
2. The gcloud CLI installed and authenticated
3. Required APIs enabled (Cloud Run, Artifact Registry)

```bash
# Update gcloud to the latest version
gcloud components update

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Authenticate for application default credentials
gcloud auth application-default login

# Enable required APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
```

### Quick Deploy with Make

The project includes a Makefile target that handles the entire deployment process:

```bash
make deploy IAP=true
```

This single command builds a container image from your agent code, pushes it to Artifact Registry, deploys to Cloud Run, and enables Identity-Aware Proxy (IAP) authentication. Within a few minutes, you'll have a secure, production URL.

The deployment process creates a Cloud Run service that runs the ADK web server, which in turn runs your complete agent pipeline. IAP sits in front of Cloud Run, ensuring that only authenticated users from your organization can access the agent.

### Granting User Access

After deployment, users need explicit access. IAP blocks everyone by default—even you:

```bash
# Grant a specific user access
gcloud run services add-iam-policy-binding retail-location-strategy \
  --member="user:someone@example.com" \
  --role="roles/run.invoker" \
  --region=us-central1

# Grant an entire group
gcloud run services add-iam-policy-binding retail-location-strategy \
  --member="group:team@example.com" \
  --role="roles/run.invoker" \
  --region=us-central1
```

See the [IAP User Access documentation](https://cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run#manage_user_or_group_access) for more details on managing permissions.

---

## Option B: Agent Starter Pack

For production deployments that need CI/CD pipelines, infrastructure-as-code, and multi-environment support, the [Agent Starter Pack](https://goo.gle/agent-starter-pack) provides a complete scaffold:

```bash
# Install the CLI
pip install --upgrade agent-starter-pack

# Create a deployment-ready project from your agent
agent-starter-pack create my-retail-agent -a adk@retail-ai-location-strategy

# Deploy with IAP enabled
cd my-retail-agent && make deploy IAP=true
```

The Agent Starter Pack wraps your agent in a production-ready template:

| Feature | Description |
|---------|-------------|
| **CI/CD Pipeline** | GitHub Actions or Cloud Build for automated deployments |
| **Infrastructure** | Terraform configurations for reproducible infrastructure |
| **Monitoring** | Cloud Monitoring integration with pre-built dashboards |
| **Security** | Secret management, IAP, service accounts |
| **Multiple Environments** | Dev, staging, and production configurations |

This is the recommended path for teams that need governance, audit trails, and enterprise-grade operations.

> **Learn more:** The [Agent Starter Pack Documentation](https://googlecloudplatform.github.io/agent-starter-pack/) covers all features and configuration options.

---

## Option C: Vertex AI Agent Engine

For fully managed deployments where you want Google to handle the infrastructure entirely, Vertex AI Agent Engine provides an enterprise-grade solution:

```python
# Deploy to Agent Engine
from google.cloud import aiplatform

aiplatform.init(project="your-project", location="us-central1")

# Create and deploy agent
agent = aiplatform.Agent(
    display_name="retail-location-strategy",
    # ... agent configuration
)
agent.deploy()
```

Agent Engine is the right choice when you need enterprise-scale deployments with SLAs, integration with the broader Vertex AI ecosystem (models, feature stores, pipelines), or multi-model orchestration beyond what ADK provides out of the box.

> **Learn more:** The [ADK Deployment documentation](https://google.github.io/adk-docs/deploy/) covers deployment options in detail.

---

## Environment Configuration

### AI Studio vs Vertex AI

Your agent can run against two different backends:

| Environment | Auth Method | When to Use |
|-------------|-------------|-------------|
| AI Studio | API Key | Local development, prototyping |
| Vertex AI | Service Account | Production, enterprise |

The key difference: AI Studio uses a simple API key, while Vertex AI uses Google Cloud service account authentication with IAM-based access control.

### Production Configuration

For production deployment with Vertex AI:

```bash
# app/.env for production
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
MAPS_API_KEY=your-maps-key
```

Setting `GOOGLE_GENAI_USE_VERTEXAI=TRUE` tells the ADK to use Vertex AI endpoints instead of AI Studio. This is required for production deployments where you want enterprise authentication and SLAs.

### Managing Secrets

Never commit API keys to source control. Use Google Secret Manager:

```bash
# Create a secret from your API key
echo -n "your-maps-api-key" | gcloud secrets create maps-api-key --data-file=-

# Grant the Cloud Run service account access to read the secret
gcloud secrets add-iam-policy-binding maps-api-key \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

Then reference the secret in your Cloud Run service configuration:

```yaml
env:
  - name: MAPS_API_KEY
    valueFrom:
      secretKeyRef:
        name: maps-api-key
        key: latest
```

The Cloud Run service reads the secret value at startup, never exposing it in logs or environment variable dumps.

---

## Production Best Practices

### 1. Model Selection for Reliability

Production deployments should use stable, generally-available models:

```python
# app/config.py

# Production: Use stable models
FAST_MODEL = "gemini-2.5-pro"  # Recommended for production
PRO_MODEL = "gemini-2.5-pro"

# Avoid preview models in production:
# FAST_MODEL = "gemini-3-pro-preview"  # May have availability issues
```

Preview models offer cutting-edge capabilities but may have quota limits, availability issues, or behavior changes. Stable models are better for production reliability.

### 2. Retry Configuration

Transient failures happen in production. Configure appropriate retries:

```python
# app/config.py
RETRY_INITIAL_DELAY = 5   # Initial delay in seconds
RETRY_ATTEMPTS = 5        # Number of retry attempts
RETRY_MAX_DELAY = 60      # Maximum delay between retries
```

These settings are passed to the `GenerateContentConfig` for each agent, ensuring graceful handling of temporary API issues.

### 3. Monitoring and Alerting

Set up Cloud Monitoring alerts for key metrics:

- **Error rates**: Alert when 5xx responses exceed 1%
- **Latency**: Alert when P95 latency exceeds 30 seconds
- **Token usage**: Monitor for unexpected spikes
- **API quota**: Alert before quota exhaustion

### 4. Cost Management

Understand your cost drivers:

| Component | Cost Driver | Optimization |
|-----------|-------------|--------------|
| Gemini API | Token usage | Use flash models where possible |
| Maps API | API calls per request | Cache competitor data |
| Cloud Run | CPU/memory per request | Right-size instances |

For most use cases, the Gemini API is the dominant cost. Monitor token usage and consider caching for repeated queries.

---

## Deployment Checklist

Before going live, verify:

- [ ] Tests passing: `make test-agents`
- [ ] Evaluations meet threshold: `make eval`
- [ ] All secrets stored in Secret Manager (not in code or env files)
- [ ] IAP configured and tested
- [ ] Users granted appropriate access
- [ ] Monitoring alerts configured
- [ ] Cost alerts set up
- [ ] Stable model versions selected (not preview)
- [ ] Retry configuration appropriate for production

---

## Post-Deployment Verification

### Get Your Service URL

```bash
# Get the deployed service URL
gcloud run services describe retail-location-strategy \
  --region=us-central1 \
  --format='value(status.url)'
```

### Test the Deployment

```bash
# Test with an authenticated request
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://your-service-url.run.app/health
```

### View Logs

```bash
# Stream live logs
gcloud run logs tail retail-location-strategy --region=us-central1

# View logs in Cloud Console
gcloud run services logs retail-location-strategy --region=us-central1
```

---

## What You've Learned

In this part, you've taken your agent from local development to production:

- **Cloud Run deployment** with `make deploy IAP=true` for quick, containerized hosting
- **Agent Starter Pack** for CI/CD pipelines and infrastructure-as-code
- **Vertex AI Agent Engine** for fully managed enterprise deployments
- **Environment configuration** for AI Studio vs Vertex AI modes
- **Secret management** with Google Secret Manager
- **Production best practices** for reliability, monitoring, and cost control

Your agent now has a URL that your team can bookmark and share.

---

## Series Complete!

Congratulations. You've built something real.

Starting from a blank project, you now have a production-deployed multi-agent system that transforms a simple question—"Where should I open a coffee shop?"—into comprehensive market intelligence with strategic reports, visual infographics, and podcast-style audio briefings.

**What you built across this series:**

| Part | What You Added | ADK Concepts |
|------|----------------|--------------|
| 1 | Project setup, first agent | Agent structure, `root_agent` export |
| 2 | IntakeAgent | Pydantic schemas, structured output, `output_key` |
| 3 | MarketResearchAgent | Built-in tools, `google_search`, state injection |
| 4 | CompetitorMappingAgent | Custom tools, `ToolContext`, API integration |
| 5 | GapAnalysisAgent | `BuiltInCodeExecutor`, code extraction |
| 6 | StrategyAdvisorAgent | `ThinkingConfig`, extended reasoning, artifacts |
| 7 | ArtifactGenerationPipeline | `ParallelAgent`, image/audio generation |
| 8 | Testing | Integration tests, evaluations, quality metrics |
| 9 | Production | Cloud Run, IAP, secrets management |

Each part added a real capability. Each capability builds on the previous. The result is a system that would have taken weeks to build from scratch, now understood component by component.

---

## What's Next?

The ADK Web UI works well for demos and internal use. But what if you want a richer experience? Real-time progress visualization, interactive cards, bidirectional state synchronization, and a polished user interface?

Check out the **[Bonus: AG-UI Frontend](./bonus-ag-ui-frontend.md)** for an optional Next.js dashboard that connects to your agent using the AG-UI Protocol. It's not required, but it shows what's possible when you want to build a custom frontend for your agent.

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `make deploy IAP=true` | Deploy to Cloud Run with IAP authentication |
| `gcloud run services describe ...` | Get service details and URL |
| `gcloud run logs tail ...` | Stream live logs |
| `gcloud secrets create ...` | Create a secret in Secret Manager |

**Files referenced in this part:**

- [`Makefile`](../Makefile) — Deployment targets
- [`app/config.py`](../app/config.py) — Environment and model configuration
- [`pyproject.toml`](../pyproject.toml) — Package dependencies and metadata

**Documentation:**

- [ADK Deployment](https://google.github.io/adk-docs/deploy/) — ADK deployment options
- [Agent Starter Pack](https://googlecloudplatform.github.io/agent-starter-pack/) — Production templates
- [Cloud Run Deployment](https://cloud.google.com/run/docs) — Cloud Run documentation
- [Identity-Aware Proxy](https://cloud.google.com/iap/docs) — IAP configuration

---

**[← Back to Part 8: Testing](./08-testing.md)** | **[Continue to Bonus: AG-UI Frontend →](./bonus-ag-ui-frontend.md)**
