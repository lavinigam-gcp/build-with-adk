# Experiment 001: Financial Data Visualization Agent

## Status: SUCCESS

A multi-stage agent pipeline that fetches real-time financial data via Google Search, extracts structured data, and generates professional visualizations using matplotlib. Charts are saved as ADK artifacts and displayed in the UI.

![Example Output](./assets/pe_ratio_chart.png)
*Example: Quarterly P/E Ratios for Top 5 S&P 500 Stocks (Q4 2020 - Q4 2025)*

---

## Quick Start

### Prerequisites

- Python 3.10+
- Google Cloud Project with Vertex AI enabled
- `gcloud` CLI authenticated

### Setup

```bash
# 1. Navigate to the experiment folder
cd adk-deep-research/code_execution_01

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create sandbox for code execution
GOOGLE_CLOUD_PROJECT=your-project-id python manage_sandbox.py create --name "financial_viz_sandbox"

# 4. Create .env file in adk-deep-research/ folder with output from step 3
# (see Environment Variables section below)

# 5. Run the agent
cd ..  # Go back to adk-deep-research folder
adk api_server code_execution_01
# Or for web UI: adk web code_execution_01
```

### Environment Variables

Create a `.env` file in the `adk-deep-research/` folder:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global  # Required for Gemini 3 Pro Preview
GOOGLE_GENAI_USE_VERTEXAI=1

# Agent Engine Configuration (from manage_sandbox.py create output)
AGENT_ENGINE_RESOURCE_NAME=projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID

# Pre-created Sandbox for Code Execution (REQUIRED)
SANDBOX_RESOURCE_NAME=projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID/sandboxEnvironments/YOUR_SANDBOX_ID
```

---

## Example Queries

### Simple Queries (Single Entity, Basic Metrics)

| Query | Chart Type | Description |
|-------|------------|-------------|
| "Show me Google's revenue for the last 5 years" | Line | Annual revenue trend |
| "Apple's stock price for 2024" | Line | Single year stock data |
| "Microsoft revenue last 3 years" | Line | Short time range |
| "Tesla quarterly earnings 2024" | Bar | Quarterly earnings breakdown |
| "Amazon net income 2022 to 2024" | Line | Net income metric |

### Medium Complexity

| Query | Chart Type | Description |
|-------|------------|-------------|
| "Compare Google and Microsoft revenue for the last 5 years" | Multi-line | Company comparison |
| "NVIDIA stock price growth from 2020 to 2024" | Line/Area | Growth visualization |
| "S&P 500 annual performance over the last decade" | Line/Area | Index, long time range |
| "Meta advertising revenue quarterly for 2023 and 2024" | Bar | Specific segment, 8 quarters |

### Complex Queries

| Query | Chart Type | Description |
|-------|------------|-------------|
| "Help me do PE analysis of quarter by quarter in last 5 years for top 5 stocks of S&P" | Multi-line | Multiple companies, derived metric (P/E ratio) |
| "Compare cloud revenue for Amazon AWS, Microsoft Azure, and Google Cloud for 2021-2024" | Multi-line | 3 companies, specific business segment |
| "Apple's revenue breakdown by product category (iPhone, Mac, iPad, Services) for 2024" | Stacked bar | Category breakdown |
| "Analyze correlation between oil prices and Exxon stock price over 5 years" | Dual-axis | Two different metrics |

### Edge Cases

| Query | What It Tests |
|-------|---------------|
| "Bitcoin price last month" | Non-stock asset, short timeframe |
| "Compare GDP of US, China, and India 2015-2024" | Non-company macroeconomic data |
| "Gold price vs S&P 500 over 10 years" | Commodity vs index comparison |

### Query Tips

- Be specific about time periods (e.g., "last 5 years", "Q1-Q4 2024")
- Mention specific companies or indices by name
- Specify the metric you want (revenue, P/E ratio, stock price, earnings, net income)
- For comparisons, explicitly list the companies you want to compare

---

## Architecture

```
User Query: "Show me Google's revenue for the last 5 years"
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│              financial_data_pipeline (SequentialAgent)          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. DATA FETCHER AGENT                                     │  │
│  │    - Tools: [google_search]                               │  │
│  │    - Searches for financial data via Google Search        │  │
│  │    - output_key: "raw_financial_data"                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 2. DATA EXTRACTOR AGENT                                   │  │
│  │    - Reads: {raw_financial_data}                          │  │
│  │    - Extracts structured data points                      │  │
│  │    - output_schema: FinancialDataExtraction (Pydantic)    │  │
│  │    - output_key: "structured_data"                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 3. CODE GENERATOR AGENT + EXECUTION CALLBACK              │  │
│  │    - Reads: {structured_data}                             │  │
│  │    - Generates Python matplotlib code                     │  │
│  │    - output_key: "chart_code"                             │  │
│  │    - after_agent_callback: execute_chart_code_callback    │  │
│  │      → Executes code ONCE via Vertex AI client            │  │
│  │      → Saves chart as ADK artifact                        │  │
│  │      → Stores result in: "execution_result"               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 4. SUMMARY AGENT                                          │  │
│  │    - Reads all previous outputs                           │  │
│  │    - Generates final summary with key insights            │  │
│  │    - References the generated chart artifact              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                          ↓
        Final Output: Summary + Chart Artifact (displayed in UI)
