# Experiment 004: Comprehensive Equity Research Report Agent

## Status: WORKING

A sophisticated multi-chart equity research report generator that produces professional investment reports with multiple visualizations, AI-generated infographics, data tables, and comprehensive company coverage.

**Key Innovation**: Given a query like "Do a fundamental analysis of Alphabet", the agent will:
1. **Plan** - Identify company and plan which metrics/charts are needed
2. **Fetch** - Gather data from 4 parallel sources (financial, valuation, market, news)
3. **Consolidate** - Merge all data into structured format
4. **Visualize** - Generate multiple charts (5-10) using a LoopAgent
5. **Infographics** - Generate 3 AI-powered infographics using Gemini 3 Pro Image
6. **Analyze** - Write professional narrative analysis sections
7. **Report** - Create a multi-page HTML report with charts, infographics, and data tables

---

## What's New in 004 vs 002

| Aspect | code_execution_02 | code_execution_04 |
|--------|-------------------|-------------------|
| Charts | 1 chart per query | **Multiple charts (5-10)** |
| Data Gathering | Sequential (1 agent) | **Parallel (4 concurrent agents)** |
| Chart Generation | Single execution | **LoopAgent iterates through metrics** |
| **Infographics** | None | **3 AI-generated infographics (parallel)** |
| **Data Tables** | None | **Raw numerical data tables** |
| Report Structure | Single-page | **Multi-section professional report** |
| Metrics Coverage | User-specified | **Auto-planned based on query** |
| Pipeline Stages | 5 agents | **8 agents (+ custom BaseAgent)** |

### New ADK Features Used

| Feature | Description | Usage in 004 |
|---------|-------------|--------------|
| **ParallelAgent** | Runs sub-agents concurrently | 4 data fetchers + 3 infographic generators |
| **LoopAgent** | Iterates with max_iterations | Generates one chart per iteration |
| **Custom BaseAgent** | User-defined agent logic | `ChartProgressChecker` for loop control |
| **EventActions.escalate** | Exit loop early | When all charts are generated |
| **FunctionTool** | Custom tool with ToolContext | `generate_infographic` for image generation |
| **Gemini 3 Pro Image** | AI image generation | Infographics using `gemini-3-pro-image-preview` |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Google Cloud Project with Vertex AI enabled
- `gcloud` CLI authenticated
- Sandbox already created (reuse from code_execution_01 or 02)

### Setup

```bash
# 1. Navigate to the experiment folder
cd adk-deep-research/code_execution_04

# 2. Install dependencies
pip install -r requirements.txt

# 3. Ensure .env file exists in adk-deep-research/ folder
# (reuse the same sandbox from previous experiments)

# 4. Run the agent
cd ..  # Go back to adk-deep-research folder
adk web code_execution_04
```

### Environment Variables

Same as previous experiments:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=1

# Pre-created Sandbox for Code Execution
SANDBOX_RESOURCE_NAME=projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID/sandboxEnvironments/YOUR_SANDBOX_ID
```

---

## Architecture

```
User Query: "Do a fundamental analysis of Alphabet"
                          |
+----------------------------------------------------------+
|      equity_research_pipeline (SequentialAgent)          |
+----------------------------------------------------------+
|                                                          |
|  1. RESEARCH PLANNER AGENT                               |
|     - Analyzes query, identifies company                 |
|     - Plans which metrics/charts are needed (5-8)        |
|     - output_schema: ResearchPlan                        |
|     - output_key: "research_plan"                        |
|                                                          |
|  2. PARALLEL DATA GATHERERS (ParallelAgent)              |
|     - Run 4 data fetchers concurrently:                  |
|     +-----------------------------------------------+    |
|     | financial_data_fetcher → "financial_data"     |    |
|     | valuation_data_fetcher → "valuation_data"     |    |
|     | market_data_fetcher → "market_data"           |    |
|     | news_sentiment_fetcher → "news_data"          |    |
|     +-----------------------------------------------+    |
|                                                          |
|  3. DATA CONSOLIDATOR AGENT                              |
|     - Merges all 4 fetcher outputs                       |
|     - Extracts structured metrics for charting           |
|     - output_schema: ConsolidatedResearchData            |
|     - output_key: "consolidated_data"                    |
|                                                          |
|  4. CHART GENERATION LOOP (LoopAgent)                    |
|     - max_iterations: 10                                 |
|     +-----------------------------------------------+    |
|     | chart_code_generator (LlmAgent)               |    |
|     |   - Generates matplotlib code for ONE chart   |    |
|     |   - after_callback: execute_and_save_chart    |    |
|     +-----------------------------------------------+    |
|     | chart_progress_checker (Custom BaseAgent)     |    |
|     |   - Checks if all metrics charted             |    |
|     |   - Escalates when done → exits loop          |    |
|     +-----------------------------------------------+    |
|                                                          |
|  5. INFOGRAPHIC PLANNER AGENT (NEW)                      |
|     - Plans 3 AI-generated infographics                  |
|     - Generates detailed prompts for each                |
|     - output_schema: InfographicPlan                     |
|     - output_key: "infographic_plan"                     |
|                                                          |
|  6. PARALLEL INFOGRAPHIC GENERATORS (ParallelAgent, NEW) |
|     - Run 3 generators concurrently:                     |
|     +-----------------------------------------------+    |
|     | infographic_generator_1 → Business Model      |    |
|     | infographic_generator_2 → Competitive Landscape|   |
|     | infographic_generator_3 → Growth Drivers      |    |
|     +-----------------------------------------------+    |
|     - Uses generate_infographic tool with Gemini 3 Pro  |
|     - Saves to "infographics_generated" state           |
|                                                          |
|  7. ANALYSIS WRITER AGENT                                |
|     - Writes 7 narrative analysis sections               |
|     - output_schema: AnalysisSections                    |
|     - output_key: "analysis_sections"                    |
|                                                          |
|  8. HTML REPORT GENERATOR AGENT                          |
|     - Creates multi-section professional report          |
|     - Embeds charts (CHART_1_PLACEHOLDER, etc.)          |
|     - Embeds infographics (INFOGRAPHIC_1_PLACEHOLDER)    |
|     - Includes data tables with raw numbers              |
|     - after_callback: inject_all_images_and_save         |
|                                                          |
+----------------------------------------------------------+
                          |
        Final Output: equity_report.html (multi-page)
                      + chart_1.png, chart_2.png, ... (artifacts)
                      + infographic_1.png, infographic_2.png, infographic_3.png
