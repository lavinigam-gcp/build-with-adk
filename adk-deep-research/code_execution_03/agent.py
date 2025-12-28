# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Financial Data Visualization Agent with Native Code Execution
==============================================================

A multi-stage agent pipeline that:
1. Fetches real-time financial data via Google Search
2. Extracts structured data points from search results (Pydantic)
3. Creates charts using NATIVE code_executor (agent has sandbox access)
4. Creates a text summary of the analysis
5. Generates a professional HTML report with embedded chart

Architecture: SequentialAgent with 5 sub-agents

KEY DIFFERENCE from code_execution_01/02:
- Stage 3 uses AgentEngineSandboxCodeExecutor directly on the LlmAgent
- Agent executes code iteratively within the sandbox
- Explicit STOP condition in instruction prevents infinite loops
- After-agent callback extracts the saved chart (not the execution itself)

This is an EXPERIMENT to test if native code_executor with proper instruction
design can prevent the infinite loop problem observed in earlier experiments.

Final Output: Downloadable HTML report artifact
"""

import base64
import datetime
import json
import os
import re
from typing import Literal

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.tools import google_search
from pydantic import BaseModel, Field


# --- Configuration ---
MODEL = "gemini-3-pro-preview"
CURRENT_DATE = datetime.datetime.now().strftime("%Y-%m-%d")


async def cleanup_sandbox_before_chart_creation(callback_context):
    """Clean up any existing chart file BEFORE the agent creates a new one.

    This callback runs BEFORE the chart_creator agent starts.
    It deletes any existing 'financial_chart.png' from previous sessions,
    ensuring we never extract a stale chart if the agent's code execution fails.

    This is critical because ADK sandbox is stateful - files persist between sessions.
    """
    import vertexai

    sandbox_name = os.environ.get("SANDBOX_RESOURCE_NAME")
    if not sandbox_name:
        print("Warning: SANDBOX_RESOURCE_NAME not set, skipping cleanup")
        return

    try:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        sandbox_location = "us-central1"

        vertexai.init(project=project_id, location=sandbox_location)
        client = vertexai.Client(project=project_id, location=sandbox_location)

        # Delete any existing chart file to ensure fresh start
        cleanup_code = '''
import os
if os.path.exists('financial_chart.png'):
    os.remove('financial_chart.png')
    print("PRE_CLEANUP:Removed existing chart file")
else:
    print("PRE_CLEANUP:No existing chart file found")
'''
        response = client.agent_engines.sandboxes.execute_code(
            name=sandbox_name,
            input_data={"code": cleanup_code}
        )
        print("Pre-chart cleanup: Ensured sandbox is clean for new chart")

    except Exception as e:
        # Non-fatal - log but don't block the agent
        print(f"Warning: Pre-chart cleanup failed: {e}")


async def extract_chart_artifact_callback(callback_context):
    """Extract the chart from sandbox and save as artifact.

    This callback runs AFTER the chart_creator agent completes.
    The agent has already executed code to save 'financial_chart.png' in the sandbox.
    We need to retrieve this file and save it as an ADK artifact.

    Key difference from code_execution_01/02:
    - In 01/02: Callback executes code AND extracts artifacts
    - In 03: Agent executes code, callback ONLY extracts artifacts
    """
    import vertexai
    from google.genai import types

    state = callback_context.state

    # Get sandbox configuration
    sandbox_name = os.environ.get("SANDBOX_RESOURCE_NAME")
    if not sandbox_name:
        state["execution_result"] = "Error: SANDBOX_RESOURCE_NAME not set"
        return

    try:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        # For sandbox operations, use us-central1 (not global)
        sandbox_location = "us-central1"

        vertexai.init(project=project_id, location=sandbox_location)
        client = vertexai.Client(project=project_id, location=sandbox_location)

        # Execute code to read the saved chart file from the sandbox
        read_code = '''
import base64
import os

# Check if the chart file exists
if os.path.exists('financial_chart.png'):
    with open('financial_chart.png', 'rb') as f:
        chart_bytes = f.read()
        chart_base64 = base64.b64encode(chart_bytes).decode('utf-8')
    print(f"CHART_DATA:{chart_base64}")
else:
    print("ERROR:Chart file not found in sandbox")
'''
        print("Extracting chart from sandbox...")
        response = client.agent_engines.sandboxes.execute_code(
            name=sandbox_name,
            input_data={"code": read_code}
        )

        # Extract the base64 data from response
        chart_base64 = None
        error_msg = None

        if response and hasattr(response, "outputs"):
            for output in response.outputs:
                if output.mime_type == "application/json" and output.metadata is None:
                    try:
                        data = json.loads(output.data.decode("utf-8"))
                        msg = data.get("msg_out", "")
                        if msg.startswith("CHART_DATA:"):
                            chart_base64 = msg.replace("CHART_DATA:", "")
                        elif msg.startswith("ERROR:"):
                            error_msg = msg.replace("ERROR:", "")
                    except (json.JSONDecodeError, AttributeError):
                        pass

        if chart_base64:
            # Decode and save as artifact
            image_bytes = base64.b64decode(chart_base64)
            image_artifact = types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/png"
            )
            version = await callback_context.save_artifact(
                filename="financial_chart.png",
                artifact=image_artifact
            )
            print(f"Saved chart artifact as version {version}")

            # CRITICAL: Clean up the chart file from sandbox after extraction
            # This prevents stale charts from being extracted in future queries
            # if the agent's code execution fails (e.g., malformed function call)
            cleanup_code = '''
import os
if os.path.exists('financial_chart.png'):
    os.remove('financial_chart.png')
    print("CLEANUP:SUCCESS")
else:
    print("CLEANUP:FILE_NOT_FOUND")
'''
            try:
                cleanup_response = client.agent_engines.sandboxes.execute_code(
                    name=sandbox_name,
                    input_data={"code": cleanup_code}
                )
                print("Cleaned up chart file from sandbox for next query")
            except Exception as cleanup_error:
                # Non-fatal - log but don't fail the callback
                print(f"Warning: Could not clean up sandbox file: {cleanup_error}")

            # Store for HTML embedding
            state["chart_base64"] = chart_base64
            state["chart_mime_type"] = "image/png"
            state["execution_result"] = f"Chart saved as artifact (version {version})"

            # IMPORTANT: Set chart_creation_result for downstream agents
            # When using code_executor, the output_key may not be auto-populated
            if "chart_creation_result" not in state or not state.get("chart_creation_result"):
                state["chart_creation_result"] = f"Chart created and saved successfully as financial_chart.png (version {version})"
        elif error_msg:
            # Chart file not found - likely the agent's code execution failed
            # This can happen due to "malformed function call" errors (known Gemini issue)
            state["execution_result"] = f"ERROR: {error_msg}. The chart creator agent may have failed to execute code properly."
            state["chart_creation_result"] = f"Chart creation FAILED: {error_msg}. Please retry the query."
            state["chart_base64"] = ""  # Explicitly set empty to prevent stale data
            print(f"Chart extraction FAILED: {error_msg}")
        else:
            state["execution_result"] = "Warning: Could not extract chart from sandbox"
            state["chart_creation_result"] = "Chart creation completed but extraction had issues"
            print("Warning: Could not extract chart base64 from sandbox response")

    except Exception as e:
        error_msg = f"Failed to extract chart: {str(e)}"
        print(error_msg)
        state["execution_result"] = error_msg
        state["chart_creation_result"] = f"Chart creation encountered an error: {str(e)}"


async def save_html_report_callback(callback_context):
    """Save the generated HTML report as a downloadable artifact.

    This callback runs AFTER the html_report_generator agent finishes,
    extracts the HTML content, injects the base64 chart, and saves it as an artifact.

    Key optimization: The LLM generates HTML with CHART_IMAGE_PLACEHOLDER, and
    this callback replaces it with the actual base64 image. This avoids passing
    the huge base64 string through the LLM's context window.
    """
    from google.genai import types

    state = callback_context.state
    html_report = state.get("html_report", "")

    if not html_report:
        state["report_result"] = "Error: No HTML report was generated"
        return

    # Extract HTML from code blocks if the LLM wrapped it
    html_match = re.search(r"```html\s*(.*?)\s*```", html_report, re.DOTALL)
    if html_match:
        html_content = html_match.group(1)
    else:
        html_match = re.search(r"```\s*(.*?)\s*```", html_report, re.DOTALL)
        if html_match:
            html_content = html_match.group(1)
        else:
            # Assume the entire output is HTML
            html_content = html_report

    # Inject the base64 chart image (optimization: LLM doesn't handle base64)
    chart_base64 = state.get("chart_base64", "")
    chart_mime_type = state.get("chart_mime_type", "image/png")

    if chart_base64:
        # Replace the placeholder with actual base64 image
        html_content = html_content.replace(
            "CHART_IMAGE_PLACEHOLDER",
            f"data:{chart_mime_type};base64,{chart_base64}"
        )
        print(f"Injected chart base64 ({len(chart_base64)} chars) into HTML")
    else:
        print("Warning: No chart_base64 found in state")

    print(f"Saving HTML report ({len(html_content)} chars)...")

    try:
        # Save HTML as artifact
        html_artifact = types.Part.from_bytes(
            data=html_content.encode('utf-8'),
            mime_type="text/html"
        )
        version = await callback_context.save_artifact(
            filename="financial_report.html",
            artifact=html_artifact
        )
        print(f"Saved HTML report artifact as version {version}")
        state["report_result"] = f"Report saved as artifact: financial_report.html (version {version})"

    except Exception as e:
        error_msg = f"Failed to save HTML report: {str(e)}"
        print(error_msg)
        state["report_result"] = error_msg


# --- HTML Report Template ---
# Professional template for the financial report
# NOTE: Double braces {{ }} are used to escape from ADK's template engine
# so they pass through as literal single braces for the LLM to fill in
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Financial Analysis Report</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
        }}
        .report-container {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            padding: 50px;
        }}
        .header {{
            border-bottom: 3px solid #4285f4;
            padding-bottom: 25px;
            margin-bottom: 35px;
        }}
        .header h1 {{
            color: #1a73e8;
            margin: 0 0 10px 0;
            font-size: 2.2em;
        }}
        .header .subtitle {{
            color: #5f6368;
            font-size: 1.1em;
            margin: 0;
        }}
        .header .date {{
            color: #9aa0a6;
            font-size: 0.9em;
            margin-top: 8px;
        }}
        .section {{
            margin-bottom: 35px;
        }}
        .section h2 {{
            color: #202124;
            border-left: 4px solid #4285f4;
            padding-left: 15px;
            margin-bottom: 20px;
            font-size: 1.5em;
        }}
        .section p {{
            color: #3c4043;
            line-height: 1.7;
        }}
        .chart-container {{
            text-align: center;
            margin: 40px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
        }}
        .chart-container img {{
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.15);
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.95em;
        }}
        .data-table th, .data-table td {{
            padding: 14px 18px;
            text-align: left;
            border-bottom: 1px solid #e8eaed;
        }}
        .data-table th {{
            background: #f8f9fa;
            color: #202124;
            font-weight: 600;
        }}
        .data-table tr:hover {{
            background: #f1f3f4;
        }}
        .key-findings ul {{
            list-style: none;
            padding: 0;
        }}
        .key-findings li {{
            padding: 14px 18px;
            margin: 10px 0;
            background: linear-gradient(90deg, #e8f0fe 0%, #f8f9fa 100%);
            border-radius: 6px;
            border-left: 4px solid #4285f4;
            color: #202124;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
        }}
        .metric-card .value {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .metric-card .label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 25px;
            border-top: 1px solid #e8eaed;
            color: #9aa0a6;
            font-size: 0.85em;
            text-align: center;
        }}
        .footer a {{
            color: #1a73e8;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <!-- HEADER -->
        <div class="header">
            <h1>REPORT_TITLE_PLACEHOLDER</h1>
            <p class="subtitle">ENTITY_PLACEHOLDER - METRIC_PLACEHOLDER</p>
            <p class="date">Generated on DATE_PLACEHOLDER</p>
        </div>

        <!-- EXECUTIVE SUMMARY -->
        <div class="section">
            <h2>Executive Summary</h2>
            SUMMARY_HTML_PLACEHOLDER
        </div>

        <!-- KEY METRICS -->
        <div class="section">
            <h2>Key Metrics</h2>
            <div class="metrics-grid">
                METRICS_CARDS_PLACEHOLDER
            </div>
        </div>

        <!-- CHART VISUALIZATION -->
        <div class="section chart-container">
            <h2>Data Visualization</h2>
            <img src="CHART_IMAGE_PLACEHOLDER" alt="Financial Chart">
        </div>

        <!-- DATA TABLE -->
        <div class="section">
            <h2>Data Points</h2>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Period</th>
                        <th>Value</th>
                        <th>Unit</th>
                    </tr>
                </thead>
                <tbody>
                    DATA_ROWS_PLACEHOLDER
                </tbody>
            </table>
        </div>

        <!-- KEY FINDINGS -->
        <div class="section key-findings">
            <h2>Key Findings</h2>
            <ul>
                KEY_FINDINGS_PLACEHOLDER
            </ul>
        </div>

        <!-- FOOTER -->
        <div class="footer">
            <p>Data Source: DATA_SOURCE_PLACEHOLDER</p>
            <p>Report generated by Financial Data Visualization Agent using Google ADK</p>
            <p>Powered by Gemini 3 Pro Preview with Native Code Execution</p>
        </div>
    </div>
</body>
</html>
'''


# --- Structured Output Models ---

class DataPoint(BaseModel):
    """A single financial data point."""

    period: str = Field(
        description="Time period (e.g., '2023', 'Q1 2024', 'Jan 2024')"
    )
    value: float = Field(
        description="Numeric value for this period"
    )
    unit: str = Field(
        default="USD",
        description="Unit of measurement (USD, %, millions, billions, etc.)"
    )


class FinancialDataExtraction(BaseModel):
    """Structured financial data extracted from search results."""

    entity: str = Field(
        description="Company, index, or entity name (e.g., 'Google', 'S&P 500')"
    )
    metric: str = Field(
        description="Financial metric being measured (e.g., 'Revenue', 'Stock Price', 'Net Income')"
    )
    data_points: list[DataPoint] = Field(
        description="List of data points with period and value"
    )
    chart_type: Literal["line", "bar", "area"] = Field(
        default="line",
        description="Recommended chart type: 'line' for trends over time, 'bar' for comparisons, 'area' for cumulative data"
    )
    chart_title: str = Field(
        description="Descriptive title for the chart"
    )
    y_axis_label: str = Field(
        description="Label for the Y-axis (e.g., 'Revenue (Billions USD)')"
    )
    data_source: str = Field(
        default="Google Search",
        description="Primary source of the data"
    )
    notes: str | None = Field(
        default=None,
        description="Any important notes or caveats about the data"
    )


# --- Agent Definitions ---

# Stage 1: Data Fetcher Agent
# Uses Google Search to find financial data based on user query
data_fetcher_agent = LlmAgent(
    model=MODEL,
    name="data_fetcher",
    description="Searches the web for financial data based on user queries using Google Search grounding.",
    instruction=f"""
