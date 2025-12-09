# Retail AI Location Strategy with Google ADK

A multi-agent AI pipeline for retail site selection, built with [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) and Gemini.

<table>
  <thead>
    <tr>
      <th colspan="2">Key Features</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>🔍</td>
      <td><strong>Multi-Agent Pipeline:</strong> 7 specialized agents for market research, competitor mapping, gap analysis, strategy synthesis, and report generation.</td>
    </tr>
    <tr>
      <td>🗺️</td>
      <td><strong>Real-World Data:</strong> Integrates Google Maps Places API for competitor mapping and Google Search for live market research.</td>
    </tr>
    <tr>
      <td>🐍</td>
      <td><strong>Code Execution:</strong> Python/pandas analysis for quantitative gap analysis with viability scoring.</td>
    </tr>
    <tr>
      <td>🎨</td>
      <td><strong>AI-Generated Outputs:</strong> Executive HTML reports and infographics via Gemini's native image generation.</td>
    </tr>
    <tr>
      <td>🖥️</td>
      <td><strong>AG-UI Frontend:</strong> Optional interactive dashboard with <a href="https://docs.ag-ui.com/">AG-UI Protocol</a> and <a href="https://docs.copilotkit.ai/">CopilotKit</a> for real-time pipeline visualization.</td>
    </tr>
    <tr>
      <td>🏗️</td>
      <td><strong>Production-Ready:</strong> Deploy to <a href="https://cloud.google.com/run">Cloud Run</a> or <a href="https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview">Vertex AI Agent Engine</a> via <a href="https://goo.gle/agent-starter-pack">Agent Starter Pack</a>.</td>
    </tr>
    <tr>
      <td>🧪</td>
      <td><strong>Tests & Evals:</strong> Unit tests, integration tests with <a href="https://google.github.io/adk-docs/">ADK Runner</a>, and evaluation datasets for measuring agent quality.</td>
    </tr>
  </tbody>
</table>

<p align="center">
  <img src="assets/images/main-intro-image.png" alt="Retail AI Location Strategy - System Architecture" width="800">
</p>

## What It Does

Given a location and business type, this pipeline automatically:

- Researches the market using live web search
- Maps competitors using Google Maps Places API
- Calculates viability scores with Python code execution
- Generates strategic recommendations with extended reasoning
- Produces an HTML executive report and visual infographic

---

## Getting Started: From Zero to Running Agent in 5 Minutes

