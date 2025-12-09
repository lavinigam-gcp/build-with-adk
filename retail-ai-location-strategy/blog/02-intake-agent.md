# Part 2: Request Parsing with IntakeAgent

By the end of this part, your agent will extract structured data from natural language requests.

**Input**: "I want to open a coffee shop in Indiranagar, Bangalore"
**Output**:
```json
{
  "target_location": "Indiranagar, Bangalore",
  "business_type": "coffee shop"
}
```

---

## The Challenge: Understanding User Intent

Users speak in natural language. They might say:

- "I want to open a coffee shop in Indiranagar, Bangalore"
- "Analyze the market for a new gym in downtown Seattle"
- "Help me find the best location for a bakery in Mumbai"
- "Where should I open my restaurant in San Francisco's Mission District?"

Our pipeline needs structured data:
- `target_location`: Where to analyze
- `business_type`: What kind of business

The **IntakeAgent** bridges this gap using Pydantic schemas for structured output.

---

## The Pydantic Schema

First, we define what structured output we want. Open `app/sub_agents/intake_agent/agent.py`:

```python
# app/sub_agents/intake_agent/agent.py
from typing import Optional
from pydantic import BaseModel, Field

class UserRequest(BaseModel):
    """Structured output for parsing user's location strategy request."""

    target_location: str = Field(
        description="The geographic location/area to analyze (e.g., 'Indiranagar, Bangalore', 'Manhattan, New York')"
    )
    business_type: str = Field(
        description="The type of business the user wants to open (e.g., 'coffee shop', 'bakery', 'gym', 'restaurant')"
    )
    additional_context: Optional[str] = Field(
        default=None,
        description="Any additional context or requirements mentioned by the user"
    )
```

**Why Pydantic?**

| Benefit | How It Helps |
|---------|--------------|
| Type safety | Gemini knows what types to output |
| Field descriptions | LLM understands what each field means |
| Validation | Automatic validation of output structure |
| IDE support | Autocomplete and type hints |

The `Field(description=...)` is critical - it tells the model what to put in each field.

---

## The Agent Instruction

The instruction uses few-shot examples to guide parsing:

```python
INTAKE_INSTRUCTION = """You are a request parser for a retail location intelligence system.

Your task is to extract the target location and business type from the user's request.

## Examples

User: "I want to open a coffee shop in Indiranagar, Bangalore"
→ target_location: "Indiranagar, Bangalore"
→ business_type: "coffee shop"

User: "Analyze the market for a new gym in downtown Seattle"
→ target_location: "downtown Seattle"
→ business_type: "gym"

User: "Help me find the best location for a bakery in Mumbai"
→ target_location: "Mumbai"
→ business_type: "bakery"

User: "Where should I open my restaurant in San Francisco's Mission District?"
→ target_location: "Mission District, San Francisco"
→ business_type: "restaurant"

## Instructions
1. Extract the geographic location mentioned by the user
2. Identify the type of business they want to open
3. Note any additional context or requirements

If the user doesn't specify a clear location or business type, make a reasonable inference or ask for clarification.
"""
```

**Few-shot prompting** makes parsing more reliable:
- Shows the model expected input/output patterns
- Covers edge cases (different phrasings, locations)
- Establishes consistent output format

---

## Building the IntakeAgent

Here's the complete agent definition:

```python
# app/sub_agents/intake_agent/agent.py
from google.adk.agents import LlmAgent
from google.genai import types

from ...config import FAST_MODEL, RETRY_INITIAL_DELAY, RETRY_ATTEMPTS

intake_agent = LlmAgent(
    name="IntakeAgent",
    model=FAST_MODEL,
    description="Parses user request to extract target location and business type",
    instruction=INTAKE_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    output_schema=UserRequest,
    output_key="parsed_request",
    after_agent_callback=after_intake,
)
```

**Key Parameters**:

