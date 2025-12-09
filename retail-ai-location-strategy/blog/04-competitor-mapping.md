# Part 4: Competitor Mapping with Google Maps API

By the end of this part, your agent will find real competitors using the Google Maps Places API.

**Input**: Market research findings + target location
**Output**: Real competitor data - names, ratings, reviews, locations

---

## From Research to Reality

Web search gives us market trends and demographics. But for competitors, we need ground-truth data:

- Actual business names and locations
- Star ratings and review counts
- Whether they're still operational
- Geographic clustering patterns

The **CompetitorMappingAgent** uses a custom tool that calls the Google Maps Places API.

---

## Building a Custom Tool

ADK tools are Python functions. The `search_places` tool wraps the Google Maps Places API.

### The Tool Definition

```python
# app/tools/places_search.py
import os
from google.adk.tools import ToolContext

def search_places(query: str, tool_context: ToolContext) -> dict:
    """Search for places using Google Maps Places API.

    This tool searches for businesses/places matching the query using the
    Google Maps Places API. It returns real competitor data including names,
    addresses, ratings, and other relevant information.

    Args:
        query: Search query combining business type and location.
               Example: "fitness studio near KR Puram, Bangalore, India"

    Returns:
        dict: A dictionary containing:
            - status: "success" or "error"
            - results: List of places found with details
            - count: Number of results found
            - error_message: Error details if status is "error"
    """
```

### Tool Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `query` | `str` | Search query the agent constructs |
| `tool_context` | `ToolContext` | Access to session state |

**Why `ToolContext`?**

It provides access to:
- `tool_context.state` - Session state (e.g., API keys)
- `tool_context.save_artifact()` - Save files like images/HTML

### The Implementation

```python
# app/tools/places_search.py
def search_places(query: str, tool_context: ToolContext) -> dict:
    try:
        import googlemaps

        # Get API key from session state first, then fall back to environment variable
        maps_api_key = tool_context.state.get("maps_api_key", "") or os.environ.get("MAPS_API_KEY", "")

        if not maps_api_key:
            return {
                "status": "error",
                "error_message": "Maps API key not found. Set MAPS_API_KEY environment variable.",
                "results": [],
                "count": 0,
            }

        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=maps_api_key)

        # Perform places search
        result = gmaps.places(query)

        # Extract and format results
        places = []
        for place in result.get("results", []):
            places.append({
                "name": place.get("name", "Unknown"),
                "address": place.get("formatted_address", place.get("vicinity", "N/A")),
                "rating": place.get("rating", 0),
                "user_ratings_total": place.get("user_ratings_total", 0),
                "price_level": place.get("price_level", "N/A"),
                "types": place.get("types", []),
                "business_status": place.get("business_status", "UNKNOWN"),
                "location": {
                    "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                    "lng": place.get("geometry", {}).get("location", {}).get("lng"),
                },
                "place_id": place.get("place_id", ""),
            })

        return {
            "status": "success",
            "results": places,
            "count": len(places),
            "next_page_token": result.get("next_page_token"),
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "results": [],
            "count": 0,
        }
```

### What the Tool Returns

Each place includes:

| Field | Description |
|-------|-------------|
| `name` | Business name |
| `address` | Full address |
| `rating` | Star rating (0-5) |
| `user_ratings_total` | Number of reviews |
| `price_level` | Price tier (1-4) |
| `business_status` | OPERATIONAL, CLOSED, etc. |
| `location` | Lat/lng coordinates |

---

## The Agent Instruction

The instruction guides the agent to use the tool effectively:

```python
COMPETITOR_MAPPING_INSTRUCTION = """You are a market intelligence analyst specializing in competitive landscape analysis.

Your task is to map and analyze all competitors in the target area using real Google Maps data.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Your Mission
Use the search_places function to get REAL data from Google Maps about existing competitors.

## Step 1: Search for Competitors
Call the search_places function with queries like:
- "{business_type} near {target_location}"
- Related business types in the same area

## Step 2: Analyze the Results
For each competitor found, note:
- Business name
- Location/address
- Rating (out of 5)
- Number of reviews
- Business status (operational, etc.)

## Step 3: Identify Patterns
Analyze the competitive landscape:

### Geographic Clustering
- Are competitors clustered in specific areas/zones?
- Which areas have high concentration vs sparse presence?
- Are there any "dead zones" with no competitors?

### Quality Segmentation
- Premium tier: High-rated (4.5+), likely higher prices
- Mid-market: Ratings 4.0-4.4
- Budget tier: Lower ratings or basic offerings
- Chain vs independent businesses

## Step 4: Strategic Assessment
Provide insights on:
- Which areas appear saturated with competitors?
- Which areas might be underserved opportunities?
- What quality gaps exist (e.g., no premium options)?

## Output Format
Provide a detailed competitor map with:
1. List of all competitors found with their details
2. Zone-by-zone breakdown of competition
3. Pattern analysis and clustering insights
4. Strategic opportunities and saturation warnings
"""
```

