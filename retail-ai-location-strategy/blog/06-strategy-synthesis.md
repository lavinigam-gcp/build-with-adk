# Part 6: Strategic Synthesis with Extended Reasoning

By the end of this part, your agent will synthesize all data into actionable strategic recommendations.

**Input**: All previous findings (market research, competitors, gap analysis)
**Output**: Structured `LocationIntelligenceReport` with recommendations

---

## The Synthesis Challenge

At this point, we have:
- Market research with demographics and trends
- Real competitor data with ratings and locations
- Quantitative analysis with viability scores

Now we need to:
- Weigh competing factors
- Handle trade-offs (e.g., high foot traffic vs. high competition)
- Generate specific, actionable recommendations

This requires deep reasoning - not just pattern matching.

---

## Extended Reasoning with ThinkingConfig

ADK supports Gemini's "thinking mode" which allocates compute budget for complex reasoning:

```python
from google.adk.planners import BuiltInPlanner
from google.genai.types import ThinkingConfig

strategy_advisor_agent = LlmAgent(
    # ...
    planner=BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=False,  # Must be False when using output_schema
            thinking_budget=-1,  # -1 means unlimited thinking budget
        )
    ),
)
```

**ThinkingConfig Parameters:**

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `include_thoughts` | `False` | Don't include thinking in output (required for `output_schema`) |
| `thinking_budget` | `-1` | Unlimited thinking tokens |
| `thinking_budget` | `1000` | Limit to 1000 thinking tokens |

**Why Use Thinking Mode?**

For synthesis tasks, the model needs to:
1. Compare multiple zones
2. Weigh competing factors
3. Consider trade-offs
4. Reason about uncertainties

Thinking mode improves quality for these complex decisions.

---

## The Complex Pydantic Schema

The output is a comprehensive `LocationIntelligenceReport`:

```python
# app/schemas/report_schema.py
from typing import List
from pydantic import BaseModel, Field


class StrengthAnalysis(BaseModel):
    """Detailed strength with evidence."""
    factor: str = Field(description="The strength factor name")
    description: str = Field(description="Description of the strength")
    evidence_from_analysis: str = Field(description="Evidence from the analysis")


class ConcernAnalysis(BaseModel):
    """Detailed concern with mitigation strategy."""
    risk: str = Field(description="The risk or concern name")
    description: str = Field(description="Description of the concern")
    mitigation_strategy: str = Field(description="Strategy to mitigate this concern")


class CompetitionProfile(BaseModel):
    """Competition characteristics in the zone."""
    total_competitors: int
    density_per_km2: float
    chain_dominance_pct: float
    avg_competitor_rating: float
    high_performers_count: int


class MarketCharacteristics(BaseModel):
    """Market fundamentals for the zone."""
    population_density: str  # Low/Medium/High
    income_level: str  # Low/Medium/High
    infrastructure_access: str
    foot_traffic_pattern: str
    rental_cost_tier: str  # Low/Medium/High


class LocationRecommendation(BaseModel):
    """Complete recommendation for a specific location."""
    location_name: str
    area: str
    overall_score: int = Field(ge=0, le=100)  # 0-100
    opportunity_type: str  # e.g., "Metro First-Mover"
    strengths: List[StrengthAnalysis]
    concerns: List[ConcernAnalysis]
    competition: CompetitionProfile
    market: MarketCharacteristics
    best_customer_segment: str
    estimated_foot_traffic: str
    next_steps: List[str]


class AlternativeLocation(BaseModel):
    """Brief summary of alternative location."""
    location_name: str
    area: str
    overall_score: int = Field(ge=0, le=100)
    opportunity_type: str
    key_strength: str
    key_concern: str
    why_not_top: str


class LocationIntelligenceReport(BaseModel):
    """Complete location intelligence analysis report."""
    target_location: str
    business_type: str
    analysis_date: str
    market_validation: str  # Overall summary
    total_competitors_found: int
    zones_analyzed: int
    top_recommendation: LocationRecommendation
    alternative_locations: List[AlternativeLocation]
    key_insights: List[str]  # 4-6 insights
    methodology_summary: str
```

**Schema Benefits:**
- Forces complete, structured output
- Every field has a description guiding the model
- Validation constraints (e.g., `ge=0, le=100` for scores)
- Nested models for complex structures

---

## The Agent Instruction

The instruction guides comprehensive synthesis:

