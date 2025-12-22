# Ad Campaign Agent

An AI-powered retail media platform built with Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/). This multi-agent system demonstrates end-to-end ad campaign management - from product selection to video ad generation using **Veo 3.1** and **Gemini**.

## The Complete Journey

![Use Case Overview](assets/use-case-poster.jpeg)

*From overwhelmed to optimized: 6-step journey from discovering your AI team to scaling winning formulas across all store locations. Traditional 4-6 week campaigns now take under 10 minutes.*

## What This Project Does

This agent helps retail media teams create and manage in-store video advertising campaigns:

- **Browse Products** - 22 pre-loaded fashion products with images
- **Create Campaigns** - Product-centric campaigns tied to store locations
- **Generate Video Ads** - Two-stage pipeline: Gemini creates scene images, Veo 3.1 animates them
- **Human-in-the-Loop Review** - Approve, pause, or archive generated videos
- **Analyze Performance** - In-store retail metrics with AI-generated charts and maps
- **Scale Winners** - Apply successful video characteristics to other campaigns

## Architecture

### High-Level Design

![High-Level Architecture](assets/high_level_system_design.jpeg)

*Layered architecture: Interface → Coordinator → Specialized Agents → AI Services → Data Storage → Deployment. The system comprises 39 tools across 4 agents managing 4 pre-loaded campaigns.*

The system uses a hierarchical multi-agent architecture with four specialized agents:

| Agent | Role | Key Tools |
|-------|------|-----------|
| **Coordinator** | Routes requests to specialists | Orchestration |
| **Campaign Agent** | Campaign CRUD, locations, demographics | 7 tools |
| **Media Agent** | Video generation, product browsing | 15 tools |
| **Review Agent** | HITL workflow, activation, status | 9 tools |
| **Analytics Agent** | Metrics, charts, maps, insights | 8 tools |

### Detailed System Architecture

![System Architecture](assets/system-architecture.jpeg)

