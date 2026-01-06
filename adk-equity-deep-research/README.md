# Experiment 004: Professional-Grade Equity Research Report Agent

## Status: WORKING (v2.1 - Professional Grade with HITL) ✅

**Version 2.1 (2026-01-06)**: Added boundary validation, multi-market support, and callback-based routing.

**Version 2.0 (2025-12-30)**: Upgraded to Morgan Stanley / Goldman Sachs standards with "Setup → Visual → Interpretation" pattern for all visuals.

A sophisticated multi-chart equity research report generator that produces **professional investment-grade reports** with contextualized visualizations, AI-generated infographics, data tables, and comprehensive company coverage.

**v2.1 Key Improvements** (Phase 1 - Foundation):
- ✅ **Boundary Validation**: Rejects unsupported queries (crypto, trading advice, private companies, personal finance)
- ✅ **Multi-Market Support**: US, India, China, Japan, Korea, Europe with market-specific metrics
- ✅ **Market Auto-Detection**: Automatically detects market from company names and context
- ✅ **FOLLOW_UP Rejection**: Gracefully rejects follow-up queries with guidance to create comprehensive queries
- ✅ **Callback-Based Routing**: Clean routing using `after_agent_callback` for validation/classification

**v2.0 Key Improvements**:
- ✅ All infographics: Square (1:1), 2K resolution, white/light themes
- ✅ Visual contextualization: Every chart/infographic has Setup + Interpretation text
- ✅ Dynamic infographic count: 2-5 infographics based on query complexity
- ✅ Professional narrative structure: Reports read like analyst reports, not placeholder documents

**Key Innovation**: Given a query like "Do a fundamental analysis of Alphabet", the agent will:
1. **Plan** - Identify company and plan which metrics/charts are needed
2. **Fetch** - Gather data from 4 parallel sources (financial, valuation, market, news)
3. **Consolidate** - Merge all data into structured format
4. **Visualize** - Generate multiple charts (5-10) using a LoopAgent
5. **Infographics** - Generate 2-5 AI-powered infographics using Gemini 3 Pro Image (v2.0: dynamic count)
6. **Analyze** - Write professional narrative with **visual contextualization** (v2.0: Setup→Visual→Interpretation)
7. **Report** - Create a professional HTML report with contextualized visuals (v2.0: no standalone placeholders)

---

## What's New in 004 vs 002

| Aspect | code_execution_02 | code_execution_04 |
|--------|-------------------|-------------------|
| Charts | 1 chart per query | **Multiple charts (5-10)** |
| Data Gathering | Sequential (1 agent) | **Parallel (4 concurrent agents)** |
| Chart Generation | Single execution | **LoopAgent iterates through metrics** |
| **Infographics** | None | **2-5 AI-generated infographics (v2.0: dynamic, parallel)** |
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

## Boundary Validation (v2.1)

The agent rejects queries that fall outside its scope with helpful guidance:

| Category | Example Keywords | Rejection Reason |
|----------|-----------------|------------------|
| **Crypto/NFT** | bitcoin, ethereum, nft, defi | Cryptocurrency analysis not supported |
| **Trading Advice** | should i buy, sell now, entry point | Buy/sell recommendations not provided |
| **Private Companies** | startup valuation, pre-ipo, unlisted | Requires public financials |
| **Personal Finance** | my portfolio, retirement planning | Consult a financial advisor |
| **Non-Financial** | weather, recipe, travel | Only equity research supported |
| **Penny Stocks** | otc market, pink sheets | Limited data availability |

Configuration: `app/rules/boundaries_config.py` (templatized - easy to add/modify/delete rules)

---

## Supported Markets (v2.1)

| Market | Exchanges | Currency | Market-Specific Metrics |
|--------|-----------|----------|------------------------|
| **US** | NYSE, NASDAQ, AMEX | USD ($) | Standard metrics |
| **India** | NSE, BSE | INR (₹) | Promoter Holding %, FII/DII Flows |
| **China** | SSE, SZSE, HKEX | CNY (¥) | State Ownership %, A/H-Share Premium |
| **Japan** | TSE, OSE | JPY (¥) | Keiretsu Affiliation, Cross-Shareholding |
| **Korea** | KRX, KOSDAQ | KRW (₩) | Chaebol Affiliation, Foreign Ownership Limit |
| **Europe** | LSE, Euronext, XETRA | EUR (€) | ESG Compliance, EU Taxonomy Alignment |

