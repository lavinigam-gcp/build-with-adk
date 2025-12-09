# Part 5: Quantitative Analysis with Code Execution

By the end of this part, your agent will write and run Python code to calculate viability scores.

**Input**: Market research + competitor data
**Output**: Calculated saturation indices, viability scores, and zone rankings

---

## When LLMs Need to Calculate

LLMs can reason about data, but they struggle with:
- Precise arithmetic
- Statistical calculations
- Complex multi-step computations
- Dynamic data analysis

The **GapAnalysisAgent** solves this by writing and executing Python code.

### The Precision Problem

Consider this: If an LLM needs to calculate a viability score based on:
- 15 competitors with various ratings
- Population density estimates
- Infrastructure quality factors
- Weighted multi-factor formulas

Asking the LLM to "think through" this leads to errors. Better to have it write code that computes exactly.

---

## BuiltInCodeExecutor

ADK provides `BuiltInCodeExecutor` for Gemini's native code execution:

```python
from google.adk.code_executors import BuiltInCodeExecutor

gap_analysis_agent = LlmAgent(
    # ...
    code_executor=BuiltInCodeExecutor(),
)
```

**What it does:**
1. Agent writes Python code
2. Gemini executes the code in a sandboxed environment
3. Output is captured and returned
4. Agent interprets the results

No server-side code execution needed - it happens within Gemini's infrastructure.

---

## The Analysis Instruction

The instruction guides the agent to write structured analysis code:

```python
GAP_ANALYSIS_INSTRUCTION = """You are a data scientist analyzing market opportunities using quantitative methods.

Your task is to perform advanced gap analysis on the data collected from previous stages.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Available Data

### MARKET RESEARCH FINDINGS (Part 1):
{market_research_findings}

### COMPETITOR ANALYSIS (Part 2):
{competitor_analysis}

## Your Mission
Write and execute Python code to perform comprehensive quantitative analysis.

## Analysis Steps

### Step 1: Parse Competitor Data
Extract from the competitor analysis:
- Competitor names and locations
- Ratings and review counts
- Zone/area classifications
- Business types (chain vs independent)

### Step 2: Calculate Zone Metrics
For each identified zone, compute:

**Basic Metrics:**
- Competitor count
- Competitor density (per estimated area)
- Average competitor rating
- Total review volume

**Opportunity Metrics:**
- Demand Signal: Based on population, income, infrastructure
- Market Saturation Index: (Competitors × Quality) / Demand
- Viability Score: Multi-factor weighted score

### Step 3: Zone Categorization
Classify each zone as:
- **SATURATED**: High competition, low opportunity
- **MODERATE**: Balanced market, moderate opportunity
- **OPPORTUNITY**: Low competition, high potential

### Step 4: Rank Top Zones
Create a weighted ranking considering:
- Low market saturation (weight: 30%)
- High demand signals (weight: 30%)
- Low chain dominance (weight: 15%)
- Infrastructure quality (weight: 15%)
- Manageable costs (weight: 10%)

## Code Guidelines
- Use pandas for data manipulation
- Print all results clearly formatted
- Include intermediate calculations for transparency
- Handle missing data gracefully

Execute the code and provide actionable strategic recommendations.
"""
```

**Key aspects:**
- Provides all previous data via state injection
- Specifies exact calculations to perform
- Gives weighting for scoring
- Requests clear output formatting

---

## Building the GapAnalysisAgent

```python
# app/sub_agents/gap_analysis/agent.py
from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor
from google.genai import types

from ...config import CODE_EXEC_MODEL, RETRY_INITIAL_DELAY, RETRY_ATTEMPTS
from ...callbacks import before_gap_analysis, after_gap_analysis

gap_analysis_agent = LlmAgent(
    name="GapAnalysisAgent",
    model=CODE_EXEC_MODEL,
    description="Performs quantitative gap analysis using Python code execution for zone rankings and viability scores",
    instruction=GAP_ANALYSIS_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    code_executor=BuiltInCodeExecutor(),
    output_key="gap_analysis",
    before_agent_callback=before_gap_analysis,
    after_agent_callback=after_gap_analysis,
)
```