You are a financial data researcher. Your job is to search for financial data based on the user's query.

**Current Date:** {CURRENT_DATE}

**Your Task:**
1. Analyze the user's query to understand what financial data they need
2. Use the google_search tool to find the most relevant and recent financial data
3. Search for specific numeric data points (revenue, stock prices, earnings, etc.)
4. If the query asks for historical data (e.g., "last 5 years"), ensure you find data for each period

**Search Strategy:**
- For company financials: Search "[Company] [metric] [year range]" (e.g., "Google revenue 2020 2021 2022 2023 2024")
- For stock data: Search "[Company] stock price history [period]"
- For market indices: Search "[Index name] performance [period]"
- Include "annual report" or "quarterly earnings" for official data

**Output:**
Provide a comprehensive summary of the financial data you found, including:
- All numeric values with their time periods
- Sources of the information
- Any relevant context or trends

Be thorough - the next agent will extract structured data from your findings.
""",
    tools=[google_search],
    output_key="raw_financial_data",
)


# Stage 2: Data Extractor Agent
# Extracts structured data points from the raw search results
data_extractor_agent = LlmAgent(
    model=MODEL,
    name="data_extractor",
    description="Extracts structured financial data points from raw search results.",
    instruction="""
You are a data extraction specialist. Your job is to convert unstructured financial data into a clean, structured format.