The instruction tells the agent:
1. **How** to call the tool
2. **What** to extract from results
3. **How** to analyze patterns
4. **What** insights to provide

---

## Building the CompetitorMappingAgent

```python
# app/sub_agents/competitor_mapping/agent.py
from google.adk.agents import LlmAgent
from google.genai import types

from ...config import FAST_MODEL, RETRY_INITIAL_DELAY, RETRY_ATTEMPTS
from ...tools import search_places
from ...callbacks import before_competitor_mapping, after_competitor_mapping

competitor_mapping_agent = LlmAgent(
    name="CompetitorMappingAgent",
    model=FAST_MODEL,
    description="Maps competitors using Google Maps Places API for ground-truth competitor data",
    instruction=COMPETITOR_MAPPING_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    tools=[search_places],
    output_key="competitor_analysis",
    before_agent_callback=before_competitor_mapping,
    after_agent_callback=after_competitor_mapping,
)
```

**Key points:**
- `tools=[search_places]` - The custom tool we built
- `output_key="competitor_analysis"` - Saves results for next agents

---

## The Callbacks

```python
# app/callbacks/pipeline_callbacks.py
def before_competitor_mapping(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log start of competitor mapping phase."""
    logger.info("=" * 60)
    logger.info("STAGE 2A: COMPETITOR MAPPING - Starting")
    logger.info("  Using Google Maps Places API for real competitor data...")
    logger.info("=" * 60)

    # Set current date for state injection
    callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d")
    callback_context.state["pipeline_stage"] = "competitor_mapping"

    return None


def after_competitor_mapping(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log completion of competitor mapping."""
    analysis = callback_context.state.get("competitor_analysis", "")
    analysis_len = len(analysis) if isinstance(analysis, str) else 0

    logger.info(f"STAGE 2A: COMPLETE - Competitor analysis: {analysis_len} characters")

    stages = callback_context.state.get("stages_completed", [])
    stages.append("competitor_mapping")
    callback_context.state["stages_completed"] = stages

    return None
```

---

## Exporting the Tool

Tools need to be exported from the tools package:

```python
# app/tools/__init__.py
from .places_search import search_places

__all__ = ["search_places"]
```

This allows importing as:
```python
from ...tools import search_places
```

---

## The Pipeline So Far

```
User Query
    │
    ▼
┌─────────────┐
│IntakeAgent  │ → target_location, business_type
└─────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│     LocationStrategyPipeline            │
├─────────────────────────────────────────┤
│  ┌───────────────────────┐              │
│  │MarketResearchAgent    │ → market_research_findings
│  │ tools: [google_search]│              │
│  └───────────────────────┘              │
│              │                          │
│              ▼                          │
│  ┌───────────────────────┐              │
│  │CompetitorMappingAgent │ ◄── YOU ARE HERE
│  │ tools: [search_places]│              │
│  │ output_key:           │              │
│  │   "competitor_        │              │
│  │    analysis"          │              │
│  └───────────────────────┘              │
│              │                          │
│              ▼                          │
│  [Next: GapAnalysisAgent]               │
└─────────────────────────────────────────┘
```

---

## Try It!

Run the agent:

```bash
make dev
```

Try: "I want to open a coffee shop in Indiranagar, Bangalore"

Watch for competitor data in the output. You'll see real business names like:
- Third Wave Coffee
- Starbucks
- Blue Tokai Coffee Roasters
- Local cafes with their actual ratings

The `competitor_analysis` state will contain the full analysis.

### Example Output

```
## Competitor Analysis: Coffee Shops in Indiranagar, Bangalore

### Competitors Found (15 total)

| Name | Rating | Reviews | Status |
|------|--------|---------|--------|
| Third Wave Coffee - Indiranagar | 4.5 | 2,847 | Operational |
| Starbucks - 100 Feet Road | 4.3 | 1,523 | Operational |
| Blue Tokai Coffee | 4.6 | 987 | Operational |
| Dyu Art Cafe | 4.4 | 3,241 | Operational |
| ... | ... | ... | ... |

### Geographic Patterns

**High Concentration Zones:**
- 100 Feet Road: 6 coffee shops within 500m
- 12th Main (CMH Road Junction): 4 coffee shops

**Lower Competition Areas:**
- Defence Colony side streets
- Areas near Indiranagar Metro Station (East)

### Quality Segmentation

**Premium (4.5+):** Third Wave Coffee, Blue Tokai, Dyu Art Cafe
**Mid-Market (4.0-4.4):** Starbucks, Cafe Coffee Day
**Budget/Casual:** Local cafes

### Strategic Insights

1. **Saturation Warning:** 100 Feet Road is highly saturated
2. **Opportunity:** Near Indiranagar Metro (East exit) has foot traffic but fewer options
3. **Quality Gap:** Limited premium specialty coffee near residential areas
```