**Market Auto-Detection**: The agent automatically detects markets from company names (e.g., "Reliance" → India, "Toyota" → Japan).

Configuration: `app/rules/markets_config.py` (templatized - easy to add new markets)

---

## Architecture

```text
User Query: "Do a fundamental analysis of Alphabet"
                          |
+===========================================================+
|      root_agent (SequentialAgent with Routing)           |
+===========================================================+
|                                                           |
|  0. QUERY VALIDATOR (v2.1)                                |
|     - Checks boundary rules (crypto, trading advice, etc) |
|     - after_agent_callback: check_validation_callback     |
|     - If invalid → respond with rejection + capabilities  |
|     - output_key: "query_validation"                      |
|                                                           |
|  1. QUERY CLASSIFIER (v2.1)                               |
|     - Classifies as NEW_QUERY or FOLLOW_UP                |
|     - Detects market (US, India, China, Japan, Korea, EU) |
|     - after_agent_callback: check_classification_callback |
|     - If FOLLOW_UP → respond with guidance to create new  |
|     - output_key: "query_classification"                  |
|                                                           |
+===========================================================+
                          | (only if valid NEW_QUERY)
+----------------------------------------------------------+
|      equity_research_pipeline (SequentialAgent)          |
|      before_agent_callback: skip_if_rejected_callback    |
+----------------------------------------------------------+
|                                                          |
|  2. RESEARCH PLANNER AGENT                               |
|     - Analyzes query, identifies company                 |
|     - Plans which metrics/charts are needed (5-8)        |
|     - output_schema: ResearchPlan                        |
|     - output_key: "research_plan"                        |
|                                                          |
|  3. PARALLEL DATA GATHERERS (ParallelAgent)              |
|     - Run 4 data fetchers concurrently:                  |
|     +-----------------------------------------------+    |
|     | financial_data_fetcher → "financial_data"     |    |
|     | valuation_data_fetcher → "valuation_data"     |    |
|     | market_data_fetcher → "market_data"           |    |
|     | news_sentiment_fetcher → "news_data"          |    |
|     +-----------------------------------------------+    |
|                                                          |
|  4. DATA CONSOLIDATOR AGENT                              |
|     - Merges all 4 fetcher outputs                       |
|     - Extracts structured metrics for charting           |
|     - output_schema: ConsolidatedResearchData            |
|     - output_key: "consolidated_data"                    |
|                                                          |
|  5. CHART GENERATION LOOP (LoopAgent)                    |
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
|  6. INFOGRAPHIC PLANNER AGENT                            |
|     - Plans 2-5 AI-generated infographics                |
|     - Generates detailed prompts for each                |
|     - output_schema: InfographicPlan                     |
|     - output_key: "infographic_plan"                     |
|                                                          |
|  7. PARALLEL INFOGRAPHIC GENERATORS (ParallelAgent)      |
|     - Run generators concurrently:                       |
|     +-----------------------------------------------+    |
|     | infographic_generator_1 → Business Model      |    |
|     | infographic_generator_2 → Competitive Landscape|   |
|     | infographic_generator_3 → Growth Drivers      |    |
|     +-----------------------------------------------+    |
|     - Uses generate_infographic tool with Gemini 3 Pro  |
|     - Saves to "infographics_generated" state           |
|                                                          |
|  8. ANALYSIS WRITER AGENT                                |
|     - Writes 7 narrative analysis sections               |
|     - output_schema: AnalysisSections                    |
|     - output_key: "analysis_sections"                    |
|                                                          |
|  9. HTML REPORT GENERATOR AGENT                          |
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

### Visual Contextualization (v2.0 NEW)

```python
class VisualContext(BaseModel):
    """Setup → Visual → Interpretation pattern for professional reports."""
    visual_id: str          # "chart_1", "infographic_2", etc.
    visual_type: Literal["chart", "infographic", "table"]
    setup_text: str         # 1-2 sentences BEFORE visual
    interpretation_text: str # 1-2 sentences AFTER visual