**Input:** You will receive raw financial data from a previous search in `{raw_financial_data}`

**Your Task:**
1. Identify the main entity (company, index, etc.) and metric being discussed
2. Extract ALL numeric data points with their corresponding time periods
3. Determine the best chart type for visualizing this data:
   - `line`: For trends over time (stock prices, revenue growth)
   - `bar`: For period-by-period comparisons (quarterly earnings)
   - `area`: For cumulative or stacked data
4. Create a descriptive chart title and axis label

**Data Extraction Rules:**
- Convert all values to consistent units (e.g., all in billions or all in millions)
- Ensure periods are in chronological order
- If data is missing for some periods, note this in the 'notes' field
- Round values appropriately (2 decimal places for billions, whole numbers for stock prices)

**Output Format:**
Your response must be a valid JSON object matching the FinancialDataExtraction schema.
""",
    output_schema=FinancialDataExtraction,
    output_key="structured_data",
)


# Stage 3: Chart Creator Agent with NATIVE CODE EXECUTION
# This is the KEY DIFFERENCE from code_execution_01/02:
# - The agent has direct sandbox access via AgentEngineSandboxCodeExecutor
# - It can execute code iteratively and see results
# - Explicit STOP condition prevents infinite loops
# - After-agent callback only extracts the saved chart
chart_creator_agent = LlmAgent(
    # Use gemini-2.5-flash for code execution - better tool calling support
    model="gemini-2.5-flash",
    name="chart_creator",
    description="Creates data visualizations using Python code execution in a sandbox.",
    instruction="""