```

---

## Pydantic Schemas

### Input Planning

```python
class MetricSpec(BaseModel):
    """Specification for a single metric to analyze."""
    metric_name: str        # e.g., "Revenue", "P/E Ratio"
    chart_type: Literal["line", "bar", "area"]
    data_source: Literal["financial", "valuation", "market", "news"]
    section: Literal["financials", "valuation", "growth", "market"]
    priority: int           # 1-10
    search_query: str       # Specific search query

class ResearchPlan(BaseModel):
    """Complete research plan."""
    company_name: str
    ticker: str
    exchange: str
    metrics_to_analyze: list[MetricSpec]
    report_sections: list[str]
```

### Infographic Planning (NEW)

```python
class InfographicSpec(BaseModel):
    """Specification for an infographic."""
    infographic_id: int     # 1, 2, or 3
    title: str              # e.g., "Business Model Overview"
    infographic_type: Literal["business_model", "competitive_landscape", "growth_drivers"]
    key_elements: list[str] # Data points to visualize
    visual_style: str       # Style description
    prompt: str             # Detailed image generation prompt

class InfographicPlan(BaseModel):
    """Plan for all infographics."""
    company_name: str
    infographics: list[InfographicSpec]  # Always 3 infographics

class InfographicResult(BaseModel):
    """Result of infographic generation."""
    infographic_id: int
    title: str
    filename: str           # "infographic_1.png"
    base64_data: str
    infographic_type: str
```

### Data Consolidation

```python
class DataPoint(BaseModel):
    period: str             # "2023", "Q1 2024"
    value: float
    unit: str

class MetricData(BaseModel):
    """Extracted data for one metric."""
    metric_name: str
    data_points: list[DataPoint]
    chart_type: str
    chart_title: str
    y_axis_label: str
    section: str
    notes: str | None

class ConsolidatedResearchData(BaseModel):
    company_name: str
    ticker: str
    metrics: list[MetricData]
    company_overview: str
    news_summary: str
    analyst_ratings: str
    key_risks: list[str]
```

---

## State Flow

```
research_plan (ResearchPlan)
    ↓
ParallelAgent (concurrent):
    → financial_data
    → valuation_data
    → market_data
    → news_data
    ↓
consolidated_data (ConsolidatedResearchData)
    ↓
LoopAgent (iterates N times):
    → current_chart_code
    → charts_generated: [ChartResult, ChartResult, ...]
    ↓
infographic_plan (InfographicPlan)
    ↓
ParallelAgent (concurrent, NEW):
    → infographic_1_result
    → infographic_2_result
    → infographic_3_result
    → infographics_generated: [InfographicResult, ...]
    ↓
analysis_sections (AnalysisSections)
    ↓
html_report (str)
    ↓
Artifacts:
    - equity_report.html
    - chart_1.png, chart_2.png, ...
    - infographic_1.png, infographic_2.png, infographic_3.png
```

---

## Image Generation Tool

The `generate_infographic` tool uses Gemini 3 Pro Image model via Vertex AI:

```python
async def generate_infographic(
    prompt: str,
    infographic_id: int,
    title: str,
    tool_context: ToolContext
) -> dict:
    """Generate an infographic using Gemini 3 Pro Image model."""

    client = genai.Client(vertexai=True, project=project_id, location=location)

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            image_config=genai_types.ImageConfig(aspect_ratio="16:9"),
        ),
    )

    # Extract and save image...
```

---

## HTML Report Structure

```
EQUITY RESEARCH REPORT
======================

HEADER
├── Company Name + Ticker + Exchange
├── Report Date
├── Sector
└── Rating Badge (Buy/Hold/Sell)