**Prerequisites:**
- **[Python 3.10-3.12](https://www.python.org/downloads/)**
- **[uv](https://github.com/astral-sh/uv)** (recommended) or pip
- **[Google Maps API key](https://console.cloud.google.com/apis/credentials)** (with Places API enabled)
- **[Node.js 18+](https://nodejs.org/)** *(only required for AG-UI frontend)*

You have two options to get started. Choose the one that best fits your setup:

*   A. **[Google AI Studio (Recommended)](#a-google-ai-studio-recommended)**: The quickest way to get started using a **Google AI Studio API key**.
*   B. **[Google Cloud Vertex AI](#b-google-cloud-vertex-ai)**: Choose this path if you want to use an existing **Google Cloud project** for authentication and production deployment.

---

### A. Google AI Studio (Recommended)

You'll need a **[Google AI Studio API Key](https://aistudio.google.com/app/apikey)**.

#### Step 1: Clone Repository
Clone the repository and `cd` into the project directory.

```bash
git clone https://github.com/lavinigam-gcp/build-with-adk.git
cd build-with-adk/retail-ai-location-strategy
```

#### Step 2: Set Environment Variables
Create a `.env` file in the `app` folder with your API keys (see `.env.example` for reference):

```bash
echo "GOOGLE_GENAI_USE_VERTEXAI=FALSE" >> app/.env
echo "GOOGLE_API_KEY=YOUR_AI_STUDIO_API_KEY" >> app/.env
echo "MAPS_API_KEY=YOUR_MAPS_API_KEY" >> app/.env
```

#### Step 3: Install & Run
From the `retail-ai-location-strategy` directory, install dependencies and start the server.

```bash
make install && make dev
```

#### What You'll See

1. Open `http://localhost:8501` in your browser
2. Select **"app"** from the agent dropdown
3. Type a query like: *"I want to open a coffee shop in Indiranagar, Bangalore"*
4. Watch the 7-stage pipeline execute:
   - **Intake** → Extract location and business type
   - **Market Research** → Web search for demographics and trends
   - **Competitor Mapping** → Google Maps Places API for competitors
   - **Gap Analysis** → Python code execution for viability scores
   - **Strategy Advisor** → Extended reasoning for recommendations
   - **Report Generator** → HTML executive report
   - **Infographic Generator** → Visual summary image

<p align="center">
  <img src="assets/gifs/adk-web-demo.gif" alt="ADK Web Demo" width="700">
</p>

Your agent is now running at `http://localhost:8501`.

---

### B. Google Cloud Vertex AI

Use Vertex AI for production deployments with enterprise features and Google Cloud integration.

You'll need: **[Google Cloud SDK](https://cloud.google.com/sdk/docs/install)** and a **Google Cloud Project** with the **Vertex AI API** enabled.

#### Step 1: Clone Repository
```bash
git clone https://github.com/lavinigam-gcp/build-with-adk.git
cd build-with-adk/retail-ai-location-strategy
```

#### Step 2: Set Environment Variables
Create a `.env` file in the `app` folder configured for Vertex AI:

```bash
echo "GOOGLE_GENAI_USE_VERTEXAI=TRUE" >> app/.env
echo "GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID" >> app/.env
echo "GOOGLE_CLOUD_LOCATION=us-central1" >> app/.env
echo "MAPS_API_KEY=YOUR_MAPS_API_KEY" >> app/.env
```

#### Step 3: Authenticate with Google Cloud
```bash
gcloud auth application-default login
```

#### Step 4: Install & Run
```bash
make install && make dev
```
Your agent is now running at `http://localhost:8501`.

<details>
<summary>🚀 Production Deployment with Agent Starter Pack</summary>

For production deployments with CI/CD, use the [Agent Starter Pack](https://goo.gle/agent-starter-pack) to create a deployment-ready project:

```bash
pip install --upgrade agent-starter-pack
agent-starter-pack create my-retail-agent -a adk@retail-ai-location-strategy
cd my-retail-agent && make deploy IAP=true
```

See the [Agent Starter Pack Documentation](https://googlecloudplatform.github.io/agent-starter-pack/) for full deployment options.
</details>

## Cloud Deployment

> **Note:** For production cloud deployment, use the [Agent Starter Pack](https://goo.gle/agent-starter-pack) to generate a deployment-ready project with CI/CD pipelines.

**Prerequisites:**
```bash
gcloud components update
gcloud config set project YOUR_PROJECT_ID
```

Deploy with the built-in [adk-web](https://github.com/google/adk-web) interface:

```bash
make deploy IAP=true
```

After deployment, grant users access to your IAP-protected service by following the [Manage User Access](https://cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run#manage_user_or_group_access) documentation.

For production deployments with CI/CD, see the [Agent Starter Pack Development Guide](https://googlecloudplatform.github.io/agent-starter-pack/guide/development-guide.html#b-production-ready-deployment-with-ci-cd).

---

## Agent Details

| Attribute | Description |
| :--- | :--- |
| **Interaction Type** | Workflow |
| **Complexity** | Advanced |
| **Agent Type** | Multi Agent (Sequential Pipeline) |
| **Components** | Multi-agent, Function calling, Web search, Google Maps API, Code execution, Image generation |
| **Vertical** | Retail / Real Estate |

<p align="center">
  <img src="assets/images/agent-tools.png" alt="Agent Tools Integration" width="700">
</p>

## Model Configuration

This agent supports multiple Gemini model families. Edit `app/config.py` to switch models based on your access and quota:

| Model Option | Text Models | Image Model | Notes |
|--------------|-------------|-------------|-------|
| **Gemini 2.5 Pro** (default) | `gemini-2.5-pro` | `gemini-3-pro-image-preview` | **Recommended** - Stable, production-ready |
| **Gemini 3 Pro Preview** | `gemini-3-pro-preview` | `gemini-3-pro-image-preview` | Recently launched - may throw 503 "model overloaded" errors |
| **Gemini 2.5 Flash** | `gemini-2.5-flash` | `gemini-2.0-flash-exp` | Fastest, lowest cost |

**Gemini 3 Documentation:**
- [Vertex AI - Get started with Gemini 3](https://cloud.google.com/vertex-ai/generative-ai/docs/start/get-started-with-gemini-3)
- [Google AI - Gemini 3 API](https://ai.google.dev/gemini-api/docs/gemini-3)

To use Gemini 3 text models, uncomment Option 2 in `app/config.py`:

```python
# app/config.py

# Comment out Option 1 (2.5 Pro)
# FAST_MODEL = "gemini-2.5-pro"
# ...

# Uncomment Option 2 (3 Pro Preview)
FAST_MODEL = "gemini-3-pro-preview"
PRO_MODEL = "gemini-3-pro-preview"
CODE_EXEC_MODEL = "gemini-3-pro-preview"
IMAGE_MODEL = "gemini-3-pro-image-preview"
```

> **Note:** If you encounter `503 UNAVAILABLE - model overloaded` errors with Gemini 3, switch back to Gemini 2.5 Pro for better reliability.

---

## AG-UI Frontend (Optional)

Want a richer experience beyond the default ADK web UI? This agent includes an optional **[AG-UI Protocol](https://docs.ag-ui.com/)** frontend built with [CopilotKit](https://docs.copilotkit.ai/) that provides:

- **Real-time Pipeline Timeline**: Watch the 7-stage analysis unfold with collapsible steps
- **Generative UI**: Rich visualizations appear in the chat as the agent works
- **Interactive Dashboard**: Location scores, competitor stats, market characteristics
- **Bidirectional State Sync**: Frontend and ADK agent share state in real-time

<p align="center">
  <img src="assets/images/ag-ui-sync.png" alt="AG-UI Bidirectional State Sync" width="650">
</p>

### Quick Start

```bash
# First time: Install frontend dependencies
make ag-ui-install

# Run both backend and frontend servers
make ag-ui
```

This starts:
- **Backend** at `http://localhost:8000` (FastAPI + ADK agent)
- **Frontend** at `http://localhost:3000` (Next.js + CopilotKit)

Open `http://localhost:3000` to see the interactive dashboard.

<p align="center">
  <img src="assets/gifs/ag-ui-demo.gif" alt="AG-UI Frontend Demo" width="700">
</p>

<details>
<summary>Manual Setup (Alternative)</summary>

```bash
# Terminal 1: Start the backend
cd app/frontend/backend
pip install -r requirements.txt
python main.py
# Runs at http://localhost:8000

# Terminal 2: Start the frontend
cd app/frontend
npm install
cp .env.local.example .env.local
npm run dev
# Runs at http://localhost:3000
```
</details>

See [app/frontend/README.md](app/frontend/README.md) for detailed frontend documentation.

---

## Example Prompts

| Region | Location | Business | Example Prompt |
|--------|----------|----------|----------------|
| Asia | Bangalore, India | Coffee Shop | "I want to open a coffee shop in Indiranagar, Bangalore" |
| Asia | Tokyo, Japan | Ramen Restaurant | "Analyze Shibuya, Tokyo for opening a ramen restaurant" |
| Asia | Singapore | Bubble Tea | "Where should I open a bubble tea shop in Orchard Road, Singapore?" |
| Americas | Austin, Texas | Fitness Studio | "Where should I open a fitness studio in Austin, Texas?" |
| Americas | Mexico City | Taco Restaurant | "Analyze Roma Norte, Mexico City for a taco restaurant" |
| Americas | Toronto, Canada | Craft Brewery | "Help me find a location for a craft brewery in Toronto's Distillery District" |
| Europe | London, UK | Bookstore Cafe | "Help me find the best location for a bookstore cafe in Shoreditch, London" |
| Europe | Berlin, Germany | Vegan Restaurant | "Analyze Berlin's Kreuzberg for opening a vegan restaurant" |
| Middle East | Dubai, UAE | Bakery | "I'm planning to open a bakery in Dubai Marina" |
| Oceania | Sydney, Australia | Juice Bar | "Analyze the market for a juice bar in Bondi Beach, Sydney" |

---

## Architecture

<p align="center">
  <img src="assets/images/pipeline-architecture.png" alt="Pipeline Architecture" width="700">
</p>

The pipeline is built as a `SequentialAgent` that orchestrates 7 specialized sub-agents, each handling a specific phase of the analysis.

### State Flow

Each agent reads from and writes to a shared session state, enabling seamless data flow between stages:

<p align="center">
  <img src="assets/images/data-flow.png" alt="Data Flow Between Agents" width="650">
</p>

---

## Project Structure

```
retail-ai-location-strategy/
│
├── Makefile                 # Build commands: dev, test, eval, deploy
├── pyproject.toml           # Python dependencies and package config
├── README.md                # This file
├── DEVELOPER_GUIDE.md       # Architecture deep-dive and implementation details
│
├── app/                     # Main agent package (ADK discovers root_agent here)
│   ├── __init__.py          # Exports root_agent for ADK CLI
│   ├── agent.py             # SequentialAgent pipeline orchestrating 7 sub-agents
│   ├── config.py            # Model selection (Gemini 2.5/3) and retry settings
│   ├── .env                 # API keys (create from .env.example)
│   │
│   ├── sub_agents/          # 7 specialized agents in execution order
│   │   ├── intake_agent/    # Stage 0: Parse user request → target_location, business_type
│   │   ├── market_research/ # Stage 1: Google Search for demographics and trends
│   │   ├── competitor_mapping/  # Stage 2A: Google Maps Places API for competitors
│   │   ├── gap_analysis/    # Stage 2B: Python code execution for viability scores
│   │   ├── strategy_advisor/    # Stage 3: Extended reasoning for recommendations
│   │   ├── report_generator/    # Stage 4A: HTML executive report generation
│   │   └── infographic_generator/  # Stage 4B: Gemini image generation
│   │
│   ├── tools/               # Custom function tools
│   │   ├── places_search.py         # Google Maps Places API wrapper
│   │   ├── html_report_generator.py # Builds styled HTML reports
│   │   └── image_generator.py       # Gemini native image generation
│   │
│   ├── schemas/             # Pydantic models for structured output
│   │   └── report_schema.py # LocationIntelligenceReport schema
│   │
│   ├── callbacks/           # Pipeline lifecycle hooks
│   │   └── pipeline_callbacks.py    # Logging and state extraction
│   │
│   └── frontend/            # Optional AG-UI dashboard (Next.js + CopilotKit)
│       ├── backend/         # FastAPI server bridging ADK ↔ AG-UI
│       └── src/             # React components for pipeline visualization
│
├── tests/                   # Testing infrastructure
│   ├── README.md            # Comprehensive testing guide
│   ├── conftest.py          # Shared pytest fixtures
│   ├── unit/                # Fast tests, no API calls (~2 seconds)
│   │   └── test_schemas.py  # Pydantic schema validation
│   ├── integration/         # Real API tests (~2-5 minutes)
│   │   └── test_agents.py   # Individual agent tests using Runner
│   └── evalsets/            # ADK evaluation datasets
│       ├── intake.evalset.json   # IntakeAgent parsing accuracy
│       └── pipeline.evalset.json # Full pipeline quality measurement
│
└── notebook/                # Original prototype
    └── retail_ai_location_strategy_gemini_3.ipynb
```

---

## Learn More

For detailed documentation, see **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)**:

- [The Business Problem](DEVELOPER_GUIDE.md#the-business-problem) - Why this exists
- [Architecture Deep Dive](DEVELOPER_GUIDE.md#architecture-deep-dive) - State flow and agent communication
- [Agents and Tools](DEVELOPER_GUIDE.md#agents-and-tools) - Sub-agents, tools, callbacks, schemas
- [Configuration](DEVELOPER_GUIDE.md#configuration) - Model selection and retry options
- [Troubleshooting](DEVELOPER_GUIDE.md#troubleshooting) - Common issues and fixes

## Troubleshooting

If you encounter issues while setting up or running this agent, here are some resources to help you troubleshoot:
- [ADK Documentation](https://google.github.io/adk-docs/): Comprehensive documentation for the Agent Development Kit
- [Vertex AI Authentication Guide](https://cloud.google.com/vertex-ai/docs/authentication): Detailed instructions for setting up authentication
- [Agent Starter Pack Troubleshooting](https://googlecloudplatform.github.io/agent-starter-pack/guide/troubleshooting.html): Common issues

---

## Testing

This project includes both **tests** (verify correctness) and **evaluations** (measure quality).

```bash
# Quick validation - test IntakeAgent parsing (~30 seconds)
make test-intake

# Test all individual agents (~2-5 minutes)
make test-agents

# Run unit tests only - no API calls (~2 seconds)
make test-unit

# Run ADK evaluations - measure response quality
make eval
```

For comprehensive testing documentation including how to add new tests, evaluation metrics, and production CI/CD guidance, see **[tests/README.md](tests/README.md)**.

---

## Authors

Created by [Lavi Nigam](https://github.com/lavinigam-gcp) and [Deepak Moonat](https://github.com/dmoonat).

Based on the original Retail AI Location Strategy notebook (see `notebook/` folder).

---

## Disclaimer

This agent sample is provided for illustrative purposes only. It serves as a basic example of an agent and a foundational starting point for individuals or teams to develop their own agents.

Users are solely responsible for any further development, testing, security hardening, and deployment of agents based on this sample. We recommend thorough review, testing, and the implementation of appropriate safeguards before using any derived agent in a live or critical system.

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.