You are a data visualization expert with Python code execution capability.

**Objective:** Create ONE chart from the financial data in `{structured_data}` and STOP.

**Environment:**
- Python with matplotlib, numpy, pandas
- Variables persist between executions

**Input Data:**
structured_data contains: entity, metric, data_points (period/value/unit), chart_type, chart_title, y_axis_label.

**Execute this code ONCE:**
1. Parse data_points to extract periods and values
2. Create chart with matplotlib: plt.style.use('ggplot'), figsize=(12,6)
3. Save as 'financial_chart.png': plt.savefig('financial_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
4. Close figure: plt.close()

**CRITICAL - STOP IMMEDIATELY AFTER SAVING:**
When you see "Saved artifacts:" with "financial_chart.png" in the output, your task is COMPLETE.
Say "Chart created successfully" and STOP. Do NOT generate more code.
Do NOT try to improve or modify the chart.
Do NOT execute any additional code blocks.
ONE code execution is all that is needed.
""",
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=os.environ.get("SANDBOX_RESOURCE_NAME"),
    ),
    output_key="chart_creation_result",
    # BEFORE: Clean up any stale chart from previous sessions
    before_agent_callback=cleanup_sandbox_before_chart_creation,
    # AFTER: Extract the saved chart file from sandbox
    after_agent_callback=extract_chart_artifact_callback,
)


# Stage 4: Summary Agent
# Creates a final summary combining insights with the visualization
summary_agent = LlmAgent(
    model=MODEL,
    name="summarizer",
    description="Creates a comprehensive summary of the financial data analysis with key insights.",
    instruction="""
You are a financial analyst. Create a summary of the analysis.

**Inputs Available:**
- Raw data: `{raw_financial_data}`
- Structured data: `{structured_data}`
- Chart creation result: `{chart_creation_result}`
- Execution result: `{execution_result}`

**Your Task:**
Create a professional summary including:

1. **Overview** (2-3 sentences)
   - What data was analyzed
   - Time period covered
   - Key entity/metric

2. **Key Findings** (3-5 bullet points)
   - Notable trends (growth, decline, stability)
   - Significant changes between periods

3. **Data Summary**
   - Highest and lowest values
   - Average or total if meaningful
   - Growth rate (if applicable)

4. **Chart**
   - Confirm chart was generated: financial_chart.png
   - Briefly describe what it shows

5. **Sources & Caveats**
   - Note the data source
   - Any limitations

**Format:**
Use markdown with headers and bullet points.
Keep concise - 200-300 words.
""",
    output_key="final_summary",
)


# Stage 5: HTML Report Generator Agent
# Uses LLM to generate a professional HTML report
# Note: The chart image is injected by the callback (not handled by LLM)
html_report_generator = LlmAgent(
    model=MODEL,
    name="html_report_generator",
    description="Generates a professional HTML report with data visualization.",
    instruction=f"""
You are an HTML report generator. Create a complete, self-contained HTML financial report.

**Inputs Available:**
- Structured data: `{{structured_data}}`
- Summary: `{{final_summary}}`

**CRITICAL - CHART IMAGE RULE:**
The chart image MUST use this EXACT src value - do NOT change it:
<img src="CHART_IMAGE_PLACEHOLDER" alt="Financial Chart">
The system will automatically replace CHART_IMAGE_PLACEHOLDER with the actual chart.
If you write anything else (like "financial_chart.png"), the chart will NOT display.

**Your Task:**
Generate a complete HTML document using the template structure shown below.

{HTML_TEMPLATE}

**Placeholder Replacements:**

Replace these placeholders with actual content:
- `REPORT_TITLE_PLACEHOLDER` → Descriptive title (e.g., "Google Annual Revenue Analysis 2020-2024")
- `ENTITY_PLACEHOLDER` → From structured_data.entity
- `METRIC_PLACEHOLDER` → From structured_data.metric
- `DATE_PLACEHOLDER` → {CURRENT_DATE}
- `SUMMARY_HTML_PLACEHOLDER` → Convert final_summary markdown to HTML paragraphs
- `METRICS_CARDS_PLACEHOLDER` → 3-4 metric cards (see format below)
- `DATA_ROWS_PLACEHOLDER` → Table rows from structured_data.data_points
- `KEY_FINDINGS_PLACEHOLDER` → Key points as <li> items
- `DATA_SOURCE_PLACEHOLDER` → From structured_data.data_source

DO NOT replace `CHART_IMAGE_PLACEHOLDER` - leave it exactly as written!

**Metrics cards format** (create 3-4 of these):
<div class="metric-card">
    <div class="value">$350.02B</div>
    <div class="label">Highest Revenue</div>
</div>

**Data rows format** (one per data point):
<tr>
    <td>2024</td>
    <td>350.02</td>
    <td>Billions USD</td>
</tr>

**Key findings format** (3-5 insights):
<li>Revenue grew 91.8% from 2020 to 2024</li>

**Output:**
Return ONLY the complete HTML document. No markdown code blocks, no explanations.
The HTML must be valid and self-contained.
""",
    output_key="html_report",
    # Callback injects base64 chart and saves as artifact
    after_agent_callback=save_html_report_callback,
)


# --- Main Pipeline ---

# Combine all agents into a sequential pipeline
financial_report_pipeline = SequentialAgent(
    name="financial_report_pipeline",
    description="""
    A 5-stage pipeline using NATIVE CODE EXECUTION for chart creation:
    1. Fetches data via Google Search
    2. Extracts structured data points (Pydantic schema)
    3. Creates chart using native code_executor (agent has sandbox access)
    4. Creates text summary with insights
    5. Generates HTML report + saves as downloadable artifact

    KEY DIFFERENCE from code_execution_01/02:
    Stage 3 uses AgentEngineSandboxCodeExecutor directly on the agent
    instead of callback-based execution. The agent can execute code
    iteratively and see results. Explicit STOP condition prevents loops.

    This is an EXPERIMENT to test native code execution architecture.

    Final Output: Downloadable HTML report artifact (financial_report.html)
    """,
    sub_agents=[
        data_fetcher_agent,      # Step 1: Google Search → raw_financial_data
        data_extractor_agent,    # Step 2: Extract → structured_data
        chart_creator_agent,     # Step 3: Native code execution → chart_creation_result
        summary_agent,           # Step 4: Summarize → final_summary
        html_report_generator,   # Step 5: Generate HTML → html_report artifact
    ],
)


# Root agent - entry point
root_agent = financial_report_pipeline