```python
STRATEGY_ADVISOR_INSTRUCTION = """You are a senior strategy consultant synthesizing location intelligence findings.

Your task is to analyze all research and provide actionable strategic recommendations.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Available Data

### MARKET RESEARCH FINDINGS (Part 1):
{market_research_findings}

### COMPETITOR ANALYSIS (Part 2A):
{competitor_analysis}

### GAP ANALYSIS (Part 2B):
{gap_analysis}

## Your Mission
Synthesize all findings into a comprehensive strategic recommendation.

## Analysis Framework

### 1. Data Integration
Review all inputs carefully:
- Market research demographics and trends
- Competitor locations, ratings, and patterns
- Quantitative gap analysis metrics and zone rankings

### 2. Strategic Synthesis
For each promising zone, evaluate:
- Opportunity Type: Categorize (e.g., "Metro First-Mover", "Residential Sticky")
- Overall Score: 0-100 weighted composite
- Strengths: Top 3-4 factors with evidence from the analysis
- Concerns: Top 2-3 risks with specific mitigation strategies

### 3. Top Recommendation Selection
Choose the single best location based on:
- Highest weighted opportunity score
- Best balance of opportunity vs risk
- Most aligned with business type requirements

### 4. Alternative Locations
Identify 2-3 alternative locations with brief analysis.

### 5. Strategic Insights
Provide 4-6 key insights spanning the entire analysis.

## Output Requirements
Your response MUST conform to the LocationIntelligenceReport schema.
Use evidence from the analysis to support all recommendations.
"""
```

---

## Building the StrategyAdvisorAgent

```python
# app/sub_agents/strategy_advisor/agent.py
from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from google.genai.types import ThinkingConfig

from ...config import PRO_MODEL, RETRY_INITIAL_DELAY, RETRY_ATTEMPTS
from ...schemas import LocationIntelligenceReport
from ...callbacks import before_strategy_advisor, after_strategy_advisor

strategy_advisor_agent = LlmAgent(
    name="StrategyAdvisorAgent",
    model=PRO_MODEL,
    description="Synthesizes findings into strategic recommendations using extended reasoning",
    instruction=STRATEGY_ADVISOR_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    planner=BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=False,  # Required when using output_schema
            thinking_budget=-1,  # Unlimited
        )
    ),
    output_schema=LocationIntelligenceReport,
    output_key="strategic_report",
    before_agent_callback=before_strategy_advisor,
    after_agent_callback=after_strategy_advisor,
)
```

**Key Configuration:**

| Parameter | Purpose |
|-----------|---------|
| `model=PRO_MODEL` | Use the most capable model for synthesis |
| `planner` with `ThinkingConfig` | Enable extended reasoning |
| `output_schema=LocationIntelligenceReport` | Force structured JSON output |
| `output_key="strategic_report"` | Save for artifact generation |

---

## Saving the JSON Artifact

The after callback saves the report as an artifact:

```python
# app/callbacks/pipeline_callbacks.py
def after_strategy_advisor(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log completion and save JSON artifact."""
    report = callback_context.state.get("strategic_report", {})
    logger.info("STAGE 3: COMPLETE - Strategic report generated")

    # Save JSON artifact
    if report:
        try:
            # Handle both dict and Pydantic model
            if hasattr(report, "model_dump"):
                report_dict = report.model_dump()
            else:
                report_dict = report

            json_str = json.dumps(report_dict, indent=2, default=str)
            json_artifact = types.Part.from_bytes(
                data=json_str.encode('utf-8'),
                mime_type="application/json"
            )
            callback_context.save_artifact("intelligence_report.json", json_artifact)
            logger.info("  Saved artifact: intelligence_report.json")
        except Exception as e:
            logger.warning(f"  Failed to save JSON artifact: {e}")

    stages = callback_context.state.get("stages_completed", [])
    stages.append("strategy_synthesis")
    callback_context.state["stages_completed"] = stages

    return None
```

**Artifact Handling:**
- `types.Part.from_bytes()` creates the artifact
- `mime_type="application/json"` identifies the file type
- `callback_context.save_artifact()` persists it
- Artifacts appear in the ADK Web UI "Artifacts" tab

---

## The Core Pipeline Complete!

