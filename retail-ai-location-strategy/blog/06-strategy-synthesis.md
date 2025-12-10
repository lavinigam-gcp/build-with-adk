# Part 6: Strategic Synthesis with Extended Reasoning

In the previous parts, you built agents that gather data—market research from web searches, competitor locations from Google Maps, and quantitative analysis from code execution. Now comes the hardest part: synthesizing all of this into a coherent strategic recommendation.

This isn't simple summarization. The agent needs to weigh competing factors, handle trade-offs, and reason through complex multi-factor decisions. A zone might have excellent foot traffic but high competition. Another might be underserved but in a declining area. How do you balance viability scores against rental costs against competitive density?

For synthesis tasks like this, standard LLM generation often falls short. The model needs to think deeply before responding. That's where Gemini's **extended reasoning** comes in.

<p align="center">
  <img src="assets/part6_output_image.jpeg" alt="Part 6: StrategyAdvisorAgent - Strategic Synthesis Output" width="600">
</p>

---

## The Synthesis Challenge

At this point in the pipeline, we have rich data from three sources:

- **Market research** with demographics, growth trends, and commercial viability indicators
- **Competitor data** with real ratings, review counts, and geographic clustering
- **Quantitative analysis** with saturation indices, viability scores, and zone rankings

The challenge is to transform this data into actionable strategic recommendations. We need to identify the single best location, explain why it's the best, acknowledge its risks with mitigation strategies, and provide concrete next steps. We also need to surface alternative locations and key insights that span the entire analysis.

This requires deep reasoning—not just pattern matching or summarization. The model needs to consider: "If Defence Colony has the highest viability score but lower foot traffic, is it still the best choice for a coffee shop that depends on walk-in customers? Or should we recommend 12th Main despite its moderate saturation, because the foot traffic compensates?"

---

## Extended Reasoning with ThinkingConfig

ADK supports Gemini's "thinking mode," which allocates additional compute budget for complex reasoning tasks. Instead of immediately generating a response, the model first thinks through the problem internally, then produces a more considered output.

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

The `ThinkingConfig` parameters control this behavior:

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `include_thoughts` | `False` | Don't include internal reasoning in output |
| `thinking_budget` | `-1` | Allow unlimited thinking tokens |
| `thinking_budget` | `1000` | Limit to 1000 thinking tokens |

For our synthesis task, we set `thinking_budget=-1` because strategic recommendations benefit from thorough consideration. The model might need to compare multiple zones, weigh competing factors, reason about uncertainties, and consider how different factors interact before arriving at a recommendation.

One important constraint: when using `output_schema` (which forces structured JSON output), you must set `include_thoughts=False`. The internal thinking cannot be included in structured output.

