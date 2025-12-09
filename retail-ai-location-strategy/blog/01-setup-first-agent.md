# Part 1: Setup and Your First Agent

By the end of this part, you'll have a working agent running on `adk-web` at `http://localhost:8501`.

## The Problem We're Solving

Opening a physical retail location is a high-stakes investment plagued by fragmented data:

- **Demographics** are on Wikipedia
- **Competitors** are on Google Maps
- **Rent trends** are in news articles
- **Analysis** needs to happen in spreadsheets

Validating a single location typically takes 1-2 weeks of manual research. Decisions end up based on "gut feeling" rather than data.

### What We'll Build

Over this series, we'll build an AI pipeline that unifies these data sources into a coherent strategy in minutes:

```
User: "I want to open a coffee shop in Indiranagar, Bangalore"
                    ↓
            [8-Agent Pipeline]
                    ↓
Output: Strategic report + infographic + podcast audio
```

The pipeline will:
1. Parse the user's request
2. Search the web for demographics and trends
3. Query Google Maps for real competitors
4. Execute Python code to calculate viability scores
5. Synthesize strategic recommendations
6. Generate HTML reports, infographics, and audio summaries

But first, let's get a basic agent running.

---

## Prerequisites

Before starting, ensure you have:

- **[Python 3.10-3.12](https://www.python.org/downloads/)** - ADK requires this version range
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package manager (recommended)
- **[Google AI Studio API Key](https://aistudio.google.com/app/apikey)** - For Gemini access
- **[Google Maps API Key](https://console.cloud.google.com/apis/credentials)** - With Places API enabled

---

## Clone and Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/lavinigam-gcp/build-with-adk.git
cd build-with-adk/retail-ai-location-strategy
```

### Step 2: Set Environment Variables

Create a `.env` file in the `app` folder:

```bash
echo "GOOGLE_GENAI_USE_VERTEXAI=FALSE" >> app/.env
echo "GOOGLE_API_KEY=YOUR_AI_STUDIO_API_KEY" >> app/.env
echo "MAPS_API_KEY=YOUR_MAPS_API_KEY" >> app/.env
```

> **Tip**: See `app/.env.example` for a template with all available options.

---

## Project Structure Tour

The project follows ADK conventions. Here's what matters:

```
retail-ai-location-strategy/
├── Makefile                 # Build commands: dev, test, deploy
├── pyproject.toml           # Python dependencies
│
├── app/                     # ADK discovers agents here
│   ├── __init__.py          # Exports root_agent (required!)
│   ├── agent.py             # Root agent definition
│   ├── config.py            # Model and retry settings
│   ├── .env                 # Your API keys
│   │
│   ├── sub_agents/          # Specialized agents (we'll add these)
│   ├── tools/               # Custom function tools
│   ├── callbacks/           # Lifecycle hooks
│   └── schemas/             # Pydantic output schemas
```

### The Critical Files

**`app/__init__.py`** - ADK looks for `root_agent` here:

```python
# app/__init__.py
from app import agent
from app.agent import root_agent

__all__ = ["agent", "root_agent"]
```

This is how ADK discovers your agent. The `root_agent` must be exported.

**`app/config.py`** - Model configuration:

```python
# app/config.py (key sections)

# Detect authentication mode
USE_VERTEX_AI = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").upper() == "TRUE"

# Model Configuration
FAST_MODEL = "gemini-2.5-pro"
PRO_MODEL = "gemini-2.5-pro"
CODE_EXEC_MODEL = "gemini-2.5-pro"
IMAGE_MODEL = "gemini-3-pro-image-preview"
TTS_MODEL = "gemini-2.5-flash-preview-tts"

# Retry Configuration
RETRY_INITIAL_DELAY = 5
RETRY_ATTEMPTS = 5
RETRY_MAX_DELAY = 60

APP_NAME = "retail_location_strategy"
```

The config supports both Google AI Studio (local dev) and Vertex AI (production).

---

## Understanding the Root Agent

Let's look at what makes up our root agent. Open `app/agent.py`:

```python
# app/agent.py
from google.adk.agents import SequentialAgent
from google.adk.agents.llm_agent import Agent
from google.adk.tools.agent_tool import AgentTool

from .config import FAST_MODEL, APP_NAME

# The root agent orchestrates the pipeline
root_agent = Agent(
    model=FAST_MODEL,
    name=APP_NAME,
    description='A strategic partner for retail businesses, guiding them to optimal physical locations.',
    instruction="""Your primary role is to orchestrate the retail location analysis.
1. Start by greeting the user.
2. Check if the TARGET_LOCATION and BUSINESS_TYPE have been provided.
3. If they are missing, ask the user clarifying questions.
4. Once you have the details, call the IntakeAgent tool to process them.
5. After IntakeAgent succeeds, delegate to the LocationStrategyPipeline.
Your main function is to manage this workflow conversationally.""",
    sub_agents=[location_strategy_pipeline],
    tools=[AgentTool(intake_agent)],
)
```

Key components:

| Parameter | Purpose |
|-----------|---------|
| `model` | The Gemini model to use |
| `name` | Agent identifier |
| `description` | What the agent does (shown in UI) |
| `instruction` | The system prompt guiding behavior |
| `sub_agents` | Agents this agent can delegate to |
| `tools` | Tools this agent can call |

The complete agent has `sub_agents` and `tools` wired up, but let's start simpler.

---

## Your First Agent (Simplified)

To understand the structure, here's what a minimal agent looks like:

```python
# Minimal root_agent (what we're building toward)
from google.adk.agents.llm_agent import Agent

root_agent = Agent(
    model="gemini-2.5-pro",
    name="retail_location_strategy",
    description="Helps find optimal retail locations",
    instruction="""You help users find locations for retail businesses.

When a user provides a location and business type, acknowledge them and
explain that you'll analyze the market for them.

For now, just have a conversation. We'll add analysis capabilities next.""",
)
```

This is just a conversational agent - no tools, no sub-agents yet. But it works!

---

## Run It!

### Step 3: Install Dependencies

From the `retail-ai-location-strategy` directory:

```bash
make install
```

This uses `uv` to install all dependencies from `pyproject.toml`.

### Step 4: Start the Development Server

```bash
make dev
```

This runs `adk web app --port 8501`.

### What You'll See

1. Open `http://localhost:8501` in your browser
2. Select **"app"** from the agent dropdown
3. Try a query like: *"I want to open a coffee shop in Bangalore"*

The agent responds and starts processing your request. You'll notice it does much more than just chat—it searches the web, finds competitors, and generates reports.

**Why does the full pipeline run?** You cloned a complete, working agent. The codebase already contains all the sub-agents, tools, and callbacks we'll explore in this series. This is intentional: you get a working end-to-end example immediately, then we'll dissect each component to understand how it works.

Think of this series as a "reverse engineering" journey. You have the finished product; now we'll understand how each piece contributes to the whole. By Part 7, you'll understand every agent, tool, and callback that makes this pipeline work.

---

## What's Happening Under the Hood

When you send a message:

1. **ADK** receives the request
2. **Root Agent** processes it using the model
3. Based on the `instruction`, it decides what to do
4. Response streams back to the UI

Right now, the complete agent:
- Uses `IntakeAgent` to parse your request
- Delegates to `LocationStrategyPipeline`
- Runs 5 sequential stages + parallel artifact generation

In the next parts, we'll build each stage from scratch.

---

## Configuration Options

### Switching Models

Edit `app/config.py` to try different models:

```python
# Option 1: Gemini 2.5 Pro (RECOMMENDED - stable)
FAST_MODEL = "gemini-2.5-pro"

# Option 2: Gemini 3 Pro Preview (latest, may have availability issues)
# FAST_MODEL = "gemini-3-pro-preview"

# Option 3: Gemini 2.5 Flash (fastest, lowest cost)
# FAST_MODEL = "gemini-2.5-flash"
```

### Using Vertex AI (Production)

For production, switch to Vertex AI:

```bash
# app/.env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

And authenticate:
```bash
gcloud auth application-default login
```

---

## What You've Learned

In this part, you:

1. Understood the problem: fragmented retail location data
2. Set up the development environment
3. Learned the project structure and ADK conventions
4. Saw how `root_agent` is defined and exported
5. Ran the agent on `adk-web`

---

## Troubleshooting

### "ModuleNotFoundError" or Import Errors

Ensure you ran `make install` from the correct directory:
```bash
cd build-with-adk/retail-ai-location-strategy
make install
```

### "GOOGLE_API_KEY not set" or Authentication Errors

Your `.env` file must be inside the `app/` folder:
```bash
ls app/.env  # Should exist
```

If missing, create it:
```bash
echo "GOOGLE_GENAI_USE_VERTEXAI=FALSE" > app/.env
echo "GOOGLE_API_KEY=your-actual-key" >> app/.env
echo "MAPS_API_KEY=your-maps-key" >> app/.env
```

### Agent Shows "Model not found" or 404 Errors

Some preview models have limited availability. Switch to stable models in `app/config.py`:
```python
FAST_MODEL = "gemini-2.5-pro"  # Stable
# FAST_MODEL = "gemini-3-pro-preview"  # May have availability issues
```

### Port 8501 Already in Use

Kill the existing process or use a different port:
```bash
make dev PORT=8502
```

---

## Next Up

Now that you have a working agent, the question is: how does it understand what you're asking for? When you say "coffee shop in Bangalore," how does the agent know to extract "coffee shop" as the business type and "Bangalore" as the location?

In [Part 2: IntakeAgent](./02-intake-agent.md), we'll explore how the **IntakeAgent** uses Pydantic schemas and few-shot prompting to parse natural language into structured data. This is the foundation that enables every subsequent agent to work with clean, reliable inputs.

The agent transforms:
- *"I want to open a coffee shop in Bangalore"*

Into structured output:
```json
{
  "target_location": "Bangalore, India",
  "business_type": "coffee shop"
}
```

---

## Quick Reference

| Command | What It Does |
|---------|--------------|
| `make install` | Install dependencies |
| `make dev` | Run development server at :8501 |
| `make test` | Run all tests |

---

**Code files referenced in this part:**
- [`app/__init__.py`](../app/__init__.py) - Agent export
- [`app/config.py`](../app/config.py) - Model configuration
- [`app/agent.py`](../app/agent.py) - Root agent definition

**ADK Documentation:**
- [Getting Started](https://google.github.io/adk-docs/get-started/quickstart/)
- [Agent Types](https://google.github.io/adk-docs/agents/)

---

<details>
<summary>Image Prompt for This Part</summary>

```json
{
  "image_type": "setup_diagram",
  "style": {
    "design": "clean, modern, professional software architecture diagram",
    "color_scheme": "Google Cloud colors (blue #4285F4, red #EA4335, yellow #FBBC05, green #34A853) with white background",
    "layout": "left to right flow",
    "aesthetic": "minimalist, vector-style icons, clear hierarchy"
  },
  "dimensions": {"aspect_ratio": "16:9", "recommended_width": 1200},
  "title": {"text": "Part 1: Setup and First Agent", "position": "top center"},
  "sections": [
    {
      "id": "prerequisites",
      "position": "left",
      "color": "#4285F4",
      "components": [
        {"name": "Python 3.10+", "icon": "python logo"},
        {"name": "uv", "icon": "package manager"},
        {"name": "API Keys", "icon": "key"}
      ]
    },
    {
      "id": "agent",
      "position": "center",
      "color": "#34A853",
      "components": [
        {"name": "Root Agent", "icon": "robot/agent", "description": "Simple conversational agent"}
      ]
    },
    {
      "id": "output",
      "position": "right",
      "color": "#FBBC05",
      "components": [
        {"name": "ADK Web UI", "icon": "browser", "port": ":8501", "description": "Chat interface"}
      ]
    }
  ],
  "connections": [
    {"from": "prerequisites", "to": "agent", "label": "make install"},
    {"from": "agent", "to": "output", "label": "make dev"}
  ]
}
```

</details>