| Parameter | Purpose |
|-----------|---------|
| `output_schema=UserRequest` | Forces Gemini to output valid `UserRequest` JSON |
| `output_key="parsed_request"` | Saves output to `state["parsed_request"]` |
| `after_agent_callback` | Post-processing hook |
| `generate_content_config` | Retry configuration for API errors |

### How `output_schema` Works

When you set `output_schema=UserRequest`:

1. ADK tells Gemini to output JSON matching the schema
2. Gemini returns structured JSON (not free text)
3. ADK validates the response against the Pydantic model
4. The validated object is saved to state using `output_key`

No manual JSON parsing needed!

---

## The After Callback

After parsing, we extract values to individual state keys for other agents:

```python
# app/sub_agents/intake_agent/agent.py
from google.adk.agents.callback_context import CallbackContext

def after_intake(callback_context: CallbackContext) -> Optional[types.Content]:
    """After intake, copy the parsed values to state for other agents."""
    parsed = callback_context.state.get("parsed_request", {})

    if isinstance(parsed, dict):
        # Extract values from parsed request
        callback_context.state["target_location"] = parsed.get("target_location", "")
        callback_context.state["business_type"] = parsed.get("business_type", "")
        callback_context.state["additional_context"] = parsed.get("additional_context", "")
    elif hasattr(parsed, "target_location"):
        # Handle Pydantic model
        callback_context.state["target_location"] = parsed.target_location
        callback_context.state["business_type"] = parsed.business_type
        callback_context.state["additional_context"] = parsed.additional_context or ""

    # Track intake stage completion
    stages = callback_context.state.get("stages_completed", [])
    stages.append("intake")
    callback_context.state["stages_completed"] = stages

    return None  # Allow normal flow to continue
```

**Why extract to individual keys?**

Other agents reference state variables like this:
```python
instruction="Research {target_location} for {business_type}..."
```

ADK injects values from state using `{variable}` syntax. Having individual keys makes this clean.

---

## Wiring IntakeAgent to Root Agent

In `app/agent.py`, the IntakeAgent is used as a tool:

```python
# app/agent.py
from google.adk.tools.agent_tool import AgentTool
from .sub_agents.intake_agent.agent import intake_agent

root_agent = Agent(
    model=FAST_MODEL,
    name=APP_NAME,
    instruction="""Your primary role is to orchestrate the retail location analysis.
1. Start by greeting the user.
2. Check if the TARGET_LOCATION and BUSINESS_TYPE have been provided.
3. If they are missing, ask the user clarifying questions.
4. Once you have the details, call the IntakeAgent tool to process them.
5. After IntakeAgent succeeds, delegate to the LocationStrategyPipeline.
Your main function is to manage this workflow conversationally.""",
    tools=[AgentTool(intake_agent)],  # IntakeAgent as a tool
    sub_agents=[location_strategy_pipeline],
)
```

**`AgentTool`** wraps an agent so it can be called like a function tool. The root agent can:
1. Talk to the user
2. Call IntakeAgent when needed
3. Access the parsed results from state

---

## Try It!

Run the agent:

```bash
make dev
```

Open `http://localhost:8501` and try different queries:

| Query | Expected Extraction |
|-------|---------------------|
| "Coffee shop in Bangalore" | location: "Bangalore", business: "coffee shop" |
| "Analyze downtown Seattle for a gym" | location: "downtown Seattle", business: "gym" |
| "Bakery in Mumbai" | location: "Mumbai", business: "bakery" |
| "Restaurant in Mission District, SF" | location: "Mission District, San Francisco", business: "restaurant" |

Watch the state panel - you'll see:
- `parsed_request`: The full structured output
- `target_location`: Extracted location
- `business_type`: Extracted business type

---

## Understanding the Flow

