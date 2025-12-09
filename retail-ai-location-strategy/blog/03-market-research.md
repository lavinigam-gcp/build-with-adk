# Part 3: Live Market Research with Google Search

By the end of this part, your agent will research real-time market data using Google Search.

**Input**: Parsed location and business type from IntakeAgent
**Output**: Live demographics, trends, and commercial viability analysis

---

## Why Live Data Matters

LLMs have training data cutoffs. They can't tell you:
- Current rental rates in a neighborhood
- Recent developments or infrastructure changes
- Today's competitive landscape
- Current consumer trends

The **MarketResearchAgent** uses Google Search to get fresh data.

### What We Research

| Focus Area | Data Points |
|------------|-------------|
| **Demographics** | Age distribution, income levels, lifestyle indicators |
| **Market Growth** | Population trends, new developments, infrastructure |
| **Industry Presence** | Existing businesses, consumer preferences, saturation |
| **Commercial Viability** | Foot traffic, rental costs, business environment |

---

## Using ADK's Built-in Google Search

ADK provides `google_search` as a built-in tool. No API key management needed - it uses Gemini's integrated search.

```python
# app/sub_agents/market_research/agent.py
from google.adk.tools import google_search
```

That's it. Import and use.

---

## The Research Instruction

The instruction guides what to search for and how to structure findings:

```python
MARKET_RESEARCH_INSTRUCTION = """You are a market research analyst specializing in retail location intelligence.

Your task is to research and validate the target market for a new business location.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Research Focus Areas

### 1. DEMOGRAPHICS
- Age distribution (identify key age groups)
- Income levels and purchasing power
- Lifestyle indicators (professionals, students, families)
- Population density and growth trends

### 2. MARKET GROWTH
- Population trends (growing, stable, declining)
- New residential and commercial developments
- Infrastructure improvements (metro, roads, tech parks)
- Economic growth indicators

### 3. INDUSTRY PRESENCE
- Existing similar businesses in the area
- Consumer preferences and spending patterns
- Market saturation indicators
- Success stories or failures of similar businesses

### 4. COMMERCIAL VIABILITY
- Foot traffic patterns (weekday vs weekend)
- Commercial real estate trends
- Typical rental costs (qualitative: low/medium/high)
- Business environment and regulations

## Instructions
1. Use Google Search to find current, verifiable data
2. Cite specific data points with sources where possible
3. Focus on information from the last 1-2 years for relevance
4. Be factual and data-driven, avoid speculation

## Output Format
Provide a structured analysis covering all four focus areas.
Conclude with a clear verdict: Is this a strong market for {business_type}? Why or why not?
Include specific recommendations for market entry strategy.
"""
```

### State Injection with `{variable}`

Notice the placeholders:
- `{target_location}` - Injected from state (set by IntakeAgent)
- `{business_type}` - Injected from state
- `{current_date}` - Injected from state (set by callback)

ADK automatically replaces these with actual values from session state.

---

## Building the MarketResearchAgent

```python
# app/sub_agents/market_research/agent.py
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.genai import types

from ...config import FAST_MODEL, RETRY_INITIAL_DELAY, RETRY_ATTEMPTS
from ...callbacks import before_market_research, after_market_research

market_research_agent = LlmAgent(
    name="MarketResearchAgent",
    model=FAST_MODEL,
    description="Researches market viability using Google Search for real-time demographics, trends, and commercial data",
    instruction=MARKET_RESEARCH_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    tools=[google_search],
    output_key="market_research_findings",
    before_agent_callback=before_market_research,
    after_agent_callback=after_market_research,
)
```

**Key Parameters**:

| Parameter | Purpose |
|-----------|---------|
| `tools=[google_search]` | Gives agent access to live web search |
| `output_key="market_research_findings"` | Saves findings to state for next agents |
| `before_agent_callback` | Setup before agent runs |
| `after_agent_callback` | Cleanup/logging after agent completes |

---

## The Before Callback

The `before_market_research` callback sets up the agent:

```python
# app/callbacks/pipeline_callbacks.py
from datetime import datetime
from google.adk.agents.callback_context import CallbackContext

def before_market_research(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log start of market research phase and initialize pipeline tracking."""
    logger.info("=" * 60)
    logger.info("STAGE 1: MARKET RESEARCH - Starting")
    logger.info(f"  Target Location: {callback_context.state.get('target_location', 'Not set')}")
    logger.info(f"  Business Type: {callback_context.state.get('business_type', 'Not set')}")
    logger.info("=" * 60)

    # Set current date for state injection in agent instruction
    callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d")

    # Initialize pipeline tracking
    callback_context.state["pipeline_stage"] = "market_research"
    callback_context.state["pipeline_start_time"] = datetime.now().isoformat()

    if "stages_completed" not in callback_context.state:
        callback_context.state["stages_completed"] = []

    return None  # Allow agent to proceed
```

**What it does**:
1. Logs the stage start with target details
2. Sets `current_date` for the instruction's `{current_date}` placeholder
3. Initializes pipeline tracking variables
4. Returns `None` to allow the agent to proceed

### Why Set `current_date` Here?

The instruction says "Focus on information from the last 1-2 years." By injecting today's date, the agent knows what "recent" means.

---

## The After Callback

```python
# app/callbacks/pipeline_callbacks.py
def after_market_research(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log completion of market research and update tracking."""
    findings = callback_context.state.get("market_research_findings", "")
    findings_len = len(findings) if isinstance(findings, str) else 0

    logger.info(f"STAGE 1: COMPLETE - Market research findings: {findings_len} characters")

    # Update stages completed
    stages = callback_context.state.get("stages_completed", [])
    stages.append("market_research")
    callback_context.state["stages_completed"] = stages

    return None
```

**What it does**:
1. Logs completion with output size
2. Tracks that this stage is complete

---

## Wiring into the Pipeline

In `app/agent.py`, the agent is added to the SequentialAgent:

```python
# app/agent.py
from google.adk.agents import SequentialAgent
from .sub_agents.market_research.agent import market_research_agent

location_strategy_pipeline = SequentialAgent(
    name="LocationStrategyPipeline",
    description="Comprehensive retail location strategy analysis pipeline...",
    sub_agents=[
        market_research_agent,        # Stage 1: Market research with search
        competitor_mapping_agent,     # Stage 2A: Competitor mapping with Maps
        gap_analysis_agent,           # Stage 2B: Gap analysis with code exec
        strategy_advisor_agent,       # Stage 3: Strategy synthesis
        artifact_generation_pipeline, # Stage 4: Artifacts (parallel)
    ],
)
```

`SequentialAgent` runs agents in order, passing state between them.

---

## The Pipeline So Far

```
User Query
    │
    ▼
┌─────────────┐
│ Root Agent  │ ── calls IntakeAgent
└─────────────┘
    │
    ▼
┌─────────────┐
│IntakeAgent  │ ── output_key="parsed_request"
└─────────────┘    → state: target_location, business_type
    │
    ▼
┌─────────────────────────────────────────┐
│     LocationStrategyPipeline            │
│         (SequentialAgent)               │
├─────────────────────────────────────────┤
│  ┌───────────────────────┐              │
│  │MarketResearchAgent    │ ◄── YOU ARE HERE
│  │ tools: [google_search]│              │
│  │ output_key:           │              │
│  │   "market_research_   │              │
│  │    findings"          │              │
│  └───────────────────────┘              │
│              │                          │
│              ▼                          │
│  [Next: CompetitorMappingAgent]         │
└─────────────────────────────────────────┘
```

---

## Try It!

Run the agent:

```bash
make dev
```

Open `http://localhost:8501` and try:
- "I want to open a coffee shop in Indiranagar, Bangalore"

Watch the output - you'll see:
1. IntakeAgent extracts location and business type
2. MarketResearchAgent searches the web
3. Real demographic and market data appears

In the state panel, look for `market_research_findings` - it contains the full research output.

### Example Output

For "coffee shop in Indiranagar, Bangalore", you might see:

```
## Demographics Analysis

Indiranagar is one of Bangalore's most affluent neighborhoods...
- Population: High density, predominantly young professionals (25-40)
- Income level: Upper-middle to high income bracket
- Lifestyle: Tech professionals, startup founders, urban millennials

## Market Growth

Recent developments include:
- Metro Purple Line connectivity (operational since 2017)
- New coworking spaces and tech offices
- Increasing commercial real estate investment

## Industry Presence

Coffee culture is strong with existing players:
- Third Wave Coffee: 2 locations
- Blue Tokai: 1 location
- Starbucks: 2 locations
- Multiple local specialty cafes

## Commercial Viability

- High foot traffic, especially evenings and weekends
- Rental costs: Premium tier (Rs 150-200/sq ft)
- Strong purchasing power for specialty coffee

## Verdict

Strong market for coffee shop. High disposable income, established coffee culture, and young professional demographic create favorable conditions. However, competition is significant - differentiation strategy required.
```

---

## What You've Learned

In this part, you:

1. Used ADK's built-in `google_search` tool
2. Created state-injected instructions with `{variable}` syntax
3. Added before/after callbacks for logging and tracking
4. Wired the agent into a SequentialAgent pipeline
5. Saw real-time search results in your agent

---

## Next Up

The market research tells us about the *opportunity*, but we're missing something critical: who exactly is already there? Search results mention "Third Wave Coffee" and "Blue Tokai," but how many locations do they have? What are their ratings? Where exactly are they positioned?

In [Part 4: Competitor Mapping](./04-competitor-mapping.md), we'll build a **custom tool** that queries the Google Maps Places API for real competitor data. Instead of relying on search snippets, we'll get structured data—competitor names, ratings, review counts, and addresses—directly from Google Maps.

You'll learn:
- How to create custom function tools with Python functions
- Using `ToolContext` to access session state from within tools
- Integrating external APIs with proper error handling

---

## Quick Reference

| Feature | How to Use |
|---------|------------|
| Built-in search | `from google.adk.tools import google_search` |
| State injection | Use `{variable_name}` in instruction |
| Before callback | `before_agent_callback=function` |
| After callback | `after_agent_callback=function` |
| Sequential pipeline | `SequentialAgent(sub_agents=[...])` |

---

**Code files referenced in this part:**
- [`app/sub_agents/market_research/agent.py`](../app/sub_agents/market_research/agent.py) - MarketResearchAgent
- [`app/callbacks/pipeline_callbacks.py`](../app/callbacks/pipeline_callbacks.py) - Callbacks
- [`app/agent.py`](../app/agent.py) - Pipeline definition

**ADK Documentation:**
- [Built-in Tools](https://google.github.io/adk-docs/tools/built-in-tools/)
- [SequentialAgent](https://google.github.io/adk-docs/agents/workflow-agents/#sequentialagent)
- [Callbacks](https://google.github.io/adk-docs/agents/callbacks/)

---

<details>
<summary>Image Prompt for This Part</summary>

```json
{
  "image_type": "pipeline_step_diagram",
  "style": {
    "design": "clean, modern technical diagram",
    "color_scheme": "Google Cloud colors (blue #4285F4, red #EA4335, yellow #FBBC05, green #34A853) with white background",
    "layout": "horizontal flow with tool callout",
    "aesthetic": "minimalist, vector-style"
  },
  "dimensions": {"aspect_ratio": "16:9", "recommended_width": 1100},
  "title": {"text": "Part 3: MarketResearchAgent - Live Web Search", "position": "top center"},
  "sections": [
    {
      "id": "previous",
      "position": "left",
      "color": "#E8F5E9",
      "components": [
        {"name": "IntakeAgent", "icon": "checkmark", "status": "completed"},
        {"name": "Parsed Request", "fields": ["target_location", "business_type"]}
      ]
    },
    {
      "id": "current",
      "position": "center",
      "color": "#34A853",
      "components": [
        {"name": "MarketResearchAgent", "icon": "magnifying glass", "status": "active"},
        {"name": "Tool: google_search", "icon": "Google search icon"}
      ]
    },
    {
      "id": "output",
      "position": "right",
      "color": "#FBBC05",
      "components": [
        {"name": "market_research_findings", "icon": "document", "content": ["Demographics", "Trends", "Foot Traffic", "Rental Rates"]}
      ]
    }
  ],
  "connections": [
    {"from": "previous", "to": "current", "label": "State: location, business"},
    {"from": "current", "to": "output", "label": "Findings"}
  ]
}
```

</details>
