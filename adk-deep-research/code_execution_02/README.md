# Experiment 002: Financial Data Visualization with HTML Report

## Status: IN DEVELOPMENT

Extends `code_execution_01` with an HTML report generation layer. The final output is a downloadable, self-contained HTML report with embedded chart, data tables, and key insights.

---

## What's New in 002

| Feature | code_execution_01 | code_execution_02 |
|---------|-------------------|-------------------|
| Output | Chart artifact + text summary | **HTML report artifact** |
| Chart | Separate PNG file | **Embedded as base64** |
| Download | Chart image only | **Complete HTML report** |
| Agents | 4-stage pipeline | **5-stage pipeline** |

### Key Addition: HTML Report Generator

A new 5th agent (`html_report_generator`) uses Gemini 3 Pro to generate a professional HTML report containing:
- Executive summary
- Key metrics cards
- Embedded chart visualization (base64)
- Data table with all values
- Key findings section
- Footer with data source

---

## Quick Start

### Prerequisites

- Python 3.10+
- Google Cloud Project with Vertex AI enabled
- `gcloud` CLI authenticated
- Sandbox already created (reuse from code_execution_01)

### Setup

```bash
# 1. Navigate to the experiment folder
cd adk-deep-research/code_execution_02

# 2. Install dependencies (same as 01)
pip install -r requirements.txt

# 3. Ensure .env file exists in adk-deep-research/ folder
# (reuse the same sandbox from code_execution_01)

# 4. Run the agent
cd ..  # Go back to adk-deep-research folder
adk api_server code_execution_02
# Or for web UI: adk web code_execution_02
```

### Environment Variables

Same as `code_execution_01` - reuse the existing `.env` file:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global  # Required for Gemini 3 Pro Preview
GOOGLE_GENAI_USE_VERTEXAI=1

# Agent Engine Configuration
AGENT_ENGINE_RESOURCE_NAME=projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID

# Pre-created Sandbox for Code Execution
SANDBOX_RESOURCE_NAME=projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID/sandboxEnvironments/YOUR_SANDBOX_ID
```

---

## Architecture

```
User Query: "Show me Google's revenue for the last 5 years"
                          |
+-------------------------------------------------------------------------+
|              financial_report_pipeline (SequentialAgent)                 |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  | 1. DATA FETCHER AGENT                                             |  |
|  |    - Tools: [google_search]                                       |  |
|  |    - Searches for financial data via Google Search                |  |
|  |    - output_key: "raw_financial_data"                             |  |
|  +-------------------------------------------------------------------+  |
|                          |                                              |
|  +-------------------------------------------------------------------+  |
|  | 2. DATA EXTRACTOR AGENT                                           |  |
|  |    - Reads: {raw_financial_data}                                  |  |
|  |    - Extracts structured data points                              |  |
|  |    - output_schema: FinancialDataExtraction (Pydantic)            |  |
|  |    - output_key: "structured_data"                                |  |
|  +-------------------------------------------------------------------+  |
|                          |                                              |
|  +-------------------------------------------------------------------+  |
|  | 3. CODE GENERATOR + CALLBACK                                      |  |
|  |    - Reads: {structured_data}                                     |  |
|  |    - Generates Python matplotlib code                             |  |
|  |    - output_key: "chart_code"                                     |  |
|  |    - after_agent_callback: execute_chart_code_callback            |  |
|  |      -> Executes code ONCE via Vertex AI sandbox                  |  |
|  |      -> Saves chart as ADK artifact                               |  |
|  |      -> Stores chart_base64 and chart_mime_type in state (NEW!)   |  |
|  +-------------------------------------------------------------------+  |
|                          |                                              |
|  +-------------------------------------------------------------------+  |
|  | 4. SUMMARY AGENT                                                  |  |
|  |    - Reads all previous outputs                                   |  |
|  |    - Generates text summary with key insights                     |  |
|  |    - output_key: "final_summary"                                  |  |
|  +-------------------------------------------------------------------+  |
|                          |                                              |
|  +-------------------------------------------------------------------+  |
|  | 5. HTML REPORT GENERATOR + CALLBACK (NEW!)                        |  |
|  |    - Reads: {structured_data}, {chart_base64}, {final_summary}    |  |
|  |    - Uses HTML template to generate report                        |  |
|  |    - output_key: "html_report"                                    |  |
|  |    - after_agent_callback: save_html_report_callback              |  |
|  |      -> Saves HTML as downloadable artifact                       |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
+-------------------------------------------------------------------------+
                          |
        Final Output: HTML Report Artifact (financial_report.html)
                      + Chart Artifact (financial_chart.png)
```

---

## State Flow

```
Agent 1 (data_fetcher):
  -> raw_financial_data

Agent 2 (data_extractor):
  <- raw_financial_data
  -> structured_data

Agent 3 (code_generator) + callback:
  <- structured_data
  -> chart_code
  -> execution_result (from callback)
  -> chart_base64 (from callback) <-- NEW
  -> chart_mime_type (from callback) <-- NEW
  -> Artifact: financial_chart.png

Agent 4 (summary):
  <- raw_financial_data, structured_data, chart_code, execution_result
  -> final_summary

Agent 5 (html_report_generator) + callback: <-- NEW
  <- structured_data, chart_base64, chart_mime_type, final_summary
  -> html_report
  -> report_result (from callback)
  -> Artifact: financial_report.html