EXECUTIVE SUMMARY
└── Investment thesis, key highlights, recommendation

KEY METRICS
└── Grid of metric cards (Revenue, EPS, P/E, etc.)

COMPANY OVERVIEW
└── Business description, competitive position

VISUAL INSIGHTS (NEW)
└── 3 AI-generated infographics:
    ├── Business Model
    ├── Competitive Landscape
    └── Growth Drivers

FINANCIAL PERFORMANCE
├── Narrative analysis
└── Charts: Revenue, Net Income, Operating Margin

VALUATION ANALYSIS
├── Narrative analysis
└── Charts: P/E Ratio, P/B Ratio, EV/EBITDA

GROWTH OUTLOOK
├── Narrative analysis
└── Charts: Revenue Growth, Stock Price

RISKS & CONCERNS
└── Risk factors list

INVESTMENT RECOMMENDATION
└── Buy/Hold/Sell with rationale

FINANCIAL DATA TABLES (NEW)
└── Raw numerical data for all metrics

FOOTER
└── Disclaimer
```

---

## Test Queries

**Simple:**
- "Analyze Apple stock"
- "Do a fundamental analysis of Microsoft"

**Medium:**
- "Do a comprehensive equity research on Alphabet"
- "Analyze NVIDIA's valuation and growth prospects"

**Complex:**
- "Compare Tesla vs Ford - comprehensive equity research"
- "Full fundamental analysis of Amazon including cloud segment"

---

## Files

| File | Description |
|------|-------------|
| `agent.py` | 8-stage pipeline with ParallelAgent + LoopAgent + Infographics |
| `config.py` | Configuration (same as 02) |
| `manage_sandbox.py` | Sandbox CLI tool (same as 02) |
| `requirements.txt` | Python dependencies |
| `__init__.py` | Package init |
| `README.md` | This documentation |

---

## Key Design Decisions

### 1. Callback-Based Code Execution

Learned from experiment 03's infinite loop issues, we use callbacks to execute chart code:

| Approach | Reliability | Why |
|----------|-------------|-----|
| **Callback (04)** | 100% | LLM generates code, callback executes ONCE |
| Native code_executor (03) | ~70% | LLM sees results, tries to "improve" |

### 2. ParallelAgent for Data Fetching + Infographics

Running agents concurrently reduces total time significantly:

```python
# Data fetching (4 parallel)
parallel_data_gatherers = ParallelAgent(
    name="parallel_data_gatherers",
    sub_agents=[
        financial_data_fetcher,
        valuation_data_fetcher,
        market_data_fetcher,
        news_sentiment_fetcher,
    ],
)

# Infographic generation (3 parallel)
parallel_infographic_generators = ParallelAgent(
    name="parallel_infographic_generators",
    sub_agents=[
        infographic_generator_1,  # Business Model
        infographic_generator_2,  # Competitive Landscape
        infographic_generator_3,  # Growth Drivers
    ],
)
```

### 3. Tool-Based Image Generation

Instead of code execution, infographics use a FunctionTool that wraps Gemini 3 Pro Image:

```python
generate_infographic_tool = FunctionTool(generate_infographic)

# Used by infographic generators
infographic_generator_1 = LlmAgent(
    tools=[generate_infographic_tool],
    ...
)
```

### 4. Placeholder-Based Image Injection

HTML uses placeholders that callbacks replace with base64:

```html
<!-- Charts -->
<img src="CHART_1_PLACEHOLDER" alt="Revenue Chart">
<img src="CHART_2_PLACEHOLDER" alt="EPS Chart">

<!-- Infographics -->
<img src="INFOGRAPHIC_1_PLACEHOLDER" alt="Business Model">
<img src="INFOGRAPHIC_2_PLACEHOLDER" alt="Competitive Landscape">
<img src="INFOGRAPHIC_3_PLACEHOLDER" alt="Growth Drivers">
```

---

## Model Configuration

| Setting | Value |
|---------|-------|
| Text Model | `gemini-3-flash-preview` |
| Image Model | `gemini-3-pro-image-preview` |
| Total Agents | 17 (8 in pipeline + 4 data + 3 infographic + 2 in loop) |
| Context | Shared via output_key |

---

## Sources

- [ADK Documentation - ParallelAgent](https://google.github.io/adk-docs/agents/workflow-agents/parallel-agent)
- [ADK Documentation - LoopAgent](https://google.github.io/adk-docs/agents/workflow-agents/loop-agent)
- [Gemini Image Generation](https://ai.google.dev/gemini-api/docs/image-generation)
- [code_execution_02](../code_execution_02/) - Base experiment this extends
- [code_execution_03](../code_execution_03/) - Lessons learned about infinite loops

---

**Last Updated**: 2025-12-28
**Experiment Status**: WORKING
**Base Experiment**: code_execution_02 (SUCCESS - RECOMMENDED)
**Key ADK Features**: ParallelAgent, LoopAgent, Custom BaseAgent, FunctionTool
**Expected Charts**: 5-10 per report
**Expected Infographics**: 3 per report (Business Model, Competitive Landscape, Growth Drivers)