With StrategyAdvisorAgent, you have a complete analysis pipeline:

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
│  GapAnalysisAgent → gap_analysis
│              │
│              ▼
│  ┌───────────────────────────┐          │
│  │  StrategyAdvisorAgent     │ ◄── YOU ARE HERE
│  │  planner: BuiltInPlanner  │          │
│  │    (ThinkingConfig)       │          │
│  │  output_schema:           │          │
│  │    LocationIntelligence   │          │
│  │    Report                 │          │
│  └───────────────────────────┘          │
│              │                          │
│              ▼                          │
│  [Next: ArtifactGenerationPipeline]     │
└─────────────────────────────────────────┘
```

---

## Try It!

Run the agent:

```bash
make dev
```

After running a query, check:
1. **State panel**: Look for `strategic_report` - it's the full structured report
2. **Artifacts tab**: Find `intelligence_report.json`

### Example Output

```json
{
  "target_location": "Indiranagar, Bangalore",
  "business_type": "coffee shop",
  "analysis_date": "2025-01-15",
  "market_validation": "Strong market with high purchasing power and established coffee culture. Competition is significant but quality gaps exist.",
  "total_competitors_found": 15,
  "zones_analyzed": 4,
  "top_recommendation": {
    "location_name": "Defence Colony",
    "area": "Indiranagar",
    "overall_score": 78,
    "opportunity_type": "Residential Premium",
    "strengths": [
      {
        "factor": "Lower Competition",
        "description": "Only 2 competitors in the zone",
        "evidence_from_analysis": "Gap analysis showed 0.85 saturation index vs 2.70 for 100 Feet Road"
      },
      {
        "factor": "High Income Residents",
        "description": "Premium residential area with high purchasing power",
        "evidence_from_analysis": "Market research indicated upper-middle to high income demographic"
      }
    ],
    "concerns": [
      {
        "risk": "Lower Foot Traffic",
        "description": "Residential area has less walk-in traffic",
        "mitigation_strategy": "Focus on third-place positioning for remote workers; implement loyalty programs"
      }
    ],
    "competition": {
      "total_competitors": 2,
      "density_per_km2": 0.8,
      "chain_dominance_pct": 0.0,
      "avg_competitor_rating": 4.25,
      "high_performers_count": 0
    },
    "market": {
      "population_density": "Medium",
      "income_level": "High",
      "infrastructure_access": "Good metro connectivity",
      "foot_traffic_pattern": "Moderate weekday, low weekend",
      "rental_cost_tier": "Medium-High"
    },
    "best_customer_segment": "Remote workers, young professionals, residents",
    "estimated_foot_traffic": "Moderate",
    "next_steps": [
      "Scout specific properties in Defence Colony",
      "Research rent rates for 500-800 sq ft spaces",
      "Visit during weekday mornings to observe traffic",
      "Analyze parking availability for drive-in customers"
    ]
  },
  "alternative_locations": [...],
  "key_insights": [
    "100 Feet Road is oversaturated with chain dominance - avoid for differentiated positioning",
    "Metro proximity correlates with foot traffic but not always with viability",
    "Quality gap exists for specialty roasters in residential areas"
  ],
  "methodology_summary": "Analysis combined Google Search market research, Google Maps Places API competitor mapping, and pandas-based quantitative gap analysis with weighted scoring."
}
```

---

## What You've Learned

In this part, you:

1. Used `ThinkingConfig` for extended reasoning
2. Designed complex nested Pydantic schemas
3. Combined thinking mode with structured output
4. Saved artifacts in callbacks with `save_artifact()`
5. Completed the core analysis pipeline

---

## Next Up

The strategic report is comprehensive—but it's JSON. Business stakeholders don't read JSON. They need polished deliverables: presentation slides they can share with investors, visual infographics for quick consumption, and maybe even an audio summary they can listen to during their commute.

In [Part 7: Artifact Generation](./07-artifact-generation.md), we'll transform this strategic report into three professional outputs simultaneously using a **ParallelAgent**. This is where your agent becomes a complete solution—from "coffee shop in Bangalore" to a McKinsey-style presentation, a visual infographic, and a podcast-style audio briefing.

You'll learn:
- **ParallelAgent** for ~40% faster concurrent execution
- Native image generation with Gemini
- Multi-speaker TTS audio generation
- The complete, production-ready agent!

---

## Quick Reference

| Feature | How to Use |
|---------|------------|
| Extended reasoning | `planner=BuiltInPlanner(thinking_config=ThinkingConfig(...))` |
| Unlimited thinking | `thinking_budget=-1` |
| With output_schema | Must set `include_thoughts=False` |
| Save artifact | `callback_context.save_artifact(name, part)` |
| Create artifact | `types.Part.from_bytes(data=..., mime_type=...)` |

---

**Code files referenced in this part:**
- [`app/sub_agents/strategy_advisor/agent.py`](../app/sub_agents/strategy_advisor/agent.py) - Agent
- [`app/schemas/report_schema.py`](../app/schemas/report_schema.py) - Pydantic schemas
- [`app/callbacks/pipeline_callbacks.py`](../app/callbacks/pipeline_callbacks.py) - Artifact saving

**ADK Documentation:**
- [Extended Reasoning](https://google.github.io/adk-docs/agents/llm-agents/#thinking-and-planning)
- [Artifacts](https://google.github.io/adk-docs/agents/artifacts/)

---

<details>
<summary>Image Prompts for This Part</summary>

### Image 1: Pipeline Flow Diagram

```json
{
  "image_type": "synthesis_diagram",
  "style": {
    "design": "consulting/strategy presentation style",
    "color_scheme": "Google Cloud colors (blue #4285F4, red #EA4335, yellow #FBBC05, green #34A853) with white background",
    "layout": "convergent flow",
    "aesthetic": "professional, clean"
  },
  "dimensions": {"aspect_ratio": "16:9", "recommended_width": 1100},
  "title": {"text": "Part 6: StrategyAdvisorAgent - Strategic Synthesis", "position": "top center"},
  "sections": [
    {
      "id": "inputs",
      "position": "left",
      "layout": "vertical stack",
      "components": [
        {"name": "market_research_findings", "color": "#E3F2FD"},
        {"name": "competitor_analysis", "color": "#E8F5E9"},
        {"name": "gap_analysis", "color": "#FFF3E0"}
      ]
    },
    {
      "id": "thinking",
      "position": "center",
      "color": "#34A853",
      "components": [
        {"name": "StrategyAdvisorAgent", "icon": "brain with gears"},
        {"name": "Extended Reasoning", "icon": "thought bubbles"},
        {"name": "ThinkingConfig", "description": "thinking_budget: -1"}
      ]
    },
    {
      "id": "output",
      "position": "right",
      "color": "#FBBC05",
      "components": [
        {"name": "LocationIntelligenceReport", "icon": "structured document", "sections": ["Top Recommendation: 78/100", "Strengths", "Concerns", "Alternatives", "Next Steps"]}
      ]
    },
    {
      "id": "artifact",
      "position": "bottom-right",
      "color": "#4285F4",
      "components": [
        {"name": "intelligence_report.json", "icon": "JSON file"}
      ]
    }
  ],
  "connections": [
    {"from": "inputs", "to": "thinking", "label": "All findings"},
    {"from": "thinking", "to": "output", "label": "Synthesize"},
    {"from": "output", "to": "artifact", "label": "Save Artifact"}
  ]
}
```

### Image 2: Extended Reasoning Concept

```json
{
  "image_type": "concept_diagram",
  "style": {
    "design": "cognitive process illustration",
    "color_scheme": "Google Cloud colors (blue #4285F4, green #34A853, yellow #FBBC05)",
    "layout": "sequential comparison showing with/without thinking",
    "aesthetic": "clean, educational, conceptual"
  },
  "dimensions": {"aspect_ratio": "16:9", "recommended_width": 1000},
  "title": {"text": "ThinkingConfig: Think Before Responding", "position": "top center"},
  "concept": "Show that thinking mode allows the model to reason internally before producing output",
  "sections": [
    {
      "id": "without_thinking",
      "position": "left half",
      "label": "Without ThinkingConfig",
      "color": "#FFF3E0",
      "components": [
        {"name": "Input", "description": "Complex synthesis task"},
        {"name": "LLM", "icon": "brain", "description": "Immediate response"},
        {"name": "Output", "icon": "document", "description": "May miss nuances"}
      ],
      "flow": "straight arrow",
      "annotation": "Fast but potentially shallow"
    },
    {
      "id": "with_thinking",
      "position": "right half",
      "label": "With ThinkingConfig",
      "color": "#E8F5E9",
      "components": [
        {"name": "Input", "description": "Complex synthesis task"},
        {"name": "Internal Reasoning", "icon": "thought cloud", "description": "Model weighs trade-offs, considers alternatives", "emphasized": true},
        {"name": "LLM", "icon": "brain + gears", "description": "Informed response"},
        {"name": "Output", "icon": "structured document", "description": "Comprehensive, nuanced"}
      ],
      "flow": "arrow with thinking bubble",
      "annotation": "thinking_budget: -1 (unlimited)"
    }
  ],
  "key_points": [
    {"text": "Thinking happens INSIDE the model", "position": "bottom left"},
    {"text": "include_thoughts=False hides internal reasoning", "position": "bottom center"},
    {"text": "Critical for complex multi-factor decisions", "position": "bottom right"}
  ]
}
```

</details>