**Key parameters:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `model` | `CODE_EXEC_MODEL` | Model optimized for code generation |
| `code_executor` | `BuiltInCodeExecutor()` | Enables code execution |
| `output_key` | `"gap_analysis"` | Saves results for next agent |

---

## Extracting Executed Code

The after callback extracts the Python code the agent wrote:

```python
# app/callbacks/pipeline_callbacks.py
def after_gap_analysis(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log completion of gap analysis and extract executed Python code."""
    gap = callback_context.state.get("gap_analysis", "")
    gap_len = len(gap) if isinstance(gap, str) else 0

    logger.info(f"STAGE 2B: COMPLETE - Gap analysis: {gap_len} characters")

    # Extract Python code from the gap_analysis content first
    extracted_code = _extract_python_code_from_content(gap)

    # Try to extract from invocation context (BuiltInCodeExecutor uses executable_code parts)
    if not extracted_code:
        extracted_code = _extract_code_from_invocation(callback_context)

    if extracted_code:
        callback_context.state["gap_analysis_code"] = extracted_code
        logger.info(f"  Extracted Python code: {len(extracted_code)} characters")

    stages = callback_context.state.get("stages_completed", [])
    stages.append("gap_analysis")
    callback_context.state["stages_completed"] = stages

    return None
```

### Why Extract the Code?

Having `gap_analysis_code` in state is useful for:
- Debugging: See exactly what was executed
- Reproducibility: Re-run the same analysis
- Transparency: Show users the methodology

### Helper Functions

```python
def _extract_python_code_from_content(content: str) -> str:
    """Extract Python code blocks from markdown content."""
    import re

    if not content:
        return ""

    # Match fenced code blocks with python language specifier
    code_blocks = []
    pattern = r'```(?:python|py)\s*\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

    for match in matches:
        code = match.strip()
        if code:
            code_blocks.append(code)

    return "\n\n# ---\n\n".join(code_blocks)


def _extract_code_from_invocation(callback_context: CallbackContext) -> str:
    """Extract Python code from invocation context session events."""
    code_blocks = []

    try:
        invocation = getattr(callback_context, '_invocation_context', None)
        if not invocation:
            return ""

        session = getattr(invocation, 'session', None)
        if not session:
            return ""

        events = getattr(session, 'events', None) or []

        for event in events:
            content = getattr(event, 'content', None)
            if not content:
                continue

            parts = getattr(content, 'parts', None) or []
            for part in parts:
                # Check for executable_code (Gemini native code execution)
                exec_code = getattr(part, 'executable_code', None)
                if exec_code:
                    code = getattr(exec_code, 'code', None)
                    if code and code.strip():
                        code_blocks.append(code.strip())

    except Exception as e:
        logger.warning(f"Error extracting code: {e}")

    return "\n\n# --- Next Code Block ---\n\n".join(code_blocks)
```

---

## Example: What the Agent Writes

Given competitor data, the agent might write:

```python
import pandas as pd

# Parse competitor data into DataFrame
competitors = [
    {"name": "Third Wave Coffee", "zone": "100 Feet Road", "rating": 4.5, "reviews": 2847, "is_chain": True},
    {"name": "Blue Tokai", "zone": "100 Feet Road", "rating": 4.6, "reviews": 987, "is_chain": True},
    {"name": "Dyu Art Cafe", "zone": "12th Main", "rating": 4.4, "reviews": 3241, "is_chain": False},
    # ... more competitors
]

df = pd.DataFrame(competitors)

# Calculate zone metrics
zone_metrics = df.groupby('zone').agg({
    'name': 'count',
    'rating': 'mean',
    'reviews': 'sum',
    'is_chain': 'mean'
}).rename(columns={
    'name': 'competitor_count',
    'rating': 'avg_rating',
    'reviews': 'total_reviews',
    'is_chain': 'chain_ratio'
})

