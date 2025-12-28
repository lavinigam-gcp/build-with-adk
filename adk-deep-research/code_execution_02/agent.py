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
Financial Data Visualization Agent with HTML Report
====================================================

A multi-stage agent pipeline that:
1. Fetches real-time financial data via Google Search
2. Extracts structured data points from search results (Pydantic)
3. Generates Python chart code AND executes via callback (ONCE)
4. Creates a text summary of the analysis
5. Generates a professional HTML report with embedded chart

Architecture: SequentialAgent with 5 sub-agents + execution callbacks

Key Design:
- Code execution happens in a CALLBACK (not an LLM agent) to guarantee
  exactly ONE execution. Using an LLM for code execution can cause loops.
- HTML generation uses LLM directly (no sandbox needed for text generation)
- Chart is embedded as base64 in the HTML for a self-contained report

Final Output: Downloadable HTML report artifact
"""

import base64
import datetime
import json
import os
import re
from typing import Literal

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search
from pydantic import BaseModel, Field


# --- Configuration ---
MODEL = "gemini-3-pro-preview"
CURRENT_DATE = datetime.datetime.now().strftime("%Y-%m-%d")


async def execute_chart_code_callback(callback_context):
    """Execute the generated chart code after code_generator completes.

    This callback runs AFTER the code_generator agent finishes, takes the
    generated code from state, executes it ONCE in the sandbox, and stores
    the result. This guarantees exactly one execution with no LLM in the loop.

    The generated chart image is saved as an ADK artifact so it can be
    displayed in the UI.
    """
    import vertexai
    from google.genai import types

    state = callback_context.state

    # Get the generated code from state
    chart_code = state.get("chart_code", "")

    if not chart_code:
        state["execution_result"] = "Error: No chart code was generated"
        return

    # Extract Python code from markdown code blocks if present
    # The code_generator might wrap code in ```python ... ```
    code_match = re.search(r"```python\s*(.*?)\s*```", chart_code, re.DOTALL)
    if code_match:
        code_to_execute = code_match.group(1)
    else:
        # Try without language specifier
        code_match = re.search(r"```\s*(.*?)\s*```", chart_code, re.DOTALL)
        if code_match:
            code_to_execute = code_match.group(1)
        else:
            # Assume the entire output is code
            code_to_execute = chart_code

    print(f"Executing chart code ({len(code_to_execute)} chars)...")

    # Get sandbox configuration
    sandbox_name = os.environ.get("SANDBOX_RESOURCE_NAME")
    if not sandbox_name:
        state["execution_result"] = "Error: SANDBOX_RESOURCE_NAME not set"
        return

    try:
        # Use Vertex AI client directly for code execution
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        vertexai.init(project=project_id, location=location)
        client = vertexai.Client(project=project_id, location=location)

        # Execute the code in the sandbox (ONCE)
        response = client.agent_engines.sandboxes.execute_code(
            name=sandbox_name,
            input_data={"code": code_to_execute}
        )

        # Process the result and extract artifacts
        # Pattern from tutorial: https://github.com/GoogleCloudPlatform/generative-ai/blob/main/agents/agent_engine/tutorial_get_started_with_code_execution.ipynb
        output_messages = []
        chart_saved = False

        if response and hasattr(response, "outputs"):
            for output in response.outputs:
                # Case 1: JSON output (stdout/stderr) - no metadata
                if output.mime_type == "application/json" and output.metadata is None:
                    try:
                        data = json.loads(output.data.decode("utf-8"))
                        if data.get("msg_out"):
                            output_messages.append(data["msg_out"])
                        if data.get("msg_err"):
                            output_messages.append(f"Error: {data['msg_err']}")
                    except (json.JSONDecodeError, AttributeError):
                        output_messages.append(str(output.data))

                # Case 2: Generated files - have metadata.attributes
                elif output.metadata and output.metadata.attributes:
                    try:
                        # Extract file name from metadata
                        file_name = output.metadata.attributes.get("file_name")
                        if isinstance(file_name, bytes):
                            file_name = file_name.decode("utf-8")

                        print(f"Found generated file: {file_name} ({output.mime_type}, {len(output.data)} bytes)")

                        # Check if it's our explicitly saved chart (not auto-captured images)
                        # The sandbox auto-captures matplotlib figures as "code_execution_image_*"
                        # We only want to save "financial_chart.png" which we explicitly save
                        is_our_chart = (
                            file_name and
                            file_name.endswith((".png", ".jpg", ".jpeg")) and
                            not file_name.startswith("code_execution_image_")
                        )
                        if is_our_chart:
                            # Get image bytes
                            image_bytes = output.data

                            # Create artifact Part and save it to ADK artifact system
                            image_artifact = types.Part.from_bytes(
                                data=image_bytes,
                                mime_type=output.mime_type or "image/png"
                            )
                            version = await callback_context.save_artifact(
                                filename=file_name,
                                artifact=image_artifact
                            )
                            print(f"Saved chart artifact '{file_name}' as version {version}")
                            output_messages.append(f"Chart saved as artifact: {file_name}")
                            chart_saved = True

                            # Store base64 for HTML report embedding
                            chart_base64 = base64.b64encode(image_bytes).decode('utf-8')
                            state["chart_base64"] = chart_base64
                            state["chart_mime_type"] = output.mime_type or "image/png"
                            print(f"Stored chart as base64 ({len(chart_base64)} chars)")
                        else:
                            # For non-image files, just log
                            output_messages.append(f"Generated file: {file_name}")

                    except Exception as e:
                        print(f"Error processing generated file: {e}")
                        output_messages.append(f"Warning: Could not save artifact: {e}")

        if not chart_saved:
            output_messages.append("Note: Chart code executed but no image file was returned from sandbox")

        state["execution_result"] = "\n".join(output_messages) if output_messages else "Code executed successfully"
        print("Chart code execution complete")

    except Exception as e:
        error_msg = f"Code execution failed: {str(e)}"
        print(error_msg)
        state["execution_result"] = error_msg


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
            <p>Powered by Gemini 3 Pro Preview</p>
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


# Stage 3: Code Generator Agent (with execution callback)
# Generates Python code for visualization, then callback executes it ONCE
code_generator_agent = LlmAgent(
    model=MODEL,
    name="code_generator",
    description="Generates Python code for data visualization. Code is executed by callback.",
    instruction="""