---

## What You've Learned

In this part, you:

1. Built a custom tool that calls an external API
2. Used `ToolContext` to access state (API keys)
3. Structured tool return values for agent consumption
4. Wrote instructions that guide effective tool use
5. Saw real competitor data from Google Maps

---

## Next Up

We have qualitative data (market research) and quantitative data (competitor ratings, review counts). But how do we turn 15 competitors with various ratings across 4 zones into a recommendation? What's the saturation index? Which zone has the best viability score?

LLMs are great at reasoning, but they struggle with arithmetic. Ask an LLM to calculate a weighted average across 15 data points and it might hallucinate. Better to have it *write code* that computes exactly.

In [Part 5: Code Execution](./05-code-execution.md), we'll add the **GapAnalysisAgent** that writes and executes Python code to calculate viability scores, saturation indices, and zone rankings. The agent doesn't just reason about numbers—it writes pandas code, runs it in a sandboxed environment, and interprets the results.

You'll learn:
- **BuiltInCodeExecutor** for safe, sandboxed code execution
- Prompt design for reliable code generation
- Extracting executed code from callbacks for transparency

---

## Quick Reference

| Concept | Implementation |
|---------|---------------|
| Custom tool | `def tool_name(args, tool_context: ToolContext) -> dict` |
| Access state | `tool_context.state.get("key")` |
| Return format | Always return a dict with status, results, etc. |
| Register tool | `tools=[my_tool]` in agent definition |
| Export tool | Add to `__all__` in `__init__.py` |

---

**Code files referenced in this part:**
- [`app/tools/places_search.py`](../app/tools/places_search.py) - Custom tool
- [`app/sub_agents/competitor_mapping/agent.py`](../app/sub_agents/competitor_mapping/agent.py) - Agent
- [`app/callbacks/pipeline_callbacks.py`](../app/callbacks/pipeline_callbacks.py) - Callbacks

**ADK Documentation:**
- [Custom Tools](https://google.github.io/adk-docs/tools/function-tools/)
- [ToolContext](https://google.github.io/adk-docs/tools/function-tools/#tool-context)

---

<details>
<summary>Image Prompt for This Part</summary>

```json
{
  "image_type": "api_integration_diagram",
  "style": {
    "design": "clean, modern technical diagram",
    "color_scheme": "Google Cloud colors (blue #4285F4, red #EA4335, yellow #FBBC05, green #34A853) with white background",
    "layout": "horizontal with API callout",
    "aesthetic": "minimalist, vector-style"
  },
  "dimensions": {"aspect_ratio": "16:9", "recommended_width": 1100},
  "title": {"text": "Part 4: CompetitorMappingAgent - Google Maps Integration", "position": "top center"},
  "sections": [
    {
      "id": "previous",
      "position": "left",
      "color": "#E8F5E9",
      "components": [
        {"name": "IntakeAgent", "icon": "checkmark"},
        {"name": "MarketResearchAgent", "icon": "checkmark"},
        {"name": "market_research_findings", "status": "available"}
      ]
    },
    {
      "id": "current",
      "position": "center",
      "color": "#34A853",
      "components": [
        {"name": "CompetitorMappingAgent", "icon": "map pin"},
        {"name": "Custom Tool: search_places", "icon": "function/code"}
      ]
    },
    {
      "id": "api",
      "position": "below center",
      "color": "#EA4335",
      "components": [
        {"name": "Google Maps Places API", "icon": "Google Maps logo", "data": ["Names", "Ratings", "Reviews", "Addresses"]}
      ]
    },
    {
      "id": "output",
      "position": "right",
      "color": "#FBBC05",
      "components": [
        {"name": "competitor_analysis", "icon": "data table", "rows": ["Competitor 1: 4.5 stars", "Competitor 2: 4.2 stars", "..."]}
      ]
    }
  ],
  "connections": [
    {"from": "previous", "to": "current"},
    {"from": "current", "to": "api", "label": "API Call", "style": "dashed"},
    {"from": "api", "to": "current", "label": "Response"},
    {"from": "current", "to": "output"}
  ]
}
```

</details>