### Infographic Planning (NEW)

```python
class InfographicSpec(BaseModel):
    """Specification for an infographic."""
    infographic_id: int     # 1, 2, 3, 4, or 5
    title: str              # e.g., "Business Model Overview"
    infographic_type: Literal["business_model", "competitive_landscape", "growth_drivers", "market_position", "risk_landscape"]
    key_elements: list[str] # Data points to visualize
    visual_style: str       # Style description
    prompt: str             # Detailed image generation prompt (v2.0: white theme enforced)

class InfographicPlan(BaseModel):
    """Plan for all infographics."""
    company_name: str
    infographics: list[InfographicSpec]  # v2.0: 2-5 infographics (dynamic)

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
            image_config=genai_types.ImageConfig(
                aspect_ratio="1:1",     # Square format for professional reports
                image_size="2K"          # High quality (1K, 2K, or 4K)
            ),
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

### Simple (2-3 infographics)
- "Analyze Apple stock"
- "Do a fundamental analysis of Microsoft"

### Medium-High Complexity (3-4 infographics)

**Financial Services Deep Dive:**
```
Equity research on JPMorgan Chase analyzing net interest margin trends, investment banking pipeline, wealth management growth, credit quality metrics, and regulatory capital requirements.
```

**Healthcare Innovation:**
```
Fundamental analysis of Eli Lilly focusing on GLP-1 obesity drug pipeline, Alzheimer's treatment commercialization, patent cliff risks, and competitive positioning against Novo Nordisk.
```

**Cloud Infrastructure:**
```
Analyze Alphabet with focus on Google Cloud profitability inflection, YouTube monetization, Search advertising resilience, AI integration across products (Gemini, Bard), and regulatory headwinds.
```

**Payment Processing:**
```
Research Visa covering payment volume trends, cross-border transaction growth, competitive threats from fintech, blockchain/crypto positioning, and operating leverage potential.
```

**Industrial Automation:**
```
Analyze Rockwell Automation evaluating smart manufacturing adoption, software subscription transition, supply chain normalization, and competitive dynamics with Siemens and Schneider Electric.
```

### High Complexity (4-5 infographics)

**Multi-Segment Analysis:**
```
Do a comprehensive equity research on Amazon covering AWS cloud growth, e-commerce profitability, and advertising revenue streams. Include competitive positioning against Microsoft Azure and Google Cloud.
```

**Tech Transformation Analysis:**
```
Full fundamental analysis of Microsoft including Azure cloud dominance, AI Copilot monetization strategy, gaming division performance, and LinkedIn integration. Assess the impact of OpenAI partnership on future growth.
```

**Sector Leadership Assessment:**
```
Analyze NVIDIA's position in the AI chip market with deep dive into data center revenue, gaming GPU trends, automotive AI partnerships, and competitive threats from AMD and custom AI chips from Google/Amazon.
```

**Turnaround Story Analysis:**
```
Comprehensive research on Intel covering manufacturing roadmap (Intel 4, Intel 3, 18A nodes), competitive position against TSMC and Samsung, foundry business strategy, and PC/server market share trends.
```

**Disruption & Innovation:**
```
Analyze Tesla covering automotive production scaling, Full Self-Driving technology progress, energy storage business growth, competitive landscape against traditional OEMs and EV startups, and margin sustainability.
```

### Maximum Complexity (5 infographics - stress tests)

**Conglomerate Breakdown:**
```
Comprehensive analysis of Berkshire Hathaway covering insurance float utilization, equity portfolio performance, operating businesses valuation (BNSF, utilities, manufacturing), succession planning, and intrinsic value calculation.
```

**Platform Economics:**
```
Full research on Meta Platforms analyzing user engagement trends across Facebook/Instagram/WhatsApp, Reels monetization, Reality Labs investment thesis, AI-driven ad targeting improvements, and regulatory challenges.
```

**Subscription Model Transition:**
```
Analyze Adobe's business model evolution from perpetual licenses to Creative Cloud subscriptions, Firefly AI integration, Figma acquisition impact, enterprise adoption trends, and competitive moats.
```

**Emerging Market Leader:**
```
Equity research on Taiwan Semiconductor (TSMC) covering advanced node leadership (3nm, 2nm roadmap), customer concentration risk (Apple, NVIDIA), geopolitical risks, capex intensity, and margin sustainability.
```

**Cyclical Recovery Play:**
```
Analyze Caterpillar assessing construction equipment demand recovery, mining equipment super-cycle thesis, dealer inventory levels, services revenue growth, and emerging markets exposure.
```

### Recommended Testing Sequence
1. **Start with**: NVIDIA (high complexity) - validates multi-segment analysis
2. **Then test**: Alphabet (medium-high) - validates cloud/advertising coverage
3. **Stress test**: Meta Platforms (maximum) - validates platform economics handling

**What Each Test Validates:**
- ✅ Dynamic infographic count (2-5 based on query complexity)
- ✅ Sector-agnostic research (tech, finance, healthcare, industrials, cyclicals)
- ✅ Setup → Visual → Interpretation pattern for all visuals
- ✅ White/light theme infographics (1:1, 2K)
- ✅ Professional narrative quality (Morgan Stanley/Goldman Sachs standards)

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

### 1. Callback-Based Routing (v2.1)

The agent uses `after_agent_callback` to check validation/classification results and stop the pipeline:

```python
# In app/callbacks/routing.py
async def check_validation_callback(callback_context):
    """Check validation result after query_validator runs."""
    state = callback_context.state
    validation = state.get("query_validation", {})

    if not validation.get("is_valid", True):
        # Return Content to stop pipeline and respond
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text=rejection_message)]
        )
    return None  # Continue to next agent