```

---

## Key Design Decisions

### 1. LLM for HTML Generation (Not Sandbox)

We use Gemini 3 Pro directly to generate HTML instead of running Python in the sandbox:

| Approach | Pros | Cons |
|----------|------|------|
| **LLM generates HTML** | Simple, no sandbox overhead, LLMs excel at text generation | Need to pass chart as base64 |
| Sandbox (Python + Jinja2) | Programmatic templating | Complex, extra sandbox call, overkill for text |

**Decision**: Use LLM because HTML is text generation - exactly what LLMs are good at.

### 2. Base64 Chart Embedding

The chart is embedded directly in the HTML as a base64 data URI:

```html
<img src="data:image/png;base64,iVBORw0KGgoAAAANS..." alt="Chart">
```

This creates a **self-contained HTML file** that:
- Works offline
- No external dependencies
- Easy to share and archive
- Displays in any browser

### 3. Professional HTML Template

The template includes:
- Modern CSS with gradients and shadows
- Responsive grid layout for metrics
- Styled data tables
- Colored key findings cards
- Professional footer

---

## HTML Report Sections

| Section | Description | Source |
|---------|-------------|--------|
| Header | Title, entity, metric, date | structured_data |
| Executive Summary | Narrative analysis | final_summary |
| Key Metrics | Cards with highest, lowest, average, growth | structured_data |
| Chart | Embedded visualization | chart_base64 |
| Data Table | Period, value, unit rows | structured_data.data_points |
| Key Findings | Bullet list of insights | final_summary |
| Footer | Data source attribution | structured_data.data_source |

---

## Example Output

For query: "Show me Google's revenue for the last 5 years"

**Generated Artifacts:**

1. `financial_chart.png` - Matplotlib line chart
2. `financial_report.html` - Complete HTML report with:
   - Title: "Google Annual Revenue Analysis 2020-2024"
   - Metric cards: Highest ($350.02B), Lowest ($182.53B), Growth (91.8%)
   - Embedded chart visualization
   - Data table with 5 rows
   - Key findings about revenue growth trend

---

## Files

| File | Description |
|------|-------------|
| `agent.py` | 5-stage pipeline with HTML generation |
| `config.py` | Configuration (same as 01) |
| `manage_sandbox.py` | Sandbox CLI tool (same as 01) |
| `requirements.txt` | Python dependencies (same as 01) |
| `__init__.py` | Package init |

---

## Model Configuration

Same as `code_execution_01`:

| Setting | Value |
|---------|-------|
| Model ID | `gemini-3-pro-preview` |
| Location | `global` (required for Gemini 3) |
| Context Window | 1M tokens |

---

## Differences from code_execution_01

### Modified Files

1. **agent.py**:
   - Added `import base64`
   - Updated docstring for 5-stage pipeline
   - Modified `execute_chart_code_callback` to store `chart_base64` and `chart_mime_type` in state
   - Added `save_html_report_callback` function
   - Added `HTML_TEMPLATE` constant
   - Added `html_report_generator` LlmAgent
   - Renamed pipeline to `financial_report_pipeline`
   - Added 5th agent to sub_agents list

### Unchanged Files

- `config.py` - same configuration
- `manage_sandbox.py` - same sandbox management
- `requirements.txt` - same dependencies
- `__init__.py` - same package init

---

## Known Considerations

1. **Large Base64 Strings**: Chart images are ~50-100KB as base64, which increases context size for the HTML generator. Gemini 3 Pro's 1M context handles this easily.

2. **HTML Validation**: The LLM may occasionally wrap output in markdown code blocks. The callback handles this by extracting content from code blocks.

3. **Template Following**: The LLM is instructed to follow the template structure but may make minor variations. The template provides consistent styling.

---

## Testing Plan

1. Start the server:
   ```bash
   cd adk-deep-research
   adk api_server code_execution_02
   ```

2. Test query: "Show me Google's revenue for the last 5 years"

3. Verify:
   - [ ] Chart artifact saved (financial_chart.png)
   - [ ] HTML artifact saved (financial_report.html)
   - [ ] HTML contains embedded chart (base64 image displays)
   - [ ] HTML is downloadable from UI
   - [ ] HTML renders correctly in browser
   - [ ] All sections populated (summary, metrics, table, findings)

---

## Potential Enhancements

1. **Multiple Chart Types**: Support pie charts, stacked bars for segment analysis
2. **Interactive Charts**: Use Chart.js or Plotly for interactive HTML charts
3. **PDF Export**: Add PDF generation alongside HTML
4. **Custom Branding**: Allow custom colors, logos, company branding
5. **Multi-Entity Reports**: Compare multiple companies in one report
6. **Historical Comparisons**: Show year-over-year comparisons with delta indicators

---

## Sources

- [ADK Code Execution Documentation](https://google.github.io/adk-docs/tools/google-cloud/code-exec-agent-engine/)
- [code_execution_01](../code_execution_01/) - Base experiment this extends
- [Gemini 3 Pro Preview](https://ai.google.dev/gemini-api/docs/gemini-3)

---

**Last Updated**: 2025-12-26
**Experiment Status**: IN DEVELOPMENT
**Base Experiment**: code_execution_01 (SUCCESS)
