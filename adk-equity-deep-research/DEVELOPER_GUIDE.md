# Developer Guide: Equity Research Report Agent

This guide provides a deep technical dive into the agent architecture, state management, callbacks, and Pydantic schemas. For getting started and basic usage, see [README.md](README.md).

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [ADK Patterns Used](#adk-patterns-used)
- [State Management](#state-management)
- [Pydantic Schemas](#pydantic-schemas)
- [Callback Reference](#callback-reference)
- [Configuration](#configuration)
- [Boundary Validation](#boundary-validation)
- [Key Design Decisions](#key-design-decisions)

---

## Architecture Overview

```text
User Query: "Do a fundamental analysis of Alphabet"
                          |
+===========================================================+
|      root_agent (SequentialAgent)                          |
|      before_agent_callback: ensure_classifier_state        |
+===========================================================+
|                                                             |
|  0. QUERY VALIDATOR (LlmAgent)                              |
|     - Checks boundary rules (crypto, trading advice, etc.)  |
|     - after_agent_callback: check_validation_callback       |
|     - output_key: "query_validation"                        |
|     - If invalid → stops with rejection message             |
|                                                             |
|  1. QUERY CLASSIFIER (LlmAgent)                             |
|     - Classifies as NEW_QUERY or FOLLOW_UP                  |
|     - Detects market (US, India, China, Japan, Korea, EU)   |
|     - after_agent_callback: check_classification_callback   |
|     - output_key: "query_classification"                    |
|     - If FOLLOW_UP → stops with guidance message            |
|                                                             |
|  2. HITL PLANNING AGENT (SequentialAgent)                   |
|     - before_agent_callback: check_plan_state_callback      |
|     +---------------------------------------------------+   |
|     | metric_planner (LlmAgent)                         |   |
|     |   - Generates EnhancedResearchPlan (10-15 metrics)|   |
|     |   - before_callback: skip_if_plan_exists          |   |
|     |   - after_callback: present_plan_callback         |   |
|     |   - output_key: "enhanced_research_plan"          |   |
|     +---------------------------------------------------+   |
|     | plan_response_classifier (LlmAgent)               |   |
|     |   - before_callback: skip_if_not_pending          |   |
|     |   - Classifies: APPROVAL, REFINEMENT, NEW_QUERY   |   |
|     |   - after_callback: process_plan_response         |   |
|     |   - output_key: "plan_response"                   |   |
|     +---------------------------------------------------+   |
|     | plan_refiner (LlmAgent)                           |   |
|     |   - before_callback: skip_if_not_refinement       |   |
|     |   - Updates plan based on user feedback           |   |
|     |   - after_callback: re_present_plan               |   |
|     |   - output_key: "enhanced_research_plan"          |   |
|     +---------------------------------------------------+   |
|                                                             |
+===========================================================+
                          | (only if plan_state == "approved")
+-----------------------------------------------------------+
|      equity_research_pipeline (SequentialAgent)            |
|      before_agent_callback: skip_if_not_approved_callback  |
+-----------------------------------------------------------+
|                                                            |
|  3. RESEARCH PLANNER (LlmAgent) - Phase 1 fallback         |
|     - output_key: "research_plan"                          |
|                                                            |
|  4. PARALLEL DATA GATHERERS (ParallelAgent)                |
|     +------------------------------------------------+     |
|     | financial_data_fetcher (LlmAgent)              |     |
|     |   - output_key: "financial_data"               |     |
|     | valuation_data_fetcher (LlmAgent)              |     |
|     |   - output_key: "valuation_data"               |     |
|     | market_data_fetcher (LlmAgent)                 |     |
|     |   - output_key: "market_data"                  |     |
|     | news_sentiment_fetcher (LlmAgent)              |     |
|     |   - output_key: "news_data"                    |     |
|     +------------------------------------------------+     |
|                                                            |
|  5. DATA CONSOLIDATOR (LlmAgent)                           |
|     - output_key: "consolidated_data"                      |
|     - output_schema: ConsolidatedResearchData              |
|                                                            |
|  6. CHART GENERATION (conditional on ENABLE_BATCH_CHARTS)  |
|                                                            |
|     [BATCH MODE - ENABLE_BATCH_CHARTS=true]                |
|     +------------------------------------------------+     |
|     | batch_chart_generator (LlmAgent)               |     |
|     |   - Generates code for ALL charts at once      |     |
|     |   - after_callback: execute_batch_charts_cb    |     |
|     |   - Single sandbox execution (~5-10x faster)   |     |
|     +------------------------------------------------+     |
|                                                            |
|     [SEQUENTIAL MODE - ENABLE_BATCH_CHARTS=false]          |
|     +------------------------------------------------+     |
|     | chart_generation_loop (LoopAgent)              |     |
|     |   - max_iterations: 15 (configurable)          |     |
|     |   +------------------------------------------+ |     |
|     |   | chart_code_generator (LlmAgent)          | |     |
|     |   |   - Generates matplotlib code for 1 chart| |     |
|     |   |   - after_cb: execute_chart_code_callback| |     |
|     |   +------------------------------------------+ |     |
|     |   | chart_progress_checker (BaseAgent)       | |     |
|     |   |   - Uses EventActions.escalate to exit   | |     |
|     |   +------------------------------------------+ |     |
|     +------------------------------------------------+     |
|                                                            |
|  7. INFOGRAPHIC PLANNER (LlmAgent)                         |
|     - Plans 2-5 AI infographics dynamically                |
|     - output_key: "infographic_plan"                       |
|     - output_schema: InfographicPlan                       |
|                                                            |
|  8. INFOGRAPHIC GENERATOR (LlmAgent)                       |
|     - Calls generate_all_infographics FunctionTool         |
|     - Tool uses asyncio.gather() for parallel generation   |
|     - after_callback: create_infographics_summary_callback |
|                                                            |
|  9. ANALYSIS WRITER (LlmAgent)                             |
|     - Writes narrative with Setup→Visual→Interpretation    |
|     - output_key: "analysis_sections"                      |
|     - output_schema: AnalysisSections                      |
|                                                            |
|  10. HTML REPORT GENERATOR (LlmAgent)                      |
|      - Creates multi-section professional report           |
|      - after_callback: save_html_report_callback           |
|      - Injects charts/infographics via placeholders        |
|                                                            |
+-----------------------------------------------------------+
                          |
        Final Outputs:
        - equity_report.html (multi-page with embedded visuals)
        - equity_report.pdf (if PDF export enabled)
        - chart_1.png, chart_2.png, ... (artifacts)
        - infographic_1.png, infographic_2.png, ... (artifacts)
```

---

## ADK Patterns Used

### Agent Types

| Agent Type | Usage | Description |
|------------|-------|-------------|
| **SequentialAgent** | Root agent, HITL planning, Pipeline | Runs sub-agents in order |
| **ParallelAgent** | Data fetchers | Runs 4 fetchers concurrently |
| **LoopAgent** | Chart generation | Iterates until all charts done |
| **LlmAgent** | Most agents | LLM-powered agents with output_schema |
| **Custom BaseAgent** | ChartProgressChecker | Custom logic for loop exit |

### Callback Patterns

| Callback Type | Pattern | Usage |
|---------------|---------|-------|
| `before_agent_callback` | Return `Content` to skip, `None` to continue | Skip agents based on state |
| `after_agent_callback` | Return `Content` to replace output, `None` to keep | Routing decisions, code execution |
| Turn Gating | Set flags, check in subsequent callbacks | Prevent auto-execution after plan presentation |

---

## State Management

| State Variable | Type | Description |
|----------------|------|-------------|
| `query_validation` | dict | Validation result (is_valid, rejection_reason) |
| `query_classification` | dict | Classification (query_type, detected_market, detected_company) |
| `plan_state` | str | HITL state machine: "none" → "pending" → "approved" |
| `enhanced_research_plan` | dict | The approved research plan with metrics |
| `plan_response` | dict | User's response classification (approval/refinement/new_query) |
| `plan_presented_this_turn` | bool | Turn gating flag - prevents auto-approval |
| `skip_pipeline` | bool | Stops all subsequent agents when rejection occurs |
| `detected_market` | str | Detected market (US, India, China, Japan, Korea, Europe) |
| `financial_data` | str | Output from financial data fetcher |
| `valuation_data` | str | Output from valuation data fetcher |
| `market_data` | str | Output from market data fetcher |
| `news_data` | str | Output from news sentiment fetcher |
| `consolidated_data` | dict | Merged data with metrics list |
| `charts_generated` | list | List of ChartResult objects |
| `charts_summary` | list | Lightweight chart metadata (no base64) |
| `infographic_plan` | dict | Plan for 2-5 infographics |
| `infographics_generated` | list | Generated infographic results with base64 |
| `infographics_summary` | list | Lightweight infographic metadata |
| `analysis_sections` | dict | Written narrative sections |

---

## Pydantic Schemas

### Phase 2 HITL Schemas

```python
class MetricCategory(str, Enum):
    """Categories for professional equity metrics."""
    PROFITABILITY = "profitability"  # Margins, ROE, ROA, ROIC
    VALUATION = "valuation"          # P/E, P/B, EV/EBITDA
    LIQUIDITY = "liquidity"          # Current ratio, quick ratio
    LEVERAGE = "leverage"            # D/E, interest coverage
    EFFICIENCY = "efficiency"        # Asset turnover, inventory turnover
    GROWTH = "growth"                # Revenue growth, EPS growth
    QUALITY = "quality"              # Piotroski F-Score, Altman Z
    RISK = "risk"                    # Beta, volatility
    MARKET_SPECIFIC = "market_specific"  # Promoter %, State Ownership

class AnalysisType(str, Enum):
    """Type of equity analysis to perform."""
    FUNDAMENTAL = "fundamental"
    VALUATION = "valuation"
    GROWTH = "growth"
    COMPREHENSIVE = "comprehensive"
    COMPARISON = "comparison"
    SECTOR = "sector"

class PlanResponseType(str, Enum):
    """Classification of user response to plan."""
    APPROVAL = "approval"
    REFINEMENT = "refinement"
    NEW_QUERY = "new_query"

class EnhancedMetricSpec(BaseModel):
    metric_name: str
    category: MetricCategory
    chart_type: Literal["line", "bar", "area"]
    data_source: Literal["financial", "valuation", "market", "news"]
    section: str
    priority: int  # 1-10
    search_query: str
    calculation_formula: str | None = None
    is_market_specific: bool = False

class EnhancedResearchPlan(BaseModel):
    company_name: str
    ticker: str
    exchange: str
    market: str  # US, India, China, Japan, Korea, Europe
    analysis_type: AnalysisType
    time_range_years: int = 5
    metrics_to_analyze: list[EnhancedMetricSpec]  # 10-15 metrics
    report_sections: list[str]
    infographic_count: int = 3
    plan_version: int = 1
    approved_by_user: bool = False

class PlanResponseClassification(BaseModel):
    response_type: PlanResponseType
    reasoning: str
    refinement_request: str | None = None
```

### Data Schemas

```python
class DataPoint(BaseModel):
    period: str      # "2023", "Q1 2024"
    value: float
    unit: str        # "USD", "%", "millions"

class MetricData(BaseModel):
    metric_name: str
    data_points: list[DataPoint]
    chart_type: Literal["line", "bar", "area"]
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

### Visual Schemas

```python
class ChartResult(BaseModel):
    chart_index: int
    metric_name: str
    filename: str        # "chart_1.png"
    base64_data: str
    section: str

class VisualContext(BaseModel):
    visual_id: str       # "chart_1", "infographic_2"
    visual_type: Literal["chart", "infographic", "table"]
    setup_text: str      # Text BEFORE visual
    interpretation_text: str  # Text AFTER visual

class InfographicSpec(BaseModel):
    infographic_id: int
    title: str
    infographic_type: Literal["business_model", "competitive_landscape", "growth_drivers"]
    key_elements: list[str]
    visual_style: str
    prompt: str

class InfographicPlan(BaseModel):
    company_name: str
    infographics: list[InfographicSpec]  # 2-5 items

class InfographicResult(BaseModel):
    infographic_id: int
    title: str
    filename: str
    base64_data: str
    infographic_type: str
```

---

## Callback Reference

### Phase 1 Callbacks (Validation & Routing)

| Callback | File | Trigger | Purpose |
|----------|------|---------|---------|
| `ensure_classifier_state_callback` | state_management.py | before root_agent | Initialize state, reset turn flags |
| `check_validation_callback` | routing.py | after query_validator | Stop if invalid query |
| `check_classification_callback` | routing.py | after query_classifier | Stop if FOLLOW_UP, handle post-approval |
| `skip_if_rejected_callback` | routing.py | before pipeline stages | Skip if rejection occurred |

### Phase 2 Callbacks (HITL Planning)

| Callback | File | Trigger | Purpose |
|----------|------|---------|---------|
| `check_plan_state_callback` | planning.py | before hitl_planning_agent | Route based on plan_state |
| `skip_if_plan_exists` | agent.py | before metric_planner | Skip if plan already exists |
| `present_plan_callback` | planning.py | after metric_planner | Format plan, set pending, STOP |
| `skip_if_not_pending` | agent.py | before plan_response_classifier | Skip if not pending or just presented |
| `process_plan_response_callback` | planning.py | after plan_response_classifier | Handle approval/refinement/new_query |
| `skip_if_not_refinement` | agent.py | before plan_refiner | Skip if not refinement request |
| `re_present_plan_after_refinement` | agent.py | after plan_refiner | Re-present updated plan |
| `skip_if_not_approved_callback` | planning.py | before pipeline | Skip if plan not approved |

### Pipeline Callbacks

| Callback | File | Trigger | Purpose |
|----------|------|---------|---------|
| `initialize_charts_state_callback` | state_management.py | before chart loop | Reset chart state |
| `execute_chart_code_callback` | chart_execution.py | after chart_code_generator | Execute ONE chart in sandbox (sequential mode) |
| `execute_batch_charts_callback` | batch_chart_execution.py | after batch_chart_generator | Execute ALL charts in sandbox (batch mode) |
| `create_infographics_summary_callback` | infographic_summary.py | after infographic_generator | Create lightweight summary |
| `save_html_report_callback` | report_generation.py | after html_report_generator | Inject images, save HTML/PDF |

---

## Configuration

All configuration is centralized in `app/config.py`:

```python
# Models
MODEL = "gemini-3-flash-preview"           # Main model for all agents
IMAGE_MODEL = "gemini-3-pro-image-preview" # Infographic generation

# Chart Generation
MAX_CHARTS = 10
MAX_CHART_ITERATIONS = 15
CHART_DPI = 150
CHART_WIDTH = 12  # inches
CHART_HEIGHT = 6  # inches
CHART_STYLE = "ggplot"

# Batch Chart Generation (Experimental)
ENABLE_BATCH_CHARTS = False  # Set True for ~5-10x speedup

# Infographics
MIN_INFOGRAPHICS = 2
MAX_INFOGRAPHICS = 5
INFOGRAPHIC_WIDTH = 1200   # pixels
INFOGRAPHIC_HEIGHT = 800   # pixels

# Report Output
HTML_REPORT_FILENAME = "equity_report.html"
CHART_FILENAME_TEMPLATE = "chart_{index}.png"
INFOGRAPHIC_FILENAME_TEMPLATE = "infographic_{index}.png"

# PDF Export
ENABLE_PDF_EXPORT = True   # Generates PDF alongside HTML
PDF_REPORT_FILENAME = "equity_report.pdf"

# Parallel Fetchers
PARALLEL_DATA_FETCHERS = 4

# Retry Configuration
RETRY_ATTEMPTS = 3
RETRY_INITIAL_DELAY = 2    # seconds
RETRY_MAX_DELAY = 10       # seconds
```

### Environment Variables

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=1
SANDBOX_RESOURCE_NAME=projects/.../sandboxes/...
ENABLE_PDF_EXPORT=true
ENABLE_BATCH_CHARTS=true   # Experimental: ~5-10x speedup for chart generation
LOG_LEVEL=INFO
```

---

## Boundary Validation

The agent rejects queries that fall outside its scope. Configuration is in `app/rules/boundaries_config.py`.

| Category | Example Keywords | Rejection Reason |
|----------|-----------------|------------------|
| **Crypto/NFT** | bitcoin, ethereum, nft, defi | Cryptocurrency analysis not supported |
| **Trading Advice** | should i buy, sell now, entry point | Buy/sell recommendations not provided |
| **Private Companies** | startup valuation, pre-ipo, unlisted | Requires public financials |
| **Personal Finance** | my portfolio, retirement planning | Consult a financial advisor |
| **Non-Financial** | weather, recipe, travel | Only equity research supported |
| **Penny Stocks** | otc market, pink sheets | Limited data availability |

---

## Key Design Decisions

### 1. Callback-Based Routing (vs. Conditional Agents)

Return `types.Content` to stop pipeline, `None` to continue. This gives fine-grained control over agent execution without complex conditional logic.

```python
def check_validation_callback(callback_context: CallbackContext) -> Content | None:
    validation = callback_context.state.get("query_validation", {})
    if not validation.get("is_valid", True):
        # Return Content to stop the pipeline
        return Content(parts=[Part(text=validation["rejection_reason"])])
    return None  # Continue to next agent
```

### 2. Turn Gating Pattern

SequentialAgent continues after callbacks return Content. We use `plan_presented_this_turn` flag to prevent subsequent agents from running in the same turn.

```python
# After presenting plan
state["plan_presented_this_turn"] = True
state["plan_state"] = "pending"

# In subsequent agent's before_callback
if state.get("plan_presented_this_turn"):
    return Content(parts=[Part(text="")])  # Skip this turn
```

### 3. Asyncio for Infographics (vs. ParallelAgent)

Single `infographic_generator` agent calls `generate_all_infographics` tool which uses `asyncio.gather()` for true parallelism within a single agent. This is more efficient than spawning multiple agents.

```python
async def generate_all_infographics(plan: InfographicPlan) -> list[InfographicResult]:
    tasks = [generate_single(spec) for spec in plan.infographics]
    return await asyncio.gather(*tasks)
```

### 4. Custom BaseAgent for Loop Control

`ChartProgressChecker` uses `EventActions(escalate=True)` to exit the LoopAgent when all charts are generated.

```python
class ChartProgressChecker(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator:
        charts_done = len(ctx.session.state.get("charts_generated", []))
        total_metrics = len(ctx.session.state.get("consolidated_data", {}).get("metrics", []))

        if charts_done >= total_metrics:
            yield Event(actions=EventActions(escalate=True))
```

### 5. State Machine for HITL

`plan_state` variable tracks the planning workflow:

```
"none" → (plan generated) → "pending" → (user approves) → "approved"
                               ↓
                         (user refines)
                               ↓
                         "pending" (updated plan)
```

---

## Project Structure (Detailed)

```
adk-equity-deep-research/
├── app/
│   ├── __init__.py
│   ├── agent.py                    # Root agent + HITL planning orchestration
│   ├── config.py                   # All configuration (models, limits, etc.)
│   │
│   ├── callbacks/                  # Agent lifecycle callbacks
│   │   ├── __init__.py
│   │   ├── chart_execution.py      # execute_chart_code_callback (sequential)
│   │   ├── batch_chart_execution.py # execute_batch_charts_callback (batch)
│   │   ├── infographic_summary.py  # create_infographics_summary_callback
│   │   ├── planning.py             # HITL callbacks (present, process, skip)
│   │   ├── report_generation.py    # save_html_report_callback
│   │   ├── routing.py              # Validation/classification routing
│   │   └── state_management.py     # State initialization, turn gating
│   │
│   ├── rules/                      # Templatized configuration
│   │   ├── __init__.py
│   │   ├── boundaries_config.py    # Rejection rules (crypto, trading, etc.)
│   │   └── markets_config.py       # Supported markets and hints
│   │
│   ├── schemas/                    # Pydantic models
│   │   ├── __init__.py
│   │   ├── chart.py                # ChartResult, VisualContext, AnalysisSections
│   │   ├── data.py                 # DataPoint, MetricData, ConsolidatedResearchData
│   │   ├── infographic.py          # InfographicSpec, InfographicPlan, InfographicResult
│   │   └── research.py             # MetricSpec, ResearchPlan, Enhanced*, QueryClassification
│   │
│   ├── sub_agents/                 # All sub-agents
│   │   ├── __init__.py
│   │   ├── analysis/
│   │   │   └── agent.py            # analysis_writer
│   │   ├── chart_generator/
│   │   │   ├── __init__.py         # Conditional export (batch vs sequential)
│   │   │   ├── agent.py            # chart_code_generator (sequential)
│   │   │   ├── batch_agent.py      # batch_chart_generator (batch mode)
│   │   │   ├── loop_pipeline.py    # chart_generation_loop (LoopAgent)
│   │   │   └── progress_checker.py # ChartProgressChecker (Custom BaseAgent)
│   │   ├── classifier/
│   │   │   ├── agent.py            # query_classifier
│   │   │   └── follow_up_handler.py
│   │   ├── consolidator/
│   │   │   └── agent.py            # data_consolidator
│   │   ├── data_fetchers/
│   │   │   ├── financial.py        # financial_data_fetcher
│   │   │   ├── valuation.py        # valuation_data_fetcher
│   │   │   ├── market.py           # market_data_fetcher
│   │   │   ├── news.py             # news_sentiment_fetcher
│   │   │   └── parallel_pipeline.py # parallel_data_gatherers (ParallelAgent)
│   │   ├── infographic/
│   │   │   ├── generator.py        # infographic_generator
│   │   │   └── planner.py          # infographic_planner
│   │   ├── planner/
│   │   │   ├── agent.py            # research_planner (Phase 1)
│   │   │   ├── metric_planner.py   # metric_planner (Phase 2 HITL)
│   │   │   ├── plan_response_classifier.py
│   │   │   └── plan_refiner.py
│   │   ├── report_generator/
│   │   │   └── agent.py            # html_report_generator
│   │   └── validator/
│   │       └── agent.py            # query_validator
│   │
│   └── tools/                      # Custom tools
│       ├── __init__.py
│       └── infographic_tools.py    # generate_infographic, generate_all_infographics
│
├── .docs/                          # Documentation
│   └── new_flow/
│       └── IMPLEMENTATION_PLAN_v2.md
│
├── .env                            # Environment variables
├── manage_sandbox.py               # Sandbox lifecycle management
├── requirements.txt
└── README.md
```

---

## Sources & References

- [ADK Documentation](https://google.github.io/adk-docs/)
- [ADK Agents Reference](https://google.github.io/adk-docs/agents/)
- [ADK Callbacks](https://google.github.io/adk-docs/callbacks/)
- [Gemini Image Generation](https://ai.google.dev/gemini-api/docs/image-generation)

---

**Last Updated**: 2026-01-24
