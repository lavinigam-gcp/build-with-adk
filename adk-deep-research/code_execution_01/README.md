# Experiment 001: Financial Data Visualization Agent

## Status: SUCCESS

A multi-stage agent pipeline that fetches real-time financial data via Google Search, extracts structured data, and generates professional visualizations using matplotlib.

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

# 3. Set environment variables
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1

# 4. (Optional but recommended) Pre-create sandbox for faster execution
python manage_sandbox.py create --name "financial_viz_sandbox"

# 5. Set the sandbox resource name from step 4 output
export SANDBOX_RESOURCE_NAME="projects/.../sandboxEnvironments/..."

# 6. Run the agent
cd ..  # Go back to adk-deep-research folder
adk web code_execution_01
```

### Environment Variables

Create a `.env` file in the `adk-deep-research/` folder:

```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=1

# Optional: Pre-created sandbox for faster execution
AGENT_ENGINE_RESOURCE_NAME=projects/.../reasoningEngines/...
SANDBOX_RESOURCE_NAME=projects/.../sandboxEnvironments/...
```

---

## Example Queries

### Tested & Working

| Query | Chart Type | Description |
|-------|------------|-------------|
| "Help me do PE analysis of quarter by quarter in last 5 years for top 5 stocks of S&P" | Multi-line | P/E ratios for AAPL, NVDA, GOOGL, MSFT, AMZN |
| "Show me Google's revenue for the last 5 years" | Line | Annual revenue trend |
| "Compare Apple and Microsoft stock prices over the last year" | Multi-line | Stock price comparison |
| "Tesla's quarterly earnings for 2024" | Bar | Quarterly earnings breakdown |
| "S&P 500 performance over the last decade" | Area | Index performance over time |

### Query Tips

- Be specific about time periods (e.g., "last 5 years", "Q1-Q4 2024")
- Mention specific companies or indices
- Specify the metric you want (revenue, P/E ratio, stock price, earnings)
- For comparisons, list the companies you want to compare

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
│  │    - Searches for financial data                          │  │
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
│  │ 3. VISUALIZATION AGENT                                    │  │
│  │    - Reads: {structured_data}                             │  │
│  │    - code_executor: AgentEngineSandboxCodeExecutor        │  │
│  │    - Generates matplotlib chart                           │  │
│  │    - Saves chart as PNG                                   │  │
│  │    - output_key: "visualization_result"                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          ↓                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 4. SUMMARY AGENT                                          │  │
│  │    - Reads all previous outputs                           │  │
│  │    - Generates final summary with key insights            │  │
│  │    - References the generated chart                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                          ↓
        Final Output: Summary + Chart Image
```

---

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main agent pipeline with 4 sub-agents |
| `config.py` | Configuration (model, chart settings) |
| `manage_sandbox.py` | CLI tool for sandbox lifecycle management |
| `requirements.txt` | Python dependencies |
| `__init__.py` | Package init |

---

## Sandbox Management

### Why Pre-create a Sandbox?

The first code execution is slow (~10-15s) because a sandbox must be created. Pre-creating the sandbox eliminates this delay.

### Commands

```bash
# Create a new sandbox
GOOGLE_CLOUD_PROJECT=your-project python manage_sandbox.py create --name "financial_viz_sandbox"

# List all sandboxes
python manage_sandbox.py list

# Test a sandbox
python manage_sandbox.py test --sandbox-id "projects/.../sandboxEnvironments/..."

# Delete a sandbox
python manage_sandbox.py delete --sandbox-id "projects/.../sandboxEnvironments/..."
```

### Sandbox Configuration Options

| Option | Values | Description |
|--------|--------|-------------|
| `--language` | LANGUAGE_PYTHON, LANGUAGE_JAVASCRIPT | Runtime language |
| `--machine` | MACHINE_CONFIG_VCPU4_RAM4GIB | Compute resources |

---

## Key Learnings

### What Works

1. **SequentialAgent Pipeline**: Clean separation of concerns, easy to debug
2. **Structured Outputs**: Pydantic schemas ensure consistent data between agents
3. **State Management**: `output_key` makes data flow between agents seamless
4. **Pre-created Sandbox**: Significantly improves execution speed

### Known Limitations

1. **Seaborn Not Available**: The sandbox only has matplotlib, numpy, pandas pre-installed
2. **Data Accuracy**: Google Search returns narrative text; extraction may not be 100% accurate
3. **Rate Limits**: Heavy usage may hit Google Search API limits

### Fixes Applied

| Issue | Fix |
|-------|-----|
| `NameError: name 'sns' is not defined` | Updated instructions to use matplotlib only, explicitly import all libraries |
| Slow first execution | Created `manage_sandbox.py` for pre-creating sandboxes |
| Dynamic sandbox selection | Agent now checks `SANDBOX_RESOURCE_NAME` env var |

---

## Code Execution Details

### Available Libraries in Sandbox

- `matplotlib.pyplot` (as plt)
- `numpy` (as np)
- `pandas` (as pd)
- `scipy`

**NOT Available**: seaborn, plotly, bokeh

### Chart Generation Guidelines

The visualization agent is instructed to:
1. Always import libraries explicitly at the top
2. Use `plt.style.use('ggplot')` for professional styling
3. Save charts as `financial_chart.png` with `dpi=150`
4. Never use seaborn

---

## Results

### Successful Test Cases

- **P/E Ratio Analysis**: Generated multi-line chart comparing 5 companies over 5 years
- **Revenue Trends**: Single company line charts with data labels
- **Stock Comparisons**: Multi-company comparisons with legends

### Performance

| Metric | Without Pre-created Sandbox | With Pre-created Sandbox |
|--------|----------------------------|-------------------------|
| First query | ~20-30s | ~10-15s |
| Subsequent queries | ~10-15s | ~10-15s |

---

## Recommendation

**Status: SUCCESS - Ready for Integration**

This experiment successfully demonstrates:
- Combining Google Search with Code Execution in a multi-agent pipeline
- Generating professional financial visualizations from natural language queries
- Managing sandbox lifecycle for production use

### Next Steps

1. Add error handling for failed searches or code execution
2. Implement chart caching to avoid re-generating same charts
3. Add support for exporting charts in multiple formats
4. Consider adding iterative refinement loop for chart quality

---

## Sources

- [ADK Code Execution Documentation](https://google.github.io/adk-docs/tools/google-cloud/code-exec-agent-engine/)
- [Google Search Grounding](https://google.github.io/adk-docs/grounding/google_search_grounding/)
- [Multi-Agent Patterns in ADK](https://google.github.io/adk-docs/agents/multi-agents/)
- [ADK Python GitHub](https://github.com/google/adk-python)
- [Code Execution Tutorial](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/agents/agent_engine/tutorial_get_started_with_code_execution.ipynb)

---

**Last Updated**: 2025-12-21
**Experiment Status**: SUCCESS
**Recommendation**: Ready for production use
