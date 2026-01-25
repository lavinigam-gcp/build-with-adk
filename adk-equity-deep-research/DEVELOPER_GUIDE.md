# Developer Guide: Equity Research Report Agent

This guide provides a deep technical dive into the agent architecture, state management, callbacks, and Pydantic schemas. For getting started and basic usage, see [README.md](README.md).

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [ADK Patterns Used](#adk-patterns-used)
- [State Management](#state-management)
- [Pydantic Schemas](#pydantic-schemas)
- [Callback Reference](#callback-reference)
- [Data Fetcher Architecture](#data-fetcher-architecture)
- [Sandbox & Code Execution](#sandbox--code-execution)
- [HITL Planning Flow](#hitl-planning-flow)
- [Multi-Market Support](#multi-market-support)
- [Configuration](#configuration)
- [Boundary Validation](#boundary-validation)
- [Key Design Decisions](#key-design-decisions)
- [Project Structure](#project-structure)

---

## Architecture Overview

<p align="center">
  <img src="assets/system-architecture.jpeg" alt="Detailed System Architecture" width="900">
</p>

### Agent Hierarchy

```
Root Agent (SequentialAgent: equity_research_agent)
|
+-- Stage 0: query_validator (LlmAgent)
|   +-- Boundary checking (crypto, trading advice, etc.)
|   +-- after_agent_callback: check_validation_callback
|
+-- Stage 1: query_classifier (LlmAgent)
|   +-- NEW_QUERY vs FOLLOW_UP classification
|   +-- Auto-detects market from company/query context
|   +-- after_agent_callback: check_classification_callback
|
+-- Stage 2: hitl_planning_agent (SequentialAgent)
|   +-- metric_planner (LlmAgent)
|   |   +-- Generates EnhancedResearchPlan with 10-15 metrics
|   |   +-- before: skip_if_plan_exists
|   |   +-- after: present_plan_callback (STOPS for user approval)
|   |
|   +-- plan_response_classifier (LlmAgent)
|   |   +-- Classifies response: approval/refinement/new_query
|   |   +-- before: skip_if_not_pending
|   |   +-- after: process_plan_response_callback
|   |
|   +-- plan_refiner (LlmAgent)
|       +-- Updates plan based on refinement feedback
|       +-- before: skip_if_not_refinement
|       +-- after: re_present_plan_after_refinement (STOPS again)
|
+-- Stage 3-10: equity_research_pipeline (SequentialAgent)
    |   before_agent_callback: skip_if_not_approved_callback
    |
    +-- research_planner (LlmAgent)
    |   +-- Phase 1 fallback if no enhanced plan
    |
    +-- parallel_data_gatherers (ParallelAgent)
    |   +-- financial_fetcher (yfinance + google_search fallback)
    |   +-- valuation_fetcher (yfinance + google_search fallback)
    |   +-- market_fetcher (yfinance + google_search fallback)
    |   +-- news_fetcher (google_search only)
    |
    +-- data_consolidator (LlmAgent)
    |   +-- Merges 4 data streams into ConsolidatedResearchData
    |
    +-- chart_generation_agent (LlmAgent or LoopAgent)
    |   +-- [BATCH MODE] batch_chart_generator - ALL charts at once
    |   +-- [SEQUENTIAL MODE] chart_generation_loop - one at a time
    |
    +-- infographic_planner (LlmAgent)
    |   +-- Plans 2-5 AI-generated infographics
    |
    +-- infographic_generator (LlmAgent)
    |   +-- Batch generates all infographics (asyncio.gather)
    |
    +-- analysis_writer (LlmAgent)
    |   +-- Writes professional narrative with Setup->Visual->Interpretation
    |
    +-- html_report_generator (LlmAgent)
        +-- Creates multi-page HTML report
        +-- after: save_html_report_callback
```

### Stage Summary

| Stage | Agent | ADK Type | Purpose |
|-------|-------|----------|---------|
| 0 | query_validator | LlmAgent | Rejects unsupported queries |
| 1 | query_classifier | LlmAgent | Classifies query type, detects market |
| 2 | hitl_planning_agent | SequentialAgent | HITL plan generation and approval |
| 3 | research_planner | LlmAgent | Plans metrics (fallback) |
| 4 | parallel_data_gatherers | ParallelAgent | Concurrent data fetching (4x speed) |
| 5 | data_consolidator | LlmAgent | Merges data streams |
| 6 | chart_generation_agent | LlmAgent/LoopAgent | Generates 5-10 charts (batch or sequential) |
| 7 | infographic_planner | LlmAgent | Plans 2-5 infographics |
| 8 | infographic_generator | LlmAgent | Generates infographics |
| 9 | analysis_writer | LlmAgent | Writes professional analysis |
| 10 | html_report_generator | LlmAgent | Creates final HTML report |

---

## ADK Patterns Used

### Agent Types

| Agent Type | Usage | Description |
|------------|-------|-------------|
| **SequentialAgent** | Root agent, HITL planning, Pipeline | Runs sub-agents in order |
| **ParallelAgent** | Data fetchers | Runs 4 fetchers concurrently |
| **LoopAgent** | Chart generation (sequential mode) | Iterates until all charts done |
| **LlmAgent** | Most agents | LLM-powered agents with output_schema |
| **Custom BaseAgent** | ChartProgressChecker | Custom logic for loop exit |

### Code Examples

#### SequentialAgent

```python
from google.adk.agents import SequentialAgent

root_agent = SequentialAgent(
    name="equity_research_agent",
    description="...",
    before_agent_callback=ensure_classifier_state_callback,
    sub_agents=[
        query_validator_with_routing,
        query_classifier_with_routing,
        hitl_planning_agent,
        equity_research_pipeline,
    ],
)
```

#### ParallelAgent

```python
from google.adk.agents import ParallelAgent

parallel_data_gatherers = ParallelAgent(
    name="parallel_data_gatherers",
    description="4 concurrent data fetchers",
    sub_agents=[
        financial_fetcher,
        valuation_fetcher,
        market_fetcher,
        news_fetcher,
    ],
)
```

#### LlmAgent with Structured Output

```python
from google.adk.agents import LlmAgent

query_validator = LlmAgent(
    model=MODEL,
    name="query_validator",
    description="Validates queries against boundary rules",
    instruction="...",
    output_schema=QueryValidation,  # Pydantic model
    output_key="query_validation",   # State key to store output
)
```

### Callback Patterns

| Callback Type | Pattern | Usage |
|---------------|---------|-------|
| `before_agent_callback` | Return `Content` to skip, `None` to continue | Skip agents based on state |
| `after_agent_callback` | Return `Content` to replace output, `None` to keep | Routing decisions, code execution |
| Turn Gating | Set flags, check in subsequent callbacks | Prevent auto-execution after plan presentation |

---

## State Management

| State Variable | Type | Set By | Used By | Description |
|----------------|------|--------|---------|-------------|
| `query_validation` | dict | query_validator | check_validation_callback | Validation result |
| `query_classification` | dict | query_classifier | check_classification_callback | Classification result |
| `plan_state` | str | planning callbacks | HITL agents, skip_if_not_approved | "none" / "pending" / "approved" |
| `enhanced_research_plan` | EnhancedResearchPlan | metric_planner / plan_refiner | pipeline agents | The approved research plan |
| `plan_response` | PlanResponseClassification | plan_response_classifier | process_plan_response_callback | User's response classification |
| `plan_presented_this_turn` | bool | present_plan_callback | skip_if_not_pending | Turn-gating flag |
| `skip_pipeline` | bool | routing callbacks | all pipeline agents | Stops pipeline on rejection |
| `detected_market` | str | check_classification_callback | data fetchers | Auto-detected market code |
| `consolidated_data` | ConsolidatedResearchData | data_consolidator | chart_generator, analysis_writer | Merged research data |
| `charts_generated` | list[dict] | execute_chart_code_callback | report_generator | Chart results with base64 |
| `charts_summary` | list[dict] | execute_chart_code_callback | analysis_writer | Chart info (no base64) |
| `infographics_summary` | list[dict] | infographic_generator | report_generator | Infographic results |
| `analysis_sections` | AnalysisSections | analysis_writer | report_generator | All analysis sections |

### State Flow

```
Turn 1: User query
  +-> query_validation, query_classification
  +-> plan_state="none" -> metric_planner runs
  +-> enhanced_research_plan created
  +-> plan_state="pending", plan_presented_this_turn=True
  +-> STOP (show plan)

Turn 2: User says "looks good"
  +-> plan_presented_this_turn=False (reset by ensure_classifier_state)
  +-> plan_response_classifier runs -> plan_response={type: "approval"}
  +-> plan_state="approved"
  +-> Pipeline runs...
  +-> consolidated_data, charts_generated, infographics_summary, analysis_sections
  +-> Final HTML report saved
```

---

## Pydantic Schemas

### HITL Planning Schemas

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

### Validation & Routing Callbacks

| Callback | File | Trigger | Purpose |
|----------|------|---------|---------|
| `ensure_classifier_state_callback` | state_management.py | before root_agent | Initialize state, reset turn flags |
| `check_validation_callback` | routing.py | after query_validator | Stop if invalid query |
| `check_classification_callback` | routing.py | after query_classifier | Stop if FOLLOW_UP, handle post-approval |
| `skip_if_rejected_callback` | routing.py | before pipeline stages | Skip if rejection occurred |

### HITL Planning Callbacks

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
| `execute_chart_code_callback` | chart_execution.py | after chart_code_generator | Execute ONE chart in sandbox (sequential) |
| `execute_batch_charts_callback` | batch_chart_execution.py | after batch_chart_generator | Execute ALL charts in sandbox (batch) |
| `create_infographics_summary_callback` | infographic_summary.py | after infographic_generator | Create lightweight summary |
| `save_html_report_callback` | report_generation.py | after html_report_generator | Inject images, save HTML/PDF |

---

## Data Fetcher Architecture

Data fetchers use a **hybrid approach** combining yfinance (structured financial data) with Google Search (qualitative context).

```
enhanced_research_plan
         |
         v
+-------------------------------------------------------------+
|              ParallelAgent (parallel_data_gatherers)         |
|  +-----------+ +-----------+ +-----------+ +---------------+ |
|  | financial | | valuation | | market    | | news_         | |
|  | _fetcher  | | _fetcher  | | _fetcher  | | sentiment     | |
|  |           | |           | |           | | _fetcher      | |
|  | yfinance  | | yfinance  | | yfinance  | | google_search | |
|  | +fallback | | +fallback | | +fallback | |               | |
|  +-----+-----+ +-----+-----+ +-----+-----+ +-------+-------+ |
|        |             |             |               |         |
|        v             v             v               v         |
|   financial     valuation     market_data      news_data     |
+-------------------------------------------------------------+
                          |
                          v
                  data_consolidator
```

### yfinance Tools

Four custom tools in `app/tools/yfinance_tools.py`:

| Tool | Data Returned | Used By |
|------|---------------|---------|
| `get_financial_statements` | Revenue, Net Income, Margins, EPS (4-5 years) | financial_data_fetcher |
| `get_valuation_metrics` | P/E, P/B, P/S, EV/EBITDA, Market Cap | valuation_data_fetcher |
| `get_market_data` | Current price, 52-week range, volume, price history | market_data_fetcher |
| `get_analyst_data` | Price targets, recommendation summary | valuation_data_fetcher |

### Mixing Tools: bypass_multi_tools_limit

**Critical ADK Limitation:** The Gemini Interactions API does not support mixing built-in tools (like `google_search`) with custom function tools in the same agent.

**Solution:** Use `GoogleSearchTool(bypass_multi_tools_limit=True)` to convert the built-in tool into a function calling tool.

```python
from google.adk.agents import LlmAgent
from google.adk.tools.google_search_tool import GoogleSearchTool
from app.tools.yfinance_tools import get_financial_statements

# CRITICAL: bypass_multi_tools_limit=True allows mixing with custom tools
google_search = GoogleSearchTool(bypass_multi_tools_limit=True)

financial_data_fetcher = LlmAgent(
    model=MODEL,
    name="financial_data_fetcher",
    tools=[get_financial_statements, google_search],  # Mixed tools now work
    ...
)
```

### Ticker Resolution

The `app/tools/ticker_resolver.py` module resolves company names to Yahoo Finance tickers:

```python
from app.tools import resolve_ticker

# Examples
resolve_ticker("Apple", "US")           # -> {"ticker": "AAPL", "validated": True}
resolve_ticker("Reliance Industries", "India")  # -> {"ticker": "RELIANCE.NS", "validated": True}
resolve_ticker("Toyota", "Japan")       # -> {"ticker": "7203.T", "validated": True}
```

**Supported Market Suffixes:**

| Market | Suffix | Example |
|--------|--------|---------|
| US | (none) | `AAPL` |
| India | `.NS` (NSE) | `RELIANCE.NS` |
| Japan | `.T` (TSE) | `7203.T` |
| Korea | `.KS` (KRX) | `005930.KS` |
| Hong Kong | `.HK` | `9988.HK` |
| UK | `.L` | `SHEL.L` |
| Germany | `.DE` | `SAP.DE` |

---

## Sandbox & Code Execution

The Agent Engine Sandbox provides isolated Python execution for secure chart generation.

### Execution Modes

| Mode | Flag | LLM Calls | Sandbox Calls | Speed |
|------|------|-----------|---------------|-------|
| **Sequential** (default) | `ENABLE_BATCH_CHARTS=false` | N (one per chart) | N (one per chart) | ~60-120s |
| **Batch** (recommended) | `ENABLE_BATCH_CHARTS=true` | 1 (all charts) | 1 (all charts) | ~10-20s |

### Batch Mode Architecture

```
+------------------------------------------------------------+
|  LlmAgent: batch_chart_generator                            |
|  -> Generates code for ALL charts in a single script        |
|  -> Script loops through metrics with try/except            |
|  -> Saves chart_1.png, chart_2.png, ..., chart_N.png       |
+------------------------------------------------------------+
                           |
                           v
+------------------------------------------------------------+
|  after_agent_callback: execute_batch_charts_callback       |
|  1. Extract code from markdown ```python blocks            |
|  2. Execute ONCE in sandbox                                |
|  3. Loop through response.outputs                          |
|  4. Match chart_N.png pattern to extract all charts        |
|  5. Save each chart as ADK artifact                        |
|  6. Populate charts_generated and charts_summary           |
+------------------------------------------------------------+
                           |
                           v
+------------------------------------------------------------+
|  Agent Engine Sandbox (Vertex AI)                          |
|  - Executes single batch script                            |
|  - Generates all charts in one execution                   |
|  - Returns: multiple image outputs + execution logs        |
|  - Timeout: 300 seconds (sufficient for 10+ charts)        |
+------------------------------------------------------------+
```

### Sandbox Capabilities

| Capability | Value | Notes |
|------------|-------|-------|
| Timeout | 300 seconds | Sufficient for 10+ charts in batch |
| File size limit | 100MB per request/response | Well within limits for charts |
| Multiple outputs | YES | `response.outputs` is a list |
| Pre-installed packages | matplotlib, numpy, pandas | No seaborn in sandbox |
| Output identification | `output.metadata.attributes["file_name"]` | Used to match chart patterns |

### Sandbox Management

Use `manage_sandbox.py` to manage sandboxes:

```bash
# Create a new sandbox
python manage_sandbox.py create --name "financial_viz_sandbox"

# List existing sandboxes
python manage_sandbox.py list

# Test sandbox functionality
python manage_sandbox.py test --sandbox-id "projects/.../sandboxes/..."

# Delete a sandbox
python manage_sandbox.py delete --sandbox-id "projects/.../sandboxes/..."
```

---

## HITL Planning Flow

### Flow Diagram

```
User Query
    |
    v
+-----------------+
| query_validator |  --rejected--> Rejection Message + STOP
+--------+--------+
         | valid
         v
+-----------------+
|query_classifier |  --FOLLOW_UP--> Guidance Message + STOP
+--------+--------+
         | NEW_QUERY
         v
+--------------------------------------------------------+
|               hitl_planning_agent                       |
|                                                         |
|  plan_state == "none"                                   |
|       |                                                 |
|       v                                                 |
|  +---------------+                                      |
|  | metric_planner| -> Generates EnhancedResearchPlan    |
|  +-------+-------+                                      |
|          |                                              |
|          v                                              |
|  present_plan_callback -> Shows plan as markdown table  |
|          |                                              |
|          v                                              |
|    STOP (wait for user)                                 |
|          |                                              |
|  User responds: "looks good" / "add ROE" / "analyze X"  |
|          |                                              |
|          v                                              |
|  plan_state == "pending"                                |
|          |                                              |
|          v                                              |
|  +------------------------+                             |
|  |plan_response_classifier| -> approval/refinement/new  |
|  +-----------+------------+                             |
|              |                                          |
|    +---------+---------+                                |
|    v         v         v                                |
| approval  refinement  new_query                         |
|    |         |         |                                |
|    |         v         v                                |
|    |   plan_refiner   reset state                       |
|    |         |         |                                |
|    |         v         |                                |
|    |   re-present      |                                |
|    |   (loop back)     |                                |
|    |                   |                                |
|    v                   v                                |
| plan_state="approved"  plan_state="none"                |
+--------------------------------------------------------+
         |
         v
+--------------------------------------------------------+
|           equity_research_pipeline                      |
|   (only runs if plan_state == "approved")              |
+--------------------------------------------------------+
```

### Turn-Gating Pattern

A critical pattern prevents agents from running in the wrong turn:

```python
# In present_plan_callback:
state["plan_presented_this_turn"] = True  # Set flag

# In skip_if_not_pending (before plan_response_classifier):
if state.get("plan_presented_this_turn"):
    # Skip - plan was just presented, don't classify yet
    return types.Content(role="model", parts=[types.Part.from_text(text="")])

# In ensure_classifier_state_callback (before root agent, each turn):
state["plan_presented_this_turn"] = False  # Reset for new turn
```

### Plan Response Types

| Response | Example | Action |
|----------|---------|--------|
| `approval` | "looks good", "proceed", "approved" | Set plan_state="approved", continue to pipeline |
| `refinement` | "add ROE", "remove P/E", "use bar charts" | Update plan via plan_refiner, re-present |
| `new_query` | "analyze Apple instead" | Reset state, generate new plan |

---

## Multi-Market Support

### Supported Markets

| Market | Exchanges | Currency | Market-Specific Metrics |
|--------|-----------|----------|------------------------|
| **US** | NYSE, NASDAQ, AMEX | USD ($) | - |
| **India** | NSE, BSE | INR | Promoter Holding %, FII/DII Flows, Promoter Pledge % |
| **China** | SSE, SZSE, HKEX | CNY | State Ownership %, A-Share vs H-Share Premium |
| **Japan** | TSE, OSE | JPY | Keiretsu Affiliation, Cross-Shareholding % |
| **Korea** | KRX, KOSDAQ | KRW | Chaebol Affiliation, Foreign Ownership Limit |
| **Europe** | LSE, Euronext, XETRA, SIX | EUR | ESG Compliance Score, EU Taxonomy Alignment |

### Market Detection

Markets are auto-detected from query context using keyword hints:

```python
MARKET_DETECTION_HINTS = {
    "US": ["nyse", "nasdaq", "apple", "microsoft", "tesla", ...],
    "India": ["nse", "bse", "reliance", "tata", "infosys", ...],
    "China": ["shanghai", "alibaba", "tencent", "baidu", ...],
    "Japan": ["tokyo", "nikkei", "toyota", "sony", "honda", ...],
    "Korea": ["kospi", "samsung", "hyundai", "lg", "naver", ...],
    "Europe": ["london", "ftse", "dax", "asml", "nestle", ...],
}
```

### Adding a New Market

1. Add market definition to `app/rules/markets_config.py`:

```python
SUPPORTED_MARKETS["Brazil"] = {
    "name": "Brazil",
    "exchanges": ["B3"],
    "currency": "BRL",
    "currency_symbol": "R$",
    "major_indices": ["Ibovespa"],
    "specific_metrics": ["Selic Rate Sensitivity"],
}
```

2. Add detection hints:

```python
MARKET_DETECTION_HINTS["Brazil"] = [
    "b3", "bovespa", "ibovespa", "brazil stock",
    "petrobras", "vale", "itau", "bradesco", ...
]
```

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

# Batch Chart Generation
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

# yfinance Configuration
YFINANCE_MAX_REQUESTS_PER_MINUTE = 30
YFINANCE_MAX_CONCURRENT_REQUESTS = 2
YFINANCE_CACHE_TTL_HOURS = 1
YFINANCE_MAX_RETRIES = 3
YFINANCE_RETRY_BASE_DELAY = 1.0  # seconds

# Retry Configuration
RETRY_ATTEMPTS = 3
RETRY_INITIAL_DELAY = 2    # seconds
RETRY_MAX_DELAY = 10       # seconds
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_CLOUD_PROJECT` | Yes | - | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | No | us-central1 | GCP region |
| `SANDBOX_RESOURCE_NAME` | Yes* | - | Sandbox resource name (for chart generation) |
| `AGENT_ENGINE_RESOURCE_NAME` | No | - | Agent Engine resource (auto-created if not set) |
| `MODEL` | No | gemini-3-flash-preview | Main LLM model |
| `IMAGE_MODEL` | No | gemini-3-pro-image-preview | Image generation model |
| `ENABLE_PDF_EXPORT` | No | true | Enable PDF generation |
| `ENABLE_BATCH_CHARTS` | No | false | Enable batch chart generation (~5-10x faster) |
| `LOG_LEVEL` | No | INFO | Logging level |

*Required for chart generation to work.

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
"none" -> (plan generated) -> "pending" -> (user approves) -> "approved"
                               |
                         (user refines)
                               |
                         "pending" (updated plan)
```

---

## Project Structure

```
adk-equity-deep-research/
+-- app/
|   +-- __init__.py
|   +-- agent.py                    # Root agent + HITL planning orchestration
|   +-- config.py                   # All configuration (models, limits, etc.)
|   |
|   +-- callbacks/                  # Agent lifecycle callbacks
|   |   +-- __init__.py
|   |   +-- chart_execution.py      # execute_chart_code_callback (sequential)
|   |   +-- batch_chart_execution.py # execute_batch_charts_callback (batch)
|   |   +-- infographic_summary.py  # create_infographics_summary_callback
|   |   +-- planning.py             # HITL callbacks (present, process, skip)
|   |   +-- report_generation.py    # save_html_report_callback
|   |   +-- routing.py              # Validation/classification routing
|   |   +-- state_management.py     # State initialization, turn gating
|   |
|   +-- rules/                      # Templatized configuration
|   |   +-- __init__.py
|   |   +-- boundaries_config.py    # Rejection rules (crypto, trading, etc.)
|   |   +-- markets_config.py       # Supported markets and hints
|   |
|   +-- schemas/                    # Pydantic models
|   |   +-- __init__.py
|   |   +-- chart.py                # ChartResult, VisualContext, AnalysisSections
|   |   +-- data.py                 # DataPoint, MetricData, ConsolidatedResearchData
|   |   +-- infographic.py          # InfographicSpec, InfographicPlan, InfographicResult
|   |   +-- research.py             # MetricSpec, ResearchPlan, Enhanced*, QueryClassification
|   |
|   +-- sub_agents/                 # All sub-agents
|   |   +-- __init__.py             # Exports all agents
|   |   +-- validator/              # Query validation
|   |   |   +-- agent.py
|   |   +-- classifier/             # Query classification
|   |   |   +-- agent.py
|   |   |   +-- follow_up_handler.py
|   |   +-- planner/                # HITL planning agents
|   |   |   +-- agent.py            # research_planner
|   |   |   +-- metric_planner.py
|   |   |   +-- plan_response_classifier.py
|   |   |   +-- plan_refiner.py
|   |   +-- data_fetchers/          # Parallel data fetching (yfinance + google_search)
|   |   |   +-- financial.py        # yfinance: get_financial_statements
|   |   |   +-- valuation.py        # yfinance: get_valuation_metrics, get_analyst_data
|   |   |   +-- market.py           # yfinance: get_market_data
|   |   |   +-- news.py             # google_search only
|   |   |   +-- parallel_pipeline.py
|   |   +-- consolidator/           # Data merging
|   |   |   +-- agent.py
|   |   +-- chart_generator/        # Chart generation (batch or sequential)
|   |   |   +-- __init__.py         # Conditional export based on feature flag
|   |   |   +-- agent.py            # chart_code_generator (sequential)
|   |   |   +-- batch_agent.py      # batch_chart_generator (batch mode)
|   |   |   +-- loop_pipeline.py
|   |   |   +-- progress_checker.py
|   |   +-- infographic/            # Infographic generation
|   |   |   +-- planner.py
|   |   |   +-- generator.py
|   |   +-- analysis/               # Analysis writing
|   |   |   +-- agent.py
|   |   +-- report_generator/       # HTML report generation
|   |       +-- agent.py
|   |
|   +-- tools/                      # Custom tools
|       +-- __init__.py             # Tool exports
|       +-- infographic_tools.py    # Gemini image generation
|       +-- yfinance_tools.py       # Financial data tools (yfinance)
|       +-- ticker_resolver.py      # Company name -> ticker resolution
|       +-- rate_limiter.py         # API rate limiting utilities
|
+-- assets/                         # Architecture diagrams and images
|   +-- use-case-poster.jpeg
|   +-- high-level-architecture.jpeg
|   +-- system-architecture.jpeg
|
+-- .docs/                          # Documentation
|   +-- project_overview.md
|   +-- image_prompts/              # JSON prompts for diagram generation
|
+-- manage_sandbox.py               # Sandbox lifecycle management
+-- requirements.txt
+-- README.md
+-- DEVELOPER_GUIDE.md              # This file
```

---

## Sources & References

- [ADK Documentation](https://google.github.io/adk-docs/)
- [ADK Agents Reference](https://google.github.io/adk-docs/agents/)
- [ADK Callbacks](https://google.github.io/adk-docs/callbacks/)
- [Gemini Image Generation](https://ai.google.dev/gemini-api/docs/image-generation)
- [yfinance Documentation](https://github.com/ranaroussi/yfinance)

---

**Last Updated**: 2025-01-25