You are a code generation expert. Your job is to generate Python code to create a chart.

**Input:** Structured financial data in `{structured_data}`

**Your Task:**
Generate a COMPLETE Python script that creates and saves a chart.

**Code Requirements:**
1. Import libraries at the top:
   ```python
   import matplotlib.pyplot as plt
   import numpy as np
   import pandas as pd
   ```

2. Parse the structured_data dictionary to extract:
   - periods (from data_points)
   - values (from data_points)
   - chart_type, chart_title, y_axis_label

3. Create the appropriate chart:
   - LINE: ax.plot() with markers
   - BAR: ax.bar()
   - AREA: ax.fill_between()

4. Apply styling:
   - plt.style.use('ggplot')
   - Figure size (12, 6)
   - Clear title and axis labels
   - Grid with alpha=0.3

5. Save and close:
   ```python
   plt.tight_layout()
   plt.savefig('financial_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
   plt.close()
   print("Chart saved successfully")
   ```

**IMPORTANT:**
- Do NOT use seaborn (not available in sandbox)
- Output ONLY the Python code wrapped in ```python ... ``` block
- End with print("Chart saved successfully")

**Output Format:**
Return the complete Python code in a code block. Nothing else.
""",
    # NO code_executor on the agent - execution happens in the callback
    output_key="chart_code",
    # Execute code after this agent completes (guarantees exactly ONE execution)
    after_agent_callback=execute_chart_code_callback,
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
- Generated code: `{chart_code}`
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

**Your Task:**
Generate a complete HTML document using the template structure shown below.

{HTML_TEMPLATE}

**Requirements:**

1. **Replace ALL PLACEHOLDER text** with actual content from the inputs:
   - `REPORT_TITLE_PLACEHOLDER`: Create a descriptive title (e.g., "Google Annual Revenue Analysis 2020-2024")
   - `ENTITY_PLACEHOLDER`: Extract from structured_data.entity
   - `METRIC_PLACEHOLDER`: Extract from structured_data.metric
   - `DATE_PLACEHOLDER`: Use current date: {CURRENT_DATE}
   - `SUMMARY_HTML_PLACEHOLDER`: Convert final_summary markdown to HTML paragraphs
   - `METRICS_CARDS_PLACEHOLDER`: Create 3-4 metric cards showing key stats (highest, lowest, average, growth rate)
   - `DATA_ROWS_PLACEHOLDER`: Create <tr> rows from structured_data.data_points
   - `KEY_FINDINGS_PLACEHOLDER`: Extract key points as <li> items
   - `DATA_SOURCE_PLACEHOLDER`: Use structured_data.data_source

2. **Chart placeholder** - Keep CHART_IMAGE_PLACEHOLDER exactly as-is in the img src:
   <img src="CHART_IMAGE_PLACEHOLDER" alt="Financial Chart">
   Do NOT replace this placeholder - the system will inject the chart automatically.

3. **Metrics cards format** (create 3-4 of these):
   <div class="metric-card">
       <div class="value">$350.02B</div>
       <div class="label">Highest Revenue</div>
   </div>

4. **Data rows format** (one per data point):
   <tr>
       <td>2024</td>
       <td>350.02</td>
       <td>Billions USD</td>
   </tr>

5. **Key findings format** (3-5 insights as list items):
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
    A 5-stage pipeline for financial data visualization with HTML report:
    1. Fetches data via Google Search
    2. Extracts structured data points (Pydantic schema)
    3. Generates chart code + executes via callback (saves chart + base64)
    4. Creates text summary with insights
    5. Generates HTML report + saves as downloadable artifact

    Key Design Decisions:
    - Code execution happens in a CALLBACK (not an LLM agent) to
      guarantee exactly ONE execution with no infinite loop risk.
    - HTML generation uses LLM directly (no sandbox needed for text)
    - Chart is embedded as base64 for self-contained HTML report

    Final Output: Downloadable HTML report artifact (financial_report.html)
    """,
    sub_agents=[
        data_fetcher_agent,      # Step 1: Google Search → raw_financial_data
        data_extractor_agent,    # Step 2: Extract → structured_data
        code_generator_agent,    # Step 3: Generate code → chart_code, callback → chart_base64
        summary_agent,           # Step 4: Summarize → final_summary
        html_report_generator,   # Step 5: Generate HTML → html_report artifact
    ],
)


# Root agent - entry point
root_agent = financial_report_pipeline