> **Learn more:** The [Extended Reasoning documentation](https://google.github.io/adk-docs/agents/llm-agents/#thinking-and-planning) covers thinking mode configuration.

---

## The LocationIntelligenceReport Schema

The output of our synthesis agent is a comprehensive `LocationIntelligenceReport`—a nested Pydantic schema that captures everything a business stakeholder needs to make a location decision.

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

This schema design has several benefits. The nested structure (`StrengthAnalysis`, `ConcernAnalysis`, etc.) ensures each recommendation includes complete information. Field descriptions guide the model on what to include. Validation constraints like `ge=0, le=100` for scores ensure output validity. And the structure itself communicates what a complete strategic recommendation looks like.

> **Learn more:** The [Structured Output documentation](https://google.github.io/adk-docs/agents/llm-agents/#structured-output) covers Pydantic integration.

---

## The Synthesis Instruction

The instruction prompt guides the model through a systematic synthesis process:

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

The instruction provides all upstream data via state injection—`{market_research_findings}`, `{competitor_analysis}`, and `{gap_analysis}` pull in the complete outputs from earlier pipeline stages. It also provides a clear framework for synthesis, ensuring the model doesn't just summarize but actually reasons through trade-offs.

---

## Building the StrategyAdvisorAgent

With the instruction and schema defined, the agent combines extended reasoning with structured output:

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

The key configuration choices:

| Parameter | Purpose |
|-----------|---------|
| `model=PRO_MODEL` | Use the most capable model for complex synthesis |
| `planner` with `ThinkingConfig` | Enable extended reasoning before responding |
| `output_schema=LocationIntelligenceReport` | Force structured JSON output matching schema |
| `output_key="strategic_report"` | Save the report for artifact generation downstream |

We use `PRO_MODEL` (typically Gemini Pro or higher) because synthesis tasks benefit from the most capable reasoning. The combination of thinking mode and structured output ensures we get both thoughtful analysis and reliably formatted results.

---

## Saving the Report as an Artifact

The strategic report is valuable beyond the current session. Stakeholders might want to download it, share it with colleagues, or process it in other systems. The after callback saves the report as a JSON artifact:

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

A few implementation details are worth noting. We check for `model_dump()` to handle both Pydantic models and plain dictionaries (ADK may return either). The `types.Part.from_bytes()` function creates the artifact with appropriate MIME type. And `callback_context.save_artifact()` persists it so it appears in the ADK Web UI's Artifacts tab.

> **Learn more:** The [Artifacts documentation](https://google.github.io/adk-docs/agents/artifacts/) covers saving and retrieving artifacts.

---

## Testing the StrategyAdvisorAgent

Start the development server and run a complete analysis:

```bash
make dev
```

Open `http://localhost:8501` and enter a query like:

> "I want to open a coffee shop in Indiranagar, Bangalore"

After the pipeline completes market research, competitor mapping, and gap analysis, you'll see the StrategyAdvisorAgent synthesize everything into a comprehensive report.

Check two places for the output:

1. **State panel**: Look for `strategic_report`—it contains the full structured report as a Pydantic model or dictionary
2. **Artifacts tab**: Find `intelligence_report.json`—the downloadable JSON file

### Example Output

Here's what a strategic report looks like:

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

Notice how the report connects evidence to recommendations. The "Lower Competition" strength cites the specific saturation index from gap analysis. The concern about foot traffic includes a concrete mitigation strategy. This is the kind of nuanced output that extended reasoning enables.

---

## What You've Learned

In this part, you've built the synthesis layer of the pipeline:

- **ThinkingConfig** enables extended reasoning for complex multi-factor decisions
- **Complex Pydantic schemas** with nested models capture complete strategic recommendations
- **`include_thoughts=False`** is required when combining thinking mode with `output_schema`
- **Artifact saving** in callbacks makes reports available for download and sharing
- **State injection** brings all upstream analysis into the synthesis context

With StrategyAdvisorAgent, the core analysis pipeline is complete. We go from a natural language request ("coffee shop in Bangalore") to a consultant-grade strategic recommendation with evidence-backed insights.

---

## Quick Reference

| Feature | How to Use |
|---------|------------|
| Extended reasoning | `planner=BuiltInPlanner(thinking_config=ThinkingConfig(...))` |
| Unlimited thinking | `thinking_budget=-1` |
| With output_schema | Must set `include_thoughts=False` |
| Save artifact | `callback_context.save_artifact(name, part)` |
| Create artifact | `types.Part.from_bytes(data=..., mime_type=...)` |

**Files referenced in this part:**

- [`app/sub_agents/strategy_advisor/agent.py`](../app/sub_agents/strategy_advisor/agent.py) — StrategyAdvisorAgent definition
- [`app/schemas/report_schema.py`](../app/schemas/report_schema.py) — Pydantic schema definitions
- [`app/callbacks/pipeline_callbacks.py`](../app/callbacks/pipeline_callbacks.py) — Artifact saving callback

**ADK Documentation:**

- [Extended Reasoning](https://google.github.io/adk-docs/agents/llm-agents/#thinking-and-planning) — ThinkingConfig and thinking mode
- [Structured Output](https://google.github.io/adk-docs/agents/llm-agents/#structured-output) — Using Pydantic with LlmAgent
- [Artifacts](https://google.github.io/adk-docs/agents/artifacts/) — Saving and retrieving artifacts
- [Session State](https://google.github.io/adk-docs/sessions/state/) — State injection between agents

---

## Next: Multimodal Artifact Generation

The strategic report is comprehensive—but it's JSON. Business stakeholders don't read JSON. They need polished deliverables: an HTML presentation they can share with investors, a visual infographic for quick consumption, and maybe even an audio summary they can listen to during their commute.

In **[Part 7: Artifact Generation](./07-artifact-generation.md)**, you'll transform this strategic report into three professional outputs simultaneously using a **ParallelAgent**. Instead of generating artifacts one by one, the ParallelAgent runs all three generation agents concurrently—making the pipeline roughly 40% faster.

You'll learn:
- Using **ParallelAgent** for concurrent execution
- Native **image generation** with Gemini's imagen capabilities
- **Multi-speaker TTS** for podcast-style audio briefings
- Saving multiple artifact types (HTML, PNG, WAV)

This is where your agent becomes a complete solution—from "coffee shop in Bangalore" to a presentation deck, visual infographic, and audio briefing, all generated automatically.

---

**[← Back to Part 5: Code Execution](./05-code-execution.md)** | **[Continue to Part 7: Artifact Generation →](./07-artifact-generation.md)**