```

### Key Design Decisions

#### 1. Callback-Based Code Execution (Critical!)

Code execution happens in a **callback** (not an LLM agent) to guarantee exactly ONE execution. Using an LLM for code execution causes infinite loops:

1. LLM outputs code block → executor runs it → result returned to LLM
2. LLM sees result → outputs ANOTHER code block → executor runs it
3. Repeat indefinitely (we observed 11+ executions before this fix!)

**The Solution:**
- **Code Generator Agent**: Generates Python code, stores in `chart_code` state key
- **after_agent_callback**: Uses Vertex AI client directly to execute code ONCE
- **No LLM in the execution loop** = guaranteed single execution

#### 2. ADK Artifact System for Chart Display

Charts are saved as ADK artifacts so they display in the UI:

```python
# In the callback:
image_artifact = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
await callback_context.save_artifact(filename="financial_chart.png", artifact=image_artifact)
```

#### 3. Filtering Auto-Captured Images

The sandbox auto-captures matplotlib figures as `code_execution_image_*` files. We filter these out to only save our explicitly named chart:

```python
is_our_chart = (
    file_name.endswith((".png", ".jpg", ".jpeg")) and
    not file_name.startswith("code_execution_image_")
)
```

---

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main agent pipeline with 4 sub-agents + execution callback |
| `config.py` | Configuration (model, chart settings) |
| `manage_sandbox.py` | CLI tool for sandbox lifecycle management |
| `requirements.txt` | Python dependencies |
| `__init__.py` | Package init |

---

## Model Configuration

This agent uses **Gemini 3 Pro Preview** (`gemini-3-pro-preview`), Google's latest reasoning-first model optimized for complex agentic workflows.

| Setting | Value |
|---------|-------|
| Model ID | `gemini-3-pro-preview` |
| Location | `global` (required for Gemini 3) |
| Context Window | 1M tokens |

**Note**: The sandbox (Agent Engine) remains in `us-central1`, but the model API calls use `global` location.

---

## Sandbox Management

### Why Pre-create a Sandbox?

The first code execution is slow (~10-15s) because a sandbox must be created. Pre-creating the sandbox eliminates this delay for the first query.

### Commands

```bash
# Create a new sandbox (outputs AGENT_ENGINE_RESOURCE_NAME and SANDBOX_RESOURCE_NAME)
GOOGLE_CLOUD_PROJECT=your-project python manage_sandbox.py create --name "financial_viz_sandbox"

# List all sandboxes
AGENT_ENGINE_RESOURCE_NAME=projects/... python manage_sandbox.py list

# Test a sandbox (verifies libraries are available)
GOOGLE_CLOUD_PROJECT=your-project python manage_sandbox.py test --sandbox-id "projects/.../sandboxEnvironments/..."