# Calculate saturation index
zone_metrics['saturation_index'] = (
    zone_metrics['competitor_count'] * zone_metrics['avg_rating']
) / 10

# Calculate viability score (higher is better)
zone_metrics['viability_score'] = (
    (1 - zone_metrics['saturation_index'] / zone_metrics['saturation_index'].max()) * 0.4 +
    (1 - zone_metrics['chain_ratio']) * 0.3 +
    (zone_metrics['avg_rating'] / 5) * 0.3
) * 100

# Rank zones
zone_metrics = zone_metrics.sort_values('viability_score', ascending=False)

print("Zone Analysis Results:")
print(zone_metrics.round(2))
print("\nTop Recommended Zone:", zone_metrics.index[0])
print("Viability Score:", round(zone_metrics['viability_score'].iloc[0], 1))
```

**Output:**

```
Zone Analysis Results:
                    competitor_count  avg_rating  total_reviews  chain_ratio  saturation_index  viability_score
zone
Defence Colony                     2        4.25           412         0.00              0.85            78.5
12th Main                          4        4.35          4521         0.25              1.74            65.2
100 Feet Road                      6        4.50          6847         0.67              2.70            52.1

Top Recommended Zone: Defence Colony
Viability Score: 78.5
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
│  MarketResearchAgent → market_research_findings
│              │
│              ▼
│  CompetitorMappingAgent → competitor_analysis
│              │
│              ▼
│  ┌───────────────────────┐              │
│  │  GapAnalysisAgent     │ ◄── YOU ARE HERE
│  │  code_executor:       │              │
│  │    BuiltInCodeExecutor│              │
│  │  output_key:          │              │
│  │    "gap_analysis"     │              │
│  └───────────────────────┘              │
│              │                          │
│              ▼                          │
│  [Next: StrategyAdvisorAgent]           │
└─────────────────────────────────────────┘
```

---

## Try It!

Run the agent:

```bash
make dev
```

Try a query and watch the gap analysis stage. In the output, you'll see:
- Python code being executed
- DataFrames with zone metrics
- Viability scores and rankings

Check the state for:
- `gap_analysis`: The full analysis output
- `gap_analysis_code`: The Python code that was executed

---

## What You've Learned

In this part, you:

1. Used `BuiltInCodeExecutor` for dynamic code execution
2. Designed instructions that guide reliable code generation
3. Extracted executed code from the callback context
4. Saw how agents combine reasoning with computation

---

## Next Up

We now have quantitative data: viability scores, saturation indices, and zone rankings. But numbers alone don't make decisions. How do we weigh a zone with 78% viability but higher rent against one with 65% viability but prime foot traffic?

In [Part 6: Strategy Synthesis](./06-strategy-synthesis.md), we'll add the **StrategyAdvisorAgent** that uses *extended reasoning* to synthesize all findings into strategic recommendations. This agent doesn't just summarize—it thinks through trade-offs before responding, using Gemini's thinking capability to produce nuanced, consultant-grade insights.

You'll learn:
- **ThinkingConfig** for "think before responding" behavior
- Complex Pydantic schemas for structured reports
- Saving JSON artifacts in callbacks

---

## Quick Reference

| Feature | How to Use |
|---------|------------|
| Enable code execution | `code_executor=BuiltInCodeExecutor()` |
| Code-optimized model | Use `CODE_EXEC_MODEL` from config |
| Access executed code | Extract from callback context |
| State injection | Use `{market_research_findings}` in instruction |

---

**Code files referenced in this part:**
- [`app/sub_agents/gap_analysis/agent.py`](../app/sub_agents/gap_analysis/agent.py) - Agent
- [`app/callbacks/pipeline_callbacks.py`](../app/callbacks/pipeline_callbacks.py) - Code extraction

**ADK Documentation:**
- [Code Execution](https://google.github.io/adk-docs/tools/code-execution/)
- [BuiltInCodeExecutor](https://google.github.io/adk-docs/tools/code-execution/#built-in-code-executor)

---

<details>
<summary>Image Prompts for This Part</summary>

### Image 1: Pipeline Flow Diagram

```json
{
  "image_type": "code_execution_diagram",
  "style": {
    "design": "developer-focused, IDE aesthetic",
    "color_scheme": "Google Cloud colors with code syntax highlighting",
    "layout": "vertical flow",
    "aesthetic": "clean, modern"
  },
  "dimensions": {"aspect_ratio": "4:3", "recommended_width": 900},
  "title": {"text": "Part 5: GapAnalysisAgent - Code Execution", "position": "top center"},
  "sections": [
    {
      "id": "input",
      "position": "top",
      "color": "#E8F5E9",
      "components": [
        {"name": "competitor_analysis", "icon": "data"},
        {"name": "market_research_findings", "icon": "data"}
      ]
    },
    {
      "id": "agent",
      "position": "center",
      "color": "#34A853",
      "components": [
        {"name": "GapAnalysisAgent", "icon": "robot + code"},
        {"name": "BuiltInCodeExecutor", "icon": "terminal"}
      ]
    },
    {
      "id": "code",
      "position": "center-right",
      "color": "#263238",
      "components": [
        {"name": "Generated Python Code", "icon": "code editor", "snippet": "import pandas as pd\ndf = pd.DataFrame(...)\nviability = calculate_score(...)"}
      ]
    },
    {
      "id": "output",
      "position": "bottom",
      "color": "#FBBC05",
      "components": [
        {"name": "gap_analysis", "content": ["Viability: 87/100", "Saturation: Low", "Opportunity: High"]}
      ]
    }
  ],
  "connections": [
    {"from": "input", "to": "agent"},
    {"from": "agent", "to": "code", "label": "Generate Code"},
    {"from": "code", "to": "output", "label": "Execute"}
  ]
}
```

### Image 2: Sandboxed Code Execution Concept

```json
{
  "image_type": "concept_diagram",
  "style": {
    "design": "security-focused architecture diagram",
    "color_scheme": "Google Cloud colors (blue #4285F4, green #34A853) with security emphasis",
    "layout": "nested containers showing isolation",
    "aesthetic": "clean, professional, enterprise security style"
  },
  "dimensions": {"aspect_ratio": "16:9", "recommended_width": 1000},
  "title": {"text": "BuiltInCodeExecutor: Safe Code Execution", "position": "top center"},
  "concept": "Illustrate that code runs INSIDE Gemini's infrastructure, not on user's server",
  "sections": [
    {
      "id": "outer",
      "label": "Gemini Cloud Infrastructure",
      "position": "full",
      "color": "#E3F2FD",
      "border": "dashed #4285F4"
    },
    {
      "id": "sandbox",
      "label": "Sandboxed Environment",
      "position": "center within outer",
      "color": "#E8F5E9",
      "border": "solid #34A853",
      "icon": "shield/lock",
      "components": [
        {"name": "Python Runtime", "icon": "python logo"},
        {"name": "pandas, numpy", "icon": "packages"},
        {"name": "Isolated Execution", "icon": "container"},
        {"name": "No Network Access", "icon": "no-wifi"},
        {"name": "No File System", "icon": "no-folder"}
      ]
    },
    {
      "id": "user_app",
      "label": "Your Application",
      "position": "left outside",
      "color": "#FFF3E0",
      "components": [
        {"name": "ADK Agent", "description": "Sends code to Gemini"},
        {"name": "Receives Results", "description": "Output text only"}
      ]
    }
  ],
  "connections": [
    {"from": "user_app", "to": "sandbox", "label": "Code string →", "style": "arrow right"},
    {"from": "sandbox", "to": "user_app", "label": "← Output text", "style": "arrow left"}
  ],
  "annotations": [
    {"text": "No server-side execution needed", "position": "bottom left"},
    {"text": "Safe: Cannot access your systems", "position": "bottom right"}
  ]
}
```

</details>