```
User: "Coffee shop in Indiranagar, Bangalore"
         │
         ▼
    ┌─────────────┐
    │ Root Agent  │ ── instruction says: "call IntakeAgent tool"
    └─────────────┘
         │
         ▼ calls AgentTool(intake_agent)
    ┌─────────────┐
    │IntakeAgent  │
    │             │ ← output_schema=UserRequest
    │             │ ← output_key="parsed_request"
    └─────────────┘
         │
         ▼ after_intake callback
    ┌─────────────┐
    │   State     │
    │             │ target_location: "Indiranagar, Bangalore"
    │             │ business_type: "coffee shop"
    └─────────────┘
```

---

## Handling Edge Cases

The instruction handles ambiguous inputs:

> "If the user doesn't specify a clear location or business type, make a reasonable inference or ask for clarification."

Examples:
- "I want to open a shop" → Agent infers or asks for location
- "Analyze Mumbai" → Agent infers business type or asks

The few-shot examples help the model handle variations gracefully.

---

## What You've Learned

In this part, you:

1. Created a Pydantic schema for structured output
2. Wrote a few-shot instruction for reliable parsing
3. Built IntakeAgent with `output_schema` and `output_key`
4. Added a callback to extract parsed values to state
5. Connected IntakeAgent to the root agent via AgentTool

---

## Next Up

We can now parse user requests reliably. But "coffee shop in Indiranagar, Bangalore" is just a starting point—we know *what* the user wants, but not *whether* it's a good idea. Is Indiranagar oversaturated with coffee shops? What are the demographics? What's the rental market like?

In [Part 3: Market Research](./03-market-research.md), we'll add the **MarketResearchAgent** that uses ADK's built-in `google_search` tool to answer these questions with live data. The agent will search for demographics, trends, foot traffic patterns, and rental rates—pulling current information that no training dataset contains.

---

## Quick Reference

| Concept | ADK Feature |
|---------|-------------|
| Structured output | `output_schema=PydanticModel` |
| Save to state | `output_key="key_name"` |
| Post-processing | `after_agent_callback` |
| Agent as tool | `AgentTool(agent)` |
| State access in callback | `callback_context.state["key"]` |

---

**Code files referenced in this part:**
- [`app/sub_agents/intake_agent/agent.py`](../app/sub_agents/intake_agent/agent.py) - IntakeAgent definition
- [`app/agent.py`](../app/agent.py) - Root agent with AgentTool

**ADK Documentation:**
- [Structured Output](https://google.github.io/adk-docs/agents/llm-agents/#structured-output)
- [Agent Callbacks](https://google.github.io/adk-docs/agents/callbacks/)
- [AgentTool](https://google.github.io/adk-docs/tools/agent-tool/)

---

<details>
<summary>Image Prompt for This Part</summary>

```json
{
  "image_type": "data_flow_diagram",
  "style": {
    "design": "clean, modern technical diagram",
    "color_scheme": "Google Cloud colors (blue #4285F4, red #EA4335, yellow #FBBC05, green #34A853) with white background",
    "layout": "horizontal flow",
    "aesthetic": "minimalist, vector-style"
  },
  "dimensions": {"aspect_ratio": "3:1", "recommended_width": 1000},
  "title": {"text": "Part 2: IntakeAgent - Request Parsing", "position": "top center"},
  "sections": [
    {
      "id": "input",
      "position": "left",
      "color": "#4285F4",
      "components": [
        {"name": "User Query", "icon": "speech bubble", "example": "I want to open a coffee shop in Indiranagar, Bangalore"}
      ]
    },
    {
      "id": "agent",
      "position": "center",
      "color": "#34A853",
      "components": [
        {"name": "IntakeAgent", "icon": "robot with clipboard", "features": ["Pydantic Schema", "Few-shot Examples"]}
      ]
    },
    {
      "id": "output",
      "position": "right",
      "color": "#FBBC05",
      "components": [
        {"name": "Structured Data", "icon": "JSON/code block", "fields": ["target_location", "business_type"]}
      ]
    }
  ],
  "connections": [
    {"from": "input", "to": "agent", "label": "Parse"},
    {"from": "agent", "to": "output", "label": "Extract"}
  ]
}
```

</details>