# Delete a sandbox
GOOGLE_CLOUD_PROJECT=your-project python manage_sandbox.py delete --sandbox-id "projects/.../sandboxEnvironments/..."
```

### Sandbox Configuration Options

| Option | Values | Description |
|--------|--------|-------------|
| `--name` | Any string | Display name for the sandbox |
| `--language` | LANGUAGE_PYTHON, LANGUAGE_JAVASCRIPT | Runtime language |
| `--machine` | MACHINE_CONFIG_VCPU4_RAM4GIB | Compute resources |

---

## Code Execution Details

### Available Libraries in Sandbox

Verified available (as of 2025-12-26):

| Library | Version | Import |
|---------|---------|--------|
| Python | 3.12.11 | - |
| matplotlib | 3.9.1 | `import matplotlib.pyplot as plt` |
| numpy | 2.3.2 | `import numpy as np` |
| pandas | 2.2.3 | `import pandas as pd` |
| seaborn | 0.12.2 | `import seaborn as sns` |
| scipy | available | `import scipy` |

**Note**: seaborn IS available (contrary to earlier documentation), but we use matplotlib for consistency.

### Chart Generation Guidelines

The code generator agent is instructed to:
1. Always import libraries explicitly at the top
2. Use `plt.style.use('ggplot')` for professional styling
3. Create figure with `figsize=(12, 6)`
4. Save charts as `financial_chart.png` with `dpi=150`
5. Call `plt.close()` after saving
6. Print "Chart saved successfully" for confirmation

---

## Key Learnings

### What Works Well

1. **SequentialAgent Pipeline**: Clean separation of concerns, easy to debug each stage
2. **Structured Outputs (Pydantic)**: `FinancialDataExtraction` schema ensures consistent data between agents
3. **State Management**: `output_key` makes data flow between agents seamless and debuggable
4. **Callback-Based Execution**: Guarantees single code execution, prevents infinite loops
5. **ADK Artifacts**: Charts display directly in the UI without file system management

### Known Limitations

1. **Data Accuracy**: Google Search returns narrative text; extraction accuracy depends on search results quality
2. **Rate Limits**: Heavy usage may hit Google Search API limits
3. **Complex Charts**: Multi-company comparisons with many data points may produce cluttered visualizations
4. **Sandbox Cold Start**: First query after sandbox creation takes ~10-15s

### Issues Encountered & Fixes

| Issue | Root Cause | Fix |
|-------|------------|-----|
| `NameError: name 'sns' is not defined` | Initial assumption seaborn unavailable | Updated instructions to import explicitly (seaborn IS available) |
| Slow first execution | Sandbox created on-demand | Created `manage_sandbox.py` for pre-creating sandboxes |
| **Infinite loop (11+ executions)** | LLM with code_executor keeps generating code after seeing results | Moved to `after_agent_callback` - no LLM in execution loop |
| Chart not visible in UI | Using raw file system instead of ADK artifacts | Added `callback_context.save_artifact()` |
| **Empty duplicate image in UI** | Sandbox auto-captures matplotlib figures as `code_execution_image_*` | Filter out auto-captured images, only save `financial_chart.png` |

---

## Performance

| Metric | Without Pre-created Sandbox | With Pre-created Sandbox |
|--------|----------------------------|-------------------------|
| First query | ~20-30s | ~10-15s |
| Subsequent queries | ~10-15s | ~10-15s |

---

## Results

### Verified Test Cases

All queries from the Example Queries section have been tested and work correctly:

- **Simple Queries**: Single company revenue/stock charts generate correctly
- **Medium Queries**: Company comparisons with multi-line charts work well
- **Complex Queries**: P/E ratio analysis across 5 companies over 5 years generates readable charts
- **Edge Cases**: Non-stock assets (Bitcoin, Gold) and macroeconomic data (GDP) handled gracefully

### Sample Output

For query: "Show me Google's revenue for the last 5 years"

**Generated Chart**: Line chart showing Alphabet Inc. annual revenue from 2020 ($182.53B) to 2024 ($350.02B)

**Summary Output**: Professional markdown summary with:
- Overview of data analyzed
- Key findings (growth trends, notable changes)
- Data summary (highs, lows, growth rate)
- Chart reference
- Sources and caveats

---

## Recommendation

**Status: SUCCESS - Ready for Production Use**

This experiment successfully demonstrates:
- Combining Google Search grounding with Code Execution in a multi-agent pipeline
- Generating professional financial visualizations from natural language queries
- Saving charts as ADK artifacts for UI display
- Managing sandbox lifecycle for production use
- Solving the infinite loop problem with callback-based execution

### Potential Enhancements

1. **Error Handling**: Add graceful fallbacks for failed searches or code execution
2. **Chart Caching**: Cache generated charts to avoid re-generating for identical queries
3. **Multiple Formats**: Support exporting charts as PNG, SVG, or PDF
4. **Iterative Refinement**: Add optional loop for user to request chart modifications
5. **Data Validation**: Validate extracted data points before generating charts

---

## Sources

- [ADK Code Execution Documentation](https://google.github.io/adk-docs/tools/google-cloud/code-exec-agent-engine/)
- [Google Search Grounding](https://google.github.io/adk-docs/grounding/google_search_grounding/)
- [Multi-Agent Patterns in ADK](https://google.github.io/adk-docs/agents/multi-agents/)
- [ADK Python GitHub](https://github.com/google/adk-python)
- [Code Execution Tutorial (Jupyter)](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/agents/agent_engine/tutorial_get_started_with_code_execution.ipynb)

---

**Last Updated**: 2025-12-26
**Experiment Status**: SUCCESS
**Recommendation**: Ready for production use