```

| Pattern | Use Case | How It Works |
|---------|----------|--------------|
| `after_agent_callback` | Routing decisions | Check output, return Content to stop or None to continue |
| `before_agent_callback` | Skip stages | Return Content to skip stage, None to proceed |
| State flags | Cross-agent coordination | Set `skip_pipeline=True` to signal downstream agents |

### 2. Callback-Based Code Execution

Learned from experiment 03's infinite loop issues, we use callbacks to execute chart code:

| Approach | Reliability | Why |
|----------|-------------|-----|
| **Callback (04)** | 100% | LLM generates code, callback executes ONCE |
| Native code_executor (03) | ~70% | LLM sees results, tries to "improve" |

### 3. ParallelAgent for Data Fetching + Infographics

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

### 4. Tool-Based Image Generation

Instead of code execution, infographics use a FunctionTool that wraps Gemini 3 Pro Image:

```python
generate_infographic_tool = FunctionTool(generate_infographic)

# Used by infographic generators
infographic_generator_1 = LlmAgent(
    tools=[generate_infographic_tool],
    ...
)
```

### 5. Placeholder-Based Image Injection

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

**Last Updated**: 2026-01-06 (v2.1)
**Experiment Status**: WORKING - PROFESSIONAL GRADE WITH HITL
**Base Experiment**: code_execution_02 (SUCCESS - RECOMMENDED)
**Key ADK Features**: ParallelAgent, LoopAgent, Custom BaseAgent, FunctionTool, Callback-Based Routing
**Expected Charts**: 5-10 per report (all contextualized with Setup→Visual→Interpretation)
**Expected Infographics**: 2-5 per report (dynamic, 1:1, 2K, white theme)
**Report Quality**: Morgan Stanley / Goldman Sachs standards
**Supported Markets**: US, India, China, Japan, Korea, Europe (auto-detected)

**Documentation**:

- v2.1 Implementation Plan: `.docs/new_flow/IMPLEMENTATION_PLAN_v2.md`
- v2.0 Implementation Summary: `.docs/IMPLEMENTATION_SUMMARY.md`
- v2.0 Overhaul Plan: `.docs/OVERHAUL_PLAN.md`