*Complete technical view showing all agent tools, external services (Gemini 3 Pro, Veo 3.1, PostgreSQL), data storage layers, and deployment options (Cloud Run with Web UI, Agent Engine for production).*

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud project with Vertex AI API enabled
- [ADK CLI](https://google.github.io/adk-docs/get-started/installation/) installed

### Local Development

```bash
# Clone and navigate
git clone <repository-url>
cd ad-campaign-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r app/requirements.txt

# Set environment variables
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GCS_BUCKET="your-gcs-bucket"
export GOOGLE_MAPS_API_KEY="your-maps-key"  # Optional

# Run with ADK Web UI
adk web app
```

Open http://localhost:8000 to access the ADK Web UI.

### Try These Prompts

```
# See what's available
What agents are available and what are our current campaigns?

# Browse products
Show me all available products with their image links

# Generate a video
Generate a video for campaign 1 with an Asian model on a beach at golden hour

# Review and activate
Show me the video review table with public links
Activate video 5

# View analytics
Get metrics for campaign 1 over the last 30 days
Generate a trendline chart for campaign 1
```

## Project Structure

```
ad-campaign-agent/
├── app/                          # Core agent code (deployment target)
│   ├── agent.py                  # Multi-agent definitions (root_agent)
│   ├── config.py                 # Models, paths, environment detection
│   ├── storage.py                # GCS/local storage abstraction
│   ├── requirements.txt          # Python dependencies
│   ├── database/
│   │   ├── db.py                 # SQLite schema and migrations
│   │   ├── mock_data.py          # Demo data population
│   │   └── products_data.py      # 22 product definitions
│   ├── models/
│   │   ├── variation.py          # CreativeVariation Pydantic model
│   │   └── video_properties.py   # VideoProperties for analysis
│   └── tools/
│       ├── campaign_tools.py     # Campaign CRUD operations
│       ├── image_tools.py        # Image handling and analysis
│       ├── video_tools.py        # Veo 3.1 video generation
│       ├── review_tools.py       # HITL activation workflow
│       ├── metrics_tools.py      # Analytics and charts
│       ├── maps_tools.py         # Google Maps integration
│       └── prompt_builders.py    # Scene/video prompt generation
├── scripts/
│   ├── deploy.sh                 # Cloud Run deployment
│   ├── deploy_ae.sh              # Agent Engine deployment
│   └── setup_gcp.sh              # GCP resource setup
├── assets/                       # Architecture diagrams
├── DEMO_GUIDE.md                 # Complete demo walkthrough
└── DEPLOYMENT.md                 # Deployment instructions
```

## Key Concepts

### Product-Centric Campaigns

Each campaign = 1 product + 1 store location.

```
Campaign: "Blue Floral Maxi Dress - Westfield Century City"
         └── Product: blue-floral-maxi-dress
         └── Store: Westfield Century City, Los Angeles, CA
```

This enables clear metrics attribution and A/B testing per product per location.

### Two-Stage Video Pipeline

1. **Stage 1 (Gemini)**: Generate scene image with model wearing the product
2. **Stage 2 (Veo 3.1)**: Animate into 8-second cinematic video

### Creative Variations

Videos can be customized with 15+ parameters:

| Category | Parameters |
|----------|------------|
| Model | `model_ethnicity` (asian, european, african, latina, etc.) |
| Setting | `setting` (studio, beach, urban, cafe, rooftop, garden) |
| Mood | `mood` (elegant, romantic, bold, playful, sophisticated) |
| Lighting | `lighting` (natural, studio, dramatic, soft, golden, neon) |
| Camera | `camera_movement` (orbit, pan, dolly, tracking, crane) |
| Activity | `activity` (walking, standing, sitting, dancing, posing) |
| Environment | `time_of_day`, `weather`, `season` |

### HITL Workflow

Videos follow a review lifecycle:

```
Generated → [Review] → Activated → [Optionally] → Paused/Archived
                           ↓
                    Metrics generated (30 days)
```

Metrics only appear after human approval.

### In-Store Retail Metrics

| Metric | Description |
|--------|-------------|
| **Impressions** | Ad displays on in-store screens |
| **Dwell Time** | Seconds shoppers viewed the ad |
| **Circulation** | Foot traffic past the display |
| **RPI** | Revenue Per Impression (primary KPI) |

## Models Used

| Purpose | Model |
|---------|-------|
| Agent Reasoning | `gemini-2.5-pro` |
| Scene Image Generation | `gemini-2.5-flash-image` |
| Video Animation | `veo-3.1-generate-preview` |
| Charts & Maps | `gemini-2.5-flash-image` |

## Deployment

Two deployment options are available:

| Option | Best For | Web UI | Session Management |
|--------|----------|--------|-------------------|
| **Cloud Run** | Development, demos | Yes (`/dev-ui`) | Manual |
| **Agent Engine** | Production, API access | No | Managed by Vertex AI |

```bash
# Cloud Run (with Web UI)
./scripts/deploy.sh

# Agent Engine (managed service)
./scripts/deploy_ae.sh
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## Demo Guide

For a complete 20-minute demo walkthrough covering all agents and features, see [DEMO_GUIDE.md](DEMO_GUIDE.md).

Pre-loaded demo campaigns:

| Campaign | Product | Store | Location |
|----------|---------|-------|----------|
| 1 | Blue Floral Maxi Dress | Westfield Century City | Los Angeles, CA |
| 2 | Elegant Black Cocktail Dress | Bloomingdale's 59th Street | New York, NY |
| 3 | Black High Waist Trousers | Water Tower Place | Chicago, IL |
| 4 | Emerald Satin Slip Dress | The Grove | Los Angeles, CA |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_CLOUD_PROJECT` | Yes | GCP project ID |
| `GCS_BUCKET` | Yes | GCS bucket for assets |
| `GOOGLE_MAPS_API_KEY` | No | For static map generation |

## Learn More

- [ADK Documentation](https://google.github.io/adk-docs/)
- [Veo 3.1 API](https://cloud.google.com/vertex-ai/generative-ai/docs/video/overview)
- [Gemini API](https://ai.google.dev/gemini-api/docs)

## License

Apache License 2.0
