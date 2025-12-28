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
Comprehensive Equity Research Report Agent (Experiment 04)
==========================================================

A multi-stage agent pipeline that generates professional equity research reports with:
1. Research Planner - Analyzes query and plans metrics/charts needed
2. Parallel Data Fetchers - 4 concurrent agents for different data types
3. Data Consolidator - Merges parallel outputs into structured format
4. Chart Generation Loop - Iterates through metrics generating multiple charts
5. Analysis Writer - Creates narrative analysis sections
6. HTML Report Generator - Creates multi-page professional report

Architecture: SequentialAgent with ParallelAgent + LoopAgent sub-pipelines

Key Design:
- ParallelAgent runs 4 data fetchers concurrently (financial, valuation, market, news)
- LoopAgent iterates through planned metrics, generating one chart per iteration
- ChartProgressChecker (custom BaseAgent) triggers escalation when all charts done
- Callback-based code execution guarantees exactly ONE execution per chart
- Multi-chart HTML report with all visualizations embedded as base64

Final Output: Downloadable HTML report artifact (equity_report.html)
              + Multiple chart artifacts (chart_1.png, chart_2.png, ...)
"""

import base64
import datetime
import json
import os
import re
from typing import Any, AsyncGenerator, Literal

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.tools import google_search, FunctionTool, ToolContext
from google.genai import types
from pydantic import BaseModel, Field


# --- Configuration ---
MODEL = "gemini-3-flash-preview"  # Gemini 3 Flash Preview for all agents
IMAGE_MODEL = "gemini-3-pro-image-preview"  # Gemini 3 Pro for image generation
CURRENT_DATE = datetime.datetime.now().strftime("%Y-%m-%d")


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class MetricSpec(BaseModel):
    """Specification for a single metric to analyze and chart."""

    metric_name: str = Field(
        description="Name of the metric (e.g., 'Revenue', 'P/E Ratio', 'Profit Margin')"
    )
    chart_type: Literal["line", "bar", "area"] = Field(
        default="line",
        description="Chart type: 'line' for trends, 'bar' for comparisons, 'area' for cumulative"
    )
    data_source: Literal["financial", "valuation", "market", "news"] = Field(
        description="Which parallel fetcher provides data for this metric"
    )
    section: Literal["financials", "valuation", "growth", "market"] = Field(
        description="Which report section this metric belongs to"
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Priority 1-10, higher = more important (determines chart order)"
    )
    search_query: str = Field(
        description="Specific search query to find data for this metric"
    )


class ResearchPlan(BaseModel):
    """Plan for the equity research report."""

    company_name: str = Field(
        description="Full company name (e.g., 'Alphabet Inc.')"
    )
    ticker: str = Field(
        description="Stock ticker symbol (e.g., 'GOOGL')"
    )
    exchange: str = Field(
        default="NASDAQ",
        description="Stock exchange (e.g., 'NASDAQ', 'NYSE', 'BSE')"
    )
    metrics_to_analyze: list[MetricSpec] = Field(
        description="List of metrics to analyze and chart (typically 5-8 metrics)"
    )
    report_sections: list[str] = Field(
        default=["overview", "financials", "valuation", "growth", "risks", "recommendation"],
        description="Sections to include in the final report"
    )


class DataPoint(BaseModel):
    """A single data point for a metric."""

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


class MetricData(BaseModel):
    """Extracted data for one metric."""

    metric_name: str = Field(
        description="Name of the metric"
    )
    data_points: list[DataPoint] = Field(
        description="List of data points with period and value"
    )
    chart_type: Literal["line", "bar", "area"] = Field(
        default="line",
        description="Chart type for visualization"
    )
    chart_title: str = Field(
        description="Descriptive title for the chart"
    )
    y_axis_label: str = Field(
        description="Label for the Y-axis"
    )
    section: str = Field(
        description="Report section this belongs to"
    )
    notes: str | None = Field(
        default=None,
        description="Any notes or caveats about the data"
    )


class ConsolidatedResearchData(BaseModel):
    """All research data consolidated from parallel fetchers."""

    company_name: str = Field(
        description="Company name"
    )
    ticker: str = Field(
        description="Stock ticker"
    )
    metrics: list[MetricData] = Field(
        description="List of extracted metrics with data"
    )
    company_overview: str = Field(
        description="Brief company description and business model"
    )
    news_summary: str = Field(
        description="Summary of recent news and developments"
    )
    analyst_ratings: str = Field(
        description="Analyst ratings and price targets"
    )
    key_risks: list[str] = Field(
        default_factory=list,
        description="Key risk factors for the company"
    )


class ChartResult(BaseModel):
    """Result of chart generation."""

    chart_index: int = Field(
        description="Chart number (1-indexed)"
    )
    metric_name: str = Field(
        description="Name of the metric charted"
    )
    filename: str = Field(
        description="Artifact filename (e.g., 'chart_1.png')"
    )
    base64_data: str = Field(
        description="Base64 encoded chart image"
    )
    section: str = Field(
        description="Report section this chart belongs to"
    )


class AnalysisSections(BaseModel):
    """Narrative analysis sections for the report."""

    executive_summary: str = Field(
        description="1-2 paragraph executive summary with investment recommendation"
    )
    company_overview: str = Field(
        description="Company description, business model, competitive position"
    )
    financial_analysis: str = Field(
        description="Analysis of revenue, profit, margins, EPS trends"
    )
    valuation_analysis: str = Field(
        description="Analysis of P/E, P/B, EV/EBITDA, fair value assessment"
    )
    growth_outlook: str = Field(
        description="Growth catalysts, future opportunities"
    )
    risks_concerns: str = Field(
        description="Key risk factors and headwinds"
    )
    investment_recommendation: str = Field(
        description="Buy/Hold/Sell recommendation with rationale"
    )


class InfographicSpec(BaseModel):
    """Specification for an infographic to generate."""

    infographic_id: int = Field(
        description="Unique identifier for this infographic (1, 2, 3)"
    )
    title: str = Field(
        description="Title of the infographic (e.g., 'Business Model Overview')"
    )
    infographic_type: Literal["business_model", "competitive_landscape", "growth_drivers"] = Field(
        description="Type of infographic to generate"
    )
    key_elements: list[str] = Field(
        description="List of key elements/data points to include in the infographic"
    )
    visual_style: str = Field(
        default="modern, professional, corporate color scheme",
        description="Visual style description for the infographic"
    )
    prompt: str = Field(
        description="Detailed prompt for image generation"
    )


class InfographicPlan(BaseModel):
    """Plan for all infographics to generate."""

    company_name: str = Field(
        description="Company name for context"
    )
    infographics: list[InfographicSpec] = Field(
        description="List of 3 infographics to generate"
    )


class InfographicResult(BaseModel):
    """Result of infographic generation."""

    infographic_id: int = Field(
        description="Infographic number (1, 2, 3)"
    )
    title: str = Field(
        description="Title of the generated infographic"
    )
    filename: str = Field(
        description="Artifact filename (e.g., 'infographic_1.png')"
    )
    base64_data: str = Field(
        description="Base64 encoded infographic image"
    )
    infographic_type: str = Field(
        description="Type of infographic"
    )


# =============================================================================
# IMAGE GENERATION TOOL
# =============================================================================

async def generate_infographic(
    prompt: str,
    infographic_id: int,
    title: str,
    tool_context: ToolContext
) -> dict:
    """Generate an infographic image using Gemini 3 Pro Image model.

    Args:
        prompt: Detailed prompt for the infographic
        infographic_id: ID number for this infographic (1, 2, or 3)
        title: Title of the infographic
        tool_context: ADK tool context for state and artifact access

    Returns:
        dict with success status and infographic details
    """
    from google import genai
    from google.genai import types as genai_types

    print(f"Generating infographic {infographic_id}: {title}")

    try:
        # Initialize Vertex AI client
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )

        # Generate infographic with Gemini 3 Pro Image model
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=genai_types.ImageConfig(
                    aspect_ratio="16:9"
                ),
            ),
        )

        # Extract image from response
        image_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                image_bytes = part.inline_data.data
                break

        if not image_bytes:
            print(f"Warning: No image generated for infographic {infographic_id}")
            return {
                "success": False,
                "error": "No image generated",
                "infographic_id": infographic_id
            }

        # Save as artifact
        filename = f"infographic_{infographic_id}.png"
        image_artifact = genai_types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/png"
        )
        version = await tool_context.save_artifact(
            filename=filename,
            artifact=image_artifact
        )
        print(f"Saved infographic artifact '{filename}' as version {version}")

        # Store base64 for HTML embedding
        infographic_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Store in state
        state = tool_context.state
        infographics_generated = state.get("infographics_generated", [])
        infographic_result = {
            "infographic_id": infographic_id,
            "title": title,
            "filename": filename,
            "base64_data": infographic_base64,
            "infographic_type": "generated"
        }
        infographics_generated.append(infographic_result)
        state["infographics_generated"] = infographics_generated

        print(f"Infographic {infographic_id} ({title}) generated successfully")

        return {
            "success": True,
            "infographic_id": infographic_id,
            "title": title,
            "filename": filename,
            "message": f"Infographic '{title}' generated and saved as {filename}"
        }

    except Exception as e:
        error_msg = f"Error generating infographic {infographic_id}: {str(e)}"
        print(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "infographic_id": infographic_id
        }


# Create the FunctionTool
generate_infographic_tool = FunctionTool(generate_infographic)


# =============================================================================
# CALLBACKS
# =============================================================================

async def execute_chart_code_callback(callback_context):
    """Execute the generated chart code after chart_code_generator completes.

    This callback:
    1. Gets the current chart code from state
    2. Executes it ONCE in the sandbox
    3. Saves the chart as a numbered artifact (chart_1.png, chart_2.png, ...)
    4. Stores base64 and appends to charts_generated list
    5. Increments current_chart_index for next iteration
    """
    import vertexai

    state = callback_context.state

    # Get current chart index (1-indexed)
    charts_generated = state.get("charts_generated", [])
    chart_index = len(charts_generated) + 1

    # Get the generated code
    chart_code = state.get("current_chart_code", "")

    if not chart_code:
        print(f"Warning: No chart code for chart {chart_index}")
        return

    # Get current metric info
    consolidated = state.get("consolidated_data")
    metrics = []
    if consolidated:
        if isinstance(consolidated, dict):
            metrics = consolidated.get("metrics", [])
        elif hasattr(consolidated, "metrics"):
            metrics = consolidated.metrics

    current_metric = None
    if chart_index <= len(metrics):
        m = metrics[chart_index - 1]
        current_metric = m if isinstance(m, dict) else m.model_dump() if hasattr(m, 'model_dump') else {}

    metric_name = current_metric.get("metric_name", f"metric_{chart_index}") if current_metric else f"metric_{chart_index}"
    section = current_metric.get("section", "financials") if current_metric else "financials"

    # Extract Python code from markdown code blocks
    code_match = re.search(r"```python\s*(.*?)\s*```", chart_code, re.DOTALL)
    if code_match:
        code_to_execute = code_match.group(1)
    else:
        code_match = re.search(r"```\s*(.*?)\s*```", chart_code, re.DOTALL)
        if code_match:
            code_to_execute = code_match.group(1)
        else:
            code_to_execute = chart_code

    # Replace the generic filename with numbered filename
    code_to_execute = code_to_execute.replace(
        "financial_chart.png",
        f"chart_{chart_index}.png"
    )

    print(f"Executing chart {chart_index} code ({len(code_to_execute)} chars)...")

    # Get sandbox configuration
    sandbox_name = os.environ.get("SANDBOX_RESOURCE_NAME")
    if not sandbox_name:
        print(f"Error: SANDBOX_RESOURCE_NAME not set for chart {chart_index}")
        return

    try:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        vertexai.init(project=project_id, location=location)
        client = vertexai.Client(project=project_id, location=location)

        # Execute the code in sandbox
        response = client.agent_engines.sandboxes.execute_code(
            name=sandbox_name,
            input_data={"code": code_to_execute}
        )

        chart_saved = False
        chart_base64 = ""
        filename = f"chart_{chart_index}.png"

        if response and hasattr(response, "outputs"):
            for output in response.outputs:
                # Look for generated image files
                if output.metadata and output.metadata.attributes:
                    file_name = output.metadata.attributes.get("file_name")
                    if isinstance(file_name, bytes):
                        file_name = file_name.decode("utf-8")

                    # Check if it's our chart (not auto-captured)
                    is_our_chart = (
                        file_name and
                        file_name.endswith((".png", ".jpg", ".jpeg")) and
                        not file_name.startswith("code_execution_image_")
                    )

                    if is_our_chart:
                        image_bytes = output.data

                        # Save as ADK artifact
                        image_artifact = types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=output.mime_type or "image/png"
                        )
                        version = await callback_context.save_artifact(
                            filename=filename,
                            artifact=image_artifact
                        )
                        print(f"Saved chart artifact '{filename}' as version {version}")

                        # Store base64 for HTML embedding
                        chart_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        chart_saved = True
                        break

        if chart_saved:
            # Create chart result and append to list
            chart_result = {
                "chart_index": chart_index,
                "metric_name": metric_name,
                "filename": filename,
                "base64_data": chart_base64,
                "section": section
            }
            charts_generated.append(chart_result)
            state["charts_generated"] = charts_generated

            # Also update charts_summary (without base64) for LLM agents
            charts_summary = state.get("charts_summary", [])
            charts_summary.append({
                "chart_index": chart_index,
                "metric_name": metric_name,
                "section": section,
                "filename": filename,
            })
            state["charts_summary"] = charts_summary
            print(f"Chart {chart_index} ({metric_name}) saved successfully")
        else:
            print(f"Warning: Chart {chart_index} code executed but no image returned")

    except Exception as e:
        print(f"Error executing chart {chart_index}: {e}")


async def initialize_charts_state_callback(callback_context):
    """Initialize charts_generated and charts_summary lists after data consolidation.

    This ensures the template variables exist in state before the chart generation loop starts.
    """
    state = callback_context.state

    # Initialize charts_generated as empty list if not exists
    if "charts_generated" not in state:
        state["charts_generated"] = []
        print("Initialized charts_generated = []")

    # Initialize charts_summary (without base64) for LLM agents
    if "charts_summary" not in state:
        state["charts_summary"] = []
        print("Initialized charts_summary = []")


async def initialize_infographics_state_callback(callback_context):
    """Initialize infographics_generated list after chart generation.

    This ensures the infographics state is ready before parallel generation.
    """
    state = callback_context.state

    # Initialize infographics_generated as empty list if not exists
    if "infographics_generated" not in state:
        state["infographics_generated"] = []
        print("Initialized infographics_generated = []")

    # Also create a summary of charts (without base64) for later agents
    charts_generated = state.get("charts_generated", [])
    charts_summary = []
    for chart in charts_generated:
        charts_summary.append({
            "chart_index": chart.get("chart_index"),
            "metric_name": chart.get("metric_name"),
            "section": chart.get("section"),
            "filename": chart.get("filename"),
        })
    state["charts_summary"] = charts_summary
    print(f"Created charts_summary with {len(charts_summary)} items (no base64)")


async def create_infographics_summary_callback(callback_context):
    """Create infographics_summary without base64 data for later agents."""
    state = callback_context.state

    infographics_generated = state.get("infographics_generated", [])
    infographics_summary = []
    for infographic in infographics_generated:
        infographics_summary.append({
            "infographic_id": infographic.get("infographic_id"),
            "title": infographic.get("title"),
            "infographic_type": infographic.get("infographic_type"),
            "filename": infographic.get("filename"),
        })
    state["infographics_summary"] = infographics_summary
    print(f"Created infographics_summary with {len(infographics_summary)} items (no base64)")


async def save_html_report_callback(callback_context):
    """Save the generated HTML report with all charts and infographics embedded.

    This callback:
    1. Gets the HTML report from state
    2. Injects all chart base64 images (CHART_1_PLACEHOLDER, CHART_2_PLACEHOLDER, etc.)
    3. Injects all infographic base64 images (INFOGRAPHIC_1_PLACEHOLDER, etc.)
    4. Saves as downloadable artifact
    """
    state = callback_context.state
    html_report = state.get("html_report", "")

    if not html_report:
        state["report_result"] = "Error: No HTML report was generated"
        return

    # Extract HTML from code blocks if wrapped
    html_match = re.search(r"```html\s*(.*?)\s*```", html_report, re.DOTALL)
    if html_match:
        html_content = html_match.group(1)
    else:
        html_match = re.search(r"```\s*(.*?)\s*```", html_report, re.DOTALL)
        if html_match:
            html_content = html_match.group(1)
        else:
            html_content = html_report

    # Inject all charts
    charts_generated = state.get("charts_generated", [])
    for chart in charts_generated:
        chart_index = chart.get("chart_index", 0)
        base64_data = chart.get("base64_data", "")

        if base64_data:
            placeholder = f"CHART_{chart_index}_PLACEHOLDER"
            html_content = html_content.replace(
                placeholder,
                f"data:image/png;base64,{base64_data}"
            )
            print(f"Injected chart {chart_index} into HTML")

    # Inject all infographics
    infographics_generated = state.get("infographics_generated", [])
    for infographic in infographics_generated:
        infographic_id = infographic.get("infographic_id", 0)
        base64_data = infographic.get("base64_data", "")

        if base64_data:
            placeholder = f"INFOGRAPHIC_{infographic_id}_PLACEHOLDER"
            html_content = html_content.replace(
                placeholder,
                f"data:image/png;base64,{base64_data}"
            )
            print(f"Injected infographic {infographic_id} into HTML")

    print(f"Saving equity report HTML ({len(html_content)} chars) with {len(charts_generated)} charts and {len(infographics_generated)} infographics...")

    try:
        html_artifact = types.Part.from_bytes(
            data=html_content.encode('utf-8'),
            mime_type="text/html"
        )
        version = await callback_context.save_artifact(
            filename="equity_report.html",
            artifact=html_artifact
        )
        print(f"Saved equity_report.html as version {version}")
        state["report_result"] = f"Report saved: equity_report.html (version {version})"

    except Exception as e:
        error_msg = f"Failed to save HTML report: {str(e)}"
        print(error_msg)
        state["report_result"] = error_msg


# =============================================================================
# CUSTOM AGENTS
# =============================================================================

class ChartProgressChecker(BaseAgent):
    """Custom agent that checks if all charts have been generated.

    This agent runs after each chart generation iteration and:
    - Compares charts_generated count vs metrics count in consolidated data
    - Escalates (exits loop) when all charts are done
    - Otherwise, allows loop to continue
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Check progress and escalate if all charts generated."""

        state = ctx.session.state

        # Get planned metrics count
        consolidated = state.get("consolidated_data")
        planned_count = 0
        if consolidated:
            if isinstance(consolidated, dict):
                planned_count = len(consolidated.get("metrics", []))
            elif hasattr(consolidated, "metrics"):
                planned_count = len(consolidated.metrics)

        # Get generated charts count
        charts_generated = state.get("charts_generated", [])
        generated_count = len(charts_generated)

        print(f"Chart progress: {generated_count}/{planned_count}")

        # Check if all done
        all_done = generated_count >= planned_count and planned_count > 0

        if all_done:
            print("All charts generated - escalating to exit loop")

        yield Event(
            author=self.name,
            content=types.Content(
                parts=[types.Part(text=f"Progress: {generated_count}/{planned_count} charts. {'Complete!' if all_done else 'Continuing...'}")],
                role="model"
            ),
            actions=EventActions(escalate=all_done)
        )


# =============================================================================
# HTML TEMPLATE
# =============================================================================

# Professional multi-section equity research report template
# Double braces {{ }} escape ADK's template engine
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Equity Research Report</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }}
        .report {{
            max-width: 1100px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 40px rgba(0,0,0,0.1);
        }}

        /* Header */
        .header {{
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
            color: white;
            padding: 40px 50px;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header .ticker {{
            font-size: 1.4em;
            opacity: 0.9;
            margin-bottom: 15px;
        }}
        .header .meta {{
            display: flex;
            gap: 30px;
            font-size: 0.95em;
            opacity: 0.8;
        }}
        .rating-badge {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            margin-top: 15px;
        }}
        .rating-buy {{ background: #4caf50; }}
        .rating-hold {{ background: #ff9800; }}
        .rating-sell {{ background: #f44336; }}

        /* Sections */
        .section {{
            padding: 40px 50px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .section:last-child {{ border-bottom: none; }}
        .section h2 {{
            color: #1a237e;
            font-size: 1.6em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #1a237e;
            display: inline-block;
        }}
        .section p {{
            margin-bottom: 15px;
            text-align: justify;
        }}

        /* Key Metrics Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 25px 0;
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
        }}
        .metric-card .label {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-top: 5px;
        }}

        /* Charts */
        .chart-container {{
            background: #fafafa;
            border-radius: 10px;
            padding: 25px;
            margin: 25px 0;
            text-align: center;
        }}
        .chart-container img {{
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .chart-title {{
            font-size: 1.1em;
            color: #555;
            margin-bottom: 15px;
        }}

        /* Tables */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .data-table th, .data-table td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        .data-table th {{
            background: #f5f5f5;
            font-weight: 600;
            color: #333;
        }}
        .data-table tr:hover {{ background: #fafafa; }}

        /* Risk List */
        .risk-list {{
            list-style: none;
        }}
        .risk-list li {{
            padding: 12px 15px;
            margin: 10px 0;
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            border-radius: 0 8px 8px 0;
        }}

        /* Infographics */
        .infographic-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 25px;
            margin: 25px 0;
        }}
        .infographic-card {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        .infographic-card:hover {{
            transform: translateY(-5px);
        }}
        .infographic-card img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .infographic-card .infographic-title {{
            padding: 15px 20px;
            background: linear-gradient(135deg, #00b4d8 0%, #0077b6 100%);
            color: white;
            font-weight: 600;
            text-align: center;
        }}

        /* Data Tables Enhanced */
        .data-section {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            margin: 20px 0;
        }}
        .data-section h3 {{
            color: #495057;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        .data-table-wrapper {{
            overflow-x: auto;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .data-table th {{
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
            color: white;
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
        }}
        .data-table td {{
            padding: 12px 16px;
            border-bottom: 1px solid #e9ecef;
        }}
        .data-table tr:last-child td {{
            border-bottom: none;
        }}
        .data-table tr:hover {{
            background: #f1f3f4;
        }}
        .data-table .number {{
            text-align: right;
            font-family: 'Courier New', monospace;
            font-weight: 500;
        }}
        .data-table .positive {{
            color: #2e7d32;
        }}
        .data-table .negative {{
            color: #c62828;
        }}

        /* Footer */
        .footer {{
            background: #263238;
            color: #b0bec5;
            padding: 30px 50px;
            font-size: 0.85em;
        }}
        .footer a {{ color: #4fc3f7; }}

        /* Print styles */
        @media print {{
            .report {{ box-shadow: none; }}
            .section {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="report">
        <!-- HEADER -->
        <div class="header">
            <h1>COMPANY_NAME_PLACEHOLDER</h1>
            <div class="ticker">TICKER_PLACEHOLDER | EXCHANGE_PLACEHOLDER</div>
            <div class="meta">
                <span>Report Date: DATE_PLACEHOLDER</span>
                <span>Sector: SECTOR_PLACEHOLDER</span>
            </div>
            <div class="rating-badge RATING_CLASS_PLACEHOLDER">RATING_PLACEHOLDER</div>
        </div>

        <!-- EXECUTIVE SUMMARY -->
        <div class="section">
            <h2>Executive Summary</h2>
            EXECUTIVE_SUMMARY_PLACEHOLDER
        </div>

        <!-- KEY METRICS -->
        <div class="section">
            <h2>Key Metrics</h2>
            <div class="metrics-grid">
                KEY_METRICS_PLACEHOLDER
            </div>
        </div>

        <!-- COMPANY OVERVIEW -->
        <div class="section">
            <h2>Company Overview</h2>
            COMPANY_OVERVIEW_PLACEHOLDER
        </div>

        <!-- VISUAL INSIGHTS (INFOGRAPHICS) -->
        <div class="section">
            <h2>Visual Insights</h2>
            <p>AI-generated infographics providing visual representations of key business concepts and data.</p>
            <div class="infographic-grid">
                INFOGRAPHICS_PLACEHOLDER
            </div>
        </div>

        <!-- FINANCIAL PERFORMANCE -->
        <div class="section">
            <h2>Financial Performance</h2>
            FINANCIAL_ANALYSIS_PLACEHOLDER
            FINANCIAL_CHARTS_PLACEHOLDER
        </div>

        <!-- VALUATION ANALYSIS -->
        <div class="section">
            <h2>Valuation Analysis</h2>
            VALUATION_ANALYSIS_PLACEHOLDER
            VALUATION_CHARTS_PLACEHOLDER
        </div>

        <!-- GROWTH OUTLOOK -->
        <div class="section">
            <h2>Growth Outlook</h2>
            GROWTH_OUTLOOK_PLACEHOLDER
            GROWTH_CHARTS_PLACEHOLDER
        </div>

        <!-- RISKS & CONCERNS -->
        <div class="section">
            <h2>Risks & Concerns</h2>
            <p>RISKS_INTRO_PLACEHOLDER</p>
            <ul class="risk-list">
                RISKS_LIST_PLACEHOLDER
            </ul>
        </div>

        <!-- INVESTMENT RECOMMENDATION -->
        <div class="section">
            <h2>Investment Recommendation</h2>
            RECOMMENDATION_PLACEHOLDER
        </div>

        <!-- RAW DATA TABLES -->
        <div class="section">
            <h2>Financial Data Tables</h2>
            <p>Detailed numerical data supporting the analysis above.</p>
            DATA_TABLES_PLACEHOLDER
        </div>

        <!-- FOOTER -->
        <div class="footer">
            <p><strong>Disclaimer:</strong> This report is generated by an AI agent for informational purposes only. It does not constitute financial advice. Always consult a qualified financial advisor before making investment decisions.</p>
            <p style="margin-top: 15px;">Generated by Equity Research Agent using Google ADK | Powered by Gemini</p>
        </div>
    </div>
</body>
</html>
'''


# =============================================================================
# AGENT DEFINITIONS
# =============================================================================

# --- Stage 1: Research Planner Agent ---
research_planner = LlmAgent(
    model=MODEL,
    name="research_planner",
    description="Analyzes user query and creates a structured research plan with metrics to analyze.",
    instruction=f"""
You are an equity research planning specialist. Analyze the user's query and create a comprehensive research plan.

**Current Date:** {CURRENT_DATE}

**Your Task:**
1. Identify the company from the user's query
2. Determine the ticker symbol and exchange
3. Plan which metrics to analyze based on the type of analysis requested
4. Create a list of 5-8 metrics that should be charted

**Standard Metrics for Fundamental Analysis:**

**Financial Metrics (data_source: "financial"):**
- Revenue (5-year trend) - chart_type: line, section: financials
- Net Income / Profit - chart_type: bar, section: financials
- Operating Margin % - chart_type: line, section: financials
- EPS (Earnings Per Share) - chart_type: line, section: financials

**Valuation Metrics (data_source: "valuation"):**
- P/E Ratio - chart_type: bar, section: valuation
- P/B Ratio (Price to Book) - chart_type: bar, section: valuation
- EV/EBITDA - chart_type: bar, section: valuation

**Growth Metrics (data_source: "market"):**
- Revenue Growth Rate % - chart_type: bar, section: growth
- Stock Price (1-year) - chart_type: line, section: market

**For each metric, provide:**
- metric_name: Clear name
- chart_type: "line" for trends, "bar" for comparisons
- data_source: Which fetcher should find this data
- section: Which report section it belongs to
- priority: 1-10 (higher = more important)
- search_query: Specific query to find this data (e.g., "Alphabet revenue 2020 2021 2022 2023 2024")

**Output:** A ResearchPlan object with all planned metrics.
""",
    output_schema=ResearchPlan,
    output_key="research_plan",
)


# --- Stage 2: Parallel Data Fetchers ---
# Four specialized agents that run concurrently

financial_data_fetcher = LlmAgent(
    model=MODEL,
    name="financial_data_fetcher",
    description="Fetches financial performance data (revenue, profit, margins, EPS).",
    instruction=f"""
You are a financial data researcher. Fetch financial performance data for the company.

**Current Date:** {CURRENT_DATE}

**Research Plan:** {{research_plan}}

**Your Task:**
1. Look at the research_plan to identify the company
2. Search for financial metrics: Revenue, Net Income, Operating Margin, EPS
3. Find data for the last 5 years if available
4. Include quarterly data if relevant

**Search Strategy:**
- "[Company] annual revenue 2020 2021 2022 2023 2024"
- "[Company] quarterly earnings report"
- "[Company] profit margin history"
- "[Company] EPS earnings per share history"

**Output:**
Provide comprehensive data with:
- All numeric values with time periods
- Sources of information
- Any notable trends or changes

Be thorough - this data will be extracted for charting.
""",
    tools=[google_search],
    output_key="financial_data",
)


valuation_data_fetcher = LlmAgent(
    model=MODEL,
    name="valuation_data_fetcher",
    description="Fetches valuation metrics (P/E, P/B, EV/EBITDA, fair value).",
    instruction=f"""
You are a valuation analyst. Fetch valuation metrics for the company.

**Current Date:** {CURRENT_DATE}

**Research Plan:** {{research_plan}}

**Your Task:**
1. Search for valuation ratios: P/E, P/B, P/S, EV/EBITDA
2. Find current values and historical comparisons
3. Compare to industry averages if available
4. Look for analyst price targets

**Search Strategy:**
- "[Company] P/E ratio current"
- "[Company] valuation multiples"
- "[Company] EV EBITDA"
- "[Company] analyst price target"

**Output:**
Provide valuation data including:
- Current ratios with dates
- Historical values for comparison
- Industry benchmarks if found
- Analyst ratings summary
""",
    tools=[google_search],
    output_key="valuation_data",
)


market_data_fetcher = LlmAgent(
    model=MODEL,
    name="market_data_fetcher",
    description="Fetches market data (stock price, market cap, volume, 52-week range).",
    instruction=f"""
You are a market data analyst. Fetch stock and market data for the company.

**Current Date:** {CURRENT_DATE}

**Research Plan:** {{research_plan}}

**Your Task:**
1. Search for current stock price and market cap
2. Find 52-week high/low
3. Look for stock price history (1-year trend)
4. Find trading volume data

**Search Strategy:**
- "[Company] stock price today"
- "[Company] market cap"
- "[Company] 52 week high low"
- "[Company] stock price history 1 year"

**Output:**
Provide market data including:
- Current stock price
- Market capitalization
- 52-week range
- Recent price movements
""",
    tools=[google_search],
    output_key="market_data",
)


news_sentiment_fetcher = LlmAgent(
    model=MODEL,
    name="news_sentiment_fetcher",
    description="Fetches recent news, analyst ratings, and market sentiment.",
    instruction=f"""
You are a news and sentiment analyst. Gather recent news and analyst opinions.

**Current Date:** {CURRENT_DATE}

**Research Plan:** {{research_plan}}

**Your Task:**
1. Search for recent news (last 30 days)
2. Find analyst ratings (buy/hold/sell distribution)
3. Look for earnings surprises or guidance updates
4. Identify key risks and concerns mentioned

**Search Strategy:**
- "[Company] news today"
- "[Company] analyst rating upgrade downgrade"
- "[Company] earnings guidance 2024 2025"
- "[Company] risks concerns"

**Output:**
Provide:
- Summary of recent news (3-5 key items)
- Analyst consensus rating
- Key risks mentioned in news
- Any catalysts or upcoming events
""",
    tools=[google_search],
    output_key="news_data",
)


# Combine fetchers into ParallelAgent
parallel_data_gatherers = ParallelAgent(
    name="parallel_data_gatherers",
    description="Runs 4 data fetchers concurrently for different data types.",
    sub_agents=[
        financial_data_fetcher,
        valuation_data_fetcher,
        market_data_fetcher,
        news_sentiment_fetcher,
    ],
)


# --- Stage 3: Data Consolidator Agent ---
data_consolidator = LlmAgent(
    model=MODEL,
    name="data_consolidator",
    description="Merges all parallel fetcher outputs into structured format for charting.",
    instruction="""
You are a data consolidation specialist. Merge all gathered data into a structured format.

**Inputs:**
- Research Plan: {research_plan}
- Financial Data: {financial_data}
- Valuation Data: {valuation_data}
- Market Data: {market_data}
- News Data: {news_data}

**Your Task:**
1. For EACH metric in research_plan.metrics_to_analyze:
   - Find the corresponding data from the appropriate fetcher output
   - Extract numeric data points with periods
   - Create a MetricData object with:
     - metric_name: Name of the metric
     - data_points: List of (period, value, unit) tuples
     - chart_type: From the research plan
     - chart_title: Descriptive title for the chart
     - y_axis_label: Appropriate label for Y-axis
     - section: Which report section
     - notes: Any caveats about the data

2. Compile company overview from financial_data and news_data

3. Summarize news and analyst ratings from news_data

4. List key risks mentioned

**Data Extraction Rules:**
- Use consistent units (billions for revenue, % for margins)
- Ensure periods are in chronological order
- If data is missing, note it and provide what's available
- Round appropriately (2 decimals for ratios, whole numbers for prices)

**Output:** A ConsolidatedResearchData object with all metrics ready for charting.
""",
    output_schema=ConsolidatedResearchData,
    output_key="consolidated_data",
    after_agent_callback=initialize_charts_state_callback,  # Initialize charts_generated = []
)


# --- Stage 4: Chart Generation Loop ---
# Iterates through each metric, generating one chart per iteration

chart_code_generator = LlmAgent(
    model=MODEL,
    name="chart_code_generator",
    description="Generates Python matplotlib code for ONE chart per iteration.",
    instruction="""
You are a data visualization expert. Generate Python code for ONE chart.

**Inputs:**
- Consolidated Data: {consolidated_data}
- Charts Summary: {charts_summary}

**Your Task:**
1. Look at charts_summary to see which charts have been created (by metric_name)
2. Find the NEXT metric in consolidated_data.metrics that hasn't been charted yet
3. Generate matplotlib code for ONLY that one chart
4. The chart should be saved as "financial_chart.png" (callback will rename it)

**Code Template:**
```python
import matplotlib.pyplot as plt
import numpy as np

# Data from consolidated_data.metrics[N]
periods = [...]  # Extract from data_points
values = [...]   # Extract from data_points

# Create figure
fig, ax = plt.subplots(figsize=(10, 6))
plt.style.use('ggplot')

# Create chart (line/bar/area based on chart_type)
ax.plot(periods, values, marker='o', linewidth=2, markersize=8)  # or ax.bar()

# Labels and title
ax.set_title('Chart Title', fontsize=14, fontweight='bold')
ax.set_xlabel('Period', fontsize=12)
ax.set_ylabel('Y-Axis Label', fontsize=12)
ax.grid(True, alpha=0.3)

# Rotate x-labels if needed
plt.xticks(rotation=45, ha='right')

# Save
plt.tight_layout()
plt.savefig('financial_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("Chart saved successfully")
```

**IMPORTANT:**
- Generate code for only ONE chart (the next one in sequence)
- Do NOT use seaborn (not available in sandbox)
- Always end with plt.savefig('financial_chart.png', ...) and plt.close()
- Output ONLY the Python code in a ```python ... ``` block

**Output:** Python code for ONE chart.
""",
    output_key="current_chart_code",
    after_agent_callback=execute_chart_code_callback,
)


# Progress checker agent
chart_progress_checker = ChartProgressChecker(
    name="chart_progress_checker",
)


# Combine into LoopAgent
chart_generation_loop = LoopAgent(
    name="chart_generation_loop",
    description="Iterates through metrics, generating one chart per iteration until all done.",
    max_iterations=10,  # Max 10 charts per report
    sub_agents=[
        chart_code_generator,
        chart_progress_checker,
    ],
)


# --- Stage 5: Infographic Planning and Generation ---
# Plans and generates 3 AI-powered infographics in parallel

infographic_planner = LlmAgent(
    model=MODEL,
    name="infographic_planner",
    description="Plans 3 AI-generated infographics based on company research data.",
    instruction="""
You are a visual communications specialist. Plan 3 infographics to enhance the equity research report.

**Inputs:**
- Research Plan: {research_plan}
- Consolidated Data: {consolidated_data}
- Company Overview from news: {news_data}

**Your Task:**
Create exactly 3 infographic specifications:

1. **Business Model Infographic** (infographic_id: 1):
   - Type: "business_model"
   - Visualize: How the company makes money, key revenue streams, business segments
   - Include: Revenue breakdown, key products/services, market position
   - Style: Clean, professional diagram with icons and flow arrows

2. **Competitive Landscape Infographic** (infographic_id: 2):
   - Type: "competitive_landscape"
   - Visualize: Company's position vs competitors
   - Include: Market share, key competitors, competitive advantages
   - Style: Comparison diagram or positioning map

3. **Growth Drivers Infographic** (infographic_id: 3):
   - Type: "growth_drivers"
   - Visualize: Key growth catalysts and opportunities
   - Include: Future growth areas, expansion plans, innovation pipeline
   - Style: Forward-looking visual with growth arrows and icons

**For each infographic, provide:**
- infographic_id: 1, 2, or 3
- title: Clear, descriptive title
- infographic_type: "business_model", "competitive_landscape", or "growth_drivers"
- key_elements: List of specific data points to visualize
- visual_style: Description of the visual approach
- prompt: DETAILED prompt for image generation (be very specific about layout, colors, text to include)

**Prompt Guidelines:**
- Be VERY specific about what to show visually
- Include actual company name and data from consolidated_data
- Describe the layout: icons, arrows, boxes, text placement
- Specify colors: use professional corporate colors
- Request: "Create a professional infographic..."
- Include key statistics and numbers from the data

**Example Prompt:**
"Create a professional business infographic for [Company Name]. Show their business model with:
- Header: 'How [Company] Makes Money'
- Three main revenue streams as colored boxes with icons: [Stream 1] ($X billion), [Stream 2] ($Y billion), [Stream 3] ($Z billion)
- Use blue and green corporate colors
- Include company logo placeholder
- Clean, modern design with arrows showing money flow
- Professional font, data-driven visualization"

**Output:** An InfographicPlan object with exactly 3 infographics.
""",
    output_schema=InfographicPlan,
    output_key="infographic_plan",
    after_agent_callback=initialize_infographics_state_callback,
)


# Three parallel infographic generators - each generates one specific infographic
infographic_generator_1 = LlmAgent(
    model=MODEL,
    name="infographic_generator_1",
    description="Generates infographic #1 (Business Model) using the generate_infographic tool.",
    instruction="""
You are an infographic generator. Generate infographic #1: Business Model.

**Input:**
- Infographic Plan: {infographic_plan}

**Your Task:**
1. Find infographic with infographic_id=1 in the plan
2. Use the generate_infographic tool with:
   - prompt: The detailed prompt from the plan (infographic.prompt)
   - infographic_id: 1
   - title: The title from the plan

Call the tool ONCE to generate the infographic.

**Output:** Confirm the infographic was generated successfully.
""",
    tools=[generate_infographic_tool],
    output_key="infographic_1_result",
)


infographic_generator_2 = LlmAgent(
    model=MODEL,
    name="infographic_generator_2",
    description="Generates infographic #2 (Competitive Landscape) using the generate_infographic tool.",
    instruction="""
You are an infographic generator. Generate infographic #2: Competitive Landscape.

**Input:**
- Infographic Plan: {infographic_plan}

**Your Task:**
1. Find infographic with infographic_id=2 in the plan
2. Use the generate_infographic tool with:
   - prompt: The detailed prompt from the plan (infographic.prompt)
   - infographic_id: 2
   - title: The title from the plan

Call the tool ONCE to generate the infographic.

**Output:** Confirm the infographic was generated successfully.
""",
    tools=[generate_infographic_tool],
    output_key="infographic_2_result",
)


infographic_generator_3 = LlmAgent(
    model=MODEL,
    name="infographic_generator_3",
    description="Generates infographic #3 (Growth Drivers) using the generate_infographic tool.",
    instruction="""
You are an infographic generator. Generate infographic #3: Growth Drivers.

**Input:**
- Infographic Plan: {infographic_plan}

**Your Task:**
1. Find infographic with infographic_id=3 in the plan
2. Use the generate_infographic tool with:
   - prompt: The detailed prompt from the plan (infographic.prompt)
   - infographic_id: 3
   - title: The title from the plan

Call the tool ONCE to generate the infographic.

**Output:** Confirm the infographic was generated successfully.
""",
    tools=[generate_infographic_tool],
    output_key="infographic_3_result",
)


# Combine into ParallelAgent for concurrent generation
parallel_infographic_generators = ParallelAgent(
    name="parallel_infographic_generators",
    description="Runs 3 infographic generators concurrently.",
    sub_agents=[
        infographic_generator_1,
        infographic_generator_2,
        infographic_generator_3,
    ],
)


# --- Stage 7: Analysis Writer Agent ---
analysis_writer = LlmAgent(
    model=MODEL,
    name="analysis_writer",
    description="Writes narrative analysis sections for the equity research report.",
    before_agent_callback=create_infographics_summary_callback,  # Create summary without base64
    instruction="""
You are a senior equity research analyst. Write professional analysis sections.

**Inputs:**
- Research Plan: {research_plan}
- Consolidated Data: {consolidated_data}

NOTE: Multiple charts and infographics have been generated based on the consolidated data.
Reference the charts in your analysis where appropriate.

**Your Task:**
Write the following sections in a professional, analytical tone:

1. **executive_summary** (2-3 paragraphs):
   - Investment thesis in first sentence
   - Key financial highlights
   - Clear buy/hold/sell recommendation with target price if data supports it

2. **company_overview** (2-3 paragraphs):
   - What the company does
   - Business model and segments
   - Competitive position and market share

3. **financial_analysis** (2-3 paragraphs):
   - Revenue and profit trends
   - Margin analysis
   - EPS growth trajectory
   - Reference the charts that show this data

4. **valuation_analysis** (2-3 paragraphs):
   - Current valuation multiples
   - Comparison to historical averages
   - Fair value assessment

5. **growth_outlook** (2 paragraphs):
   - Growth catalysts and opportunities
   - Competitive advantages (moat)

6. **risks_concerns** (list format):
   - 3-5 key risk factors
   - Industry-specific risks
   - Company-specific concerns

7. **investment_recommendation** (2 paragraphs):
   - Clear Buy/Hold/Sell rating
   - Price target rationale
   - Key takeaways for investors

**Style Guidelines:**
- Use professional, objective language
- Support claims with data from consolidated_data
- Be balanced - acknowledge both positives and risks
- Format as clean HTML paragraphs (use <p> tags)

**Output:** An AnalysisSections object with all sections written.
""",
    output_schema=AnalysisSections,
    output_key="analysis_sections",
)


# --- Stage 8: HTML Report Generator Agent ---
html_report_generator = LlmAgent(
    model=MODEL,
    name="html_report_generator",
    description="Generates the final multi-page HTML equity research report with charts, infographics, and data tables.",
    instruction=f"""
You are an HTML report generator. Create a professional equity research report.

**Inputs:**
- Research Plan: {{research_plan}}
- Consolidated Data: {{consolidated_data}}
- Charts Summary: {{charts_summary}}
- Infographics Summary: {{infographics_summary}}
- Analysis Sections: {{analysis_sections}}

NOTE: The actual image data will be injected by a callback. You just need to use the correct placeholders.

**Template:**
{HTML_TEMPLATE}

**Your Task:**
Generate a complete HTML document by replacing ALL placeholders:

1. **Header Placeholders:**
   - COMPANY_NAME_PLACEHOLDER: Company name from research_plan
   - TICKER_PLACEHOLDER: Ticker from research_plan
   - EXCHANGE_PLACEHOLDER: Exchange from research_plan
   - DATE_PLACEHOLDER: {CURRENT_DATE}
   - SECTOR_PLACEHOLDER: Determine from company info
   - RATING_PLACEHOLDER: Buy/Hold/Sell from analysis
   - RATING_CLASS_PLACEHOLDER: "rating-buy", "rating-hold", or "rating-sell"

2. **Content Placeholders:**
   - EXECUTIVE_SUMMARY_PLACEHOLDER: From analysis_sections.executive_summary (wrap in <p> tags)
   - COMPANY_OVERVIEW_PLACEHOLDER: From analysis_sections.company_overview
   - FINANCIAL_ANALYSIS_PLACEHOLDER: From analysis_sections.financial_analysis
   - VALUATION_ANALYSIS_PLACEHOLDER: From analysis_sections.valuation_analysis
   - GROWTH_OUTLOOK_PLACEHOLDER: From analysis_sections.growth_outlook
   - RISKS_INTRO_PLACEHOLDER: Brief intro to risks
   - RISKS_LIST_PLACEHOLDER: Create <li> items from analysis_sections.risks_concerns
   - RECOMMENDATION_PLACEHOLDER: From analysis_sections.investment_recommendation

3. **Metrics Placeholder:**
   - KEY_METRICS_PLACEHOLDER: Create 4-6 metric cards showing key stats:
     ```html
     <div class="metric-card">
         <div class="value">$350B</div>
         <div class="label">Revenue (TTM)</div>
     </div>
     ```

4. **Chart Placeholders:**
   - For each chart in charts_summary, create a chart container:
     ```html
     <div class="chart-container">
         <div class="chart-title">Chart Title</div>
         <img src="CHART_N_PLACEHOLDER" alt="Chart description">
     </div>
     ```
   - Use CHART_1_PLACEHOLDER, CHART_2_PLACEHOLDER, etc. (the callback will inject base64)
   - Group charts by section (FINANCIAL_CHARTS_PLACEHOLDER, VALUATION_CHARTS_PLACEHOLDER, GROWTH_CHARTS_PLACEHOLDER)

5. **Infographic Placeholders (NEW):**
   - INFOGRAPHICS_PLACEHOLDER: Create infographic cards for each item in infographics_summary:
     ```html
     <div class="infographic-card">
         <img src="INFOGRAPHIC_N_PLACEHOLDER" alt="Infographic title">
         <div class="infographic-title">Infographic Title</div>
     </div>
     ```
   - Use INFOGRAPHIC_1_PLACEHOLDER, INFOGRAPHIC_2_PLACEHOLDER, INFOGRAPHIC_3_PLACEHOLDER
   - The callback will inject the actual base64 images

6. **Data Tables Placeholder (NEW):**
   - DATA_TABLES_PLACEHOLDER: Create data tables from consolidated_data.metrics
   - For each metric, create a table with the data points:
     ```html
     <div class="data-section">
         <h3>Revenue Data</h3>
         <div class="data-table-wrapper">
             <table class="data-table">
                 <thead>
                     <tr>
                         <th>Period</th>
                         <th>Value</th>
                         <th>Unit</th>
                     </tr>
                 </thead>
                 <tbody>
                     <tr>
                         <td>2023</td>
                         <td class="number">$350.0B</td>
                         <td>USD Billions</td>
                     </tr>
                     <!-- More rows... -->
                 </tbody>
             </table>
         </div>
     </div>
     ```
   - Include ALL metrics data from consolidated_data.metrics
   - Use number formatting for values

**CRITICAL - Image Placeholders:**
- For chart 1: <img src="CHART_1_PLACEHOLDER" alt="...">
- For chart 2: <img src="CHART_2_PLACEHOLDER" alt="...">
- For infographic 1: <img src="INFOGRAPHIC_1_PLACEHOLDER" alt="...">
- For infographic 2: <img src="INFOGRAPHIC_2_PLACEHOLDER" alt="...">
- For infographic 3: <img src="INFOGRAPHIC_3_PLACEHOLDER" alt="...">
- Do NOT use base64 directly - use the PLACEHOLDER format

**Output:**
Return the COMPLETE HTML document. No markdown code blocks.
The HTML must be valid and self-contained.
""",
    output_key="html_report",
    after_agent_callback=save_html_report_callback,
)


# =============================================================================
# MAIN PIPELINE
# =============================================================================

equity_research_pipeline = SequentialAgent(
    name="equity_research_pipeline",
    description="""
    An 8-stage pipeline for comprehensive equity research reports with AI-generated infographics:

    1. Research Planner - Analyzes query, plans metrics to chart
    2. Parallel Data Gatherers - 4 concurrent fetchers (financial, valuation, market, news)
    3. Data Consolidator - Merges data into structured format
    4. Chart Generation Loop - Creates multiple charts (one per metric)
    5. Infographic Planner - Plans 3 AI-generated infographics
    6. Parallel Infographic Generators - Generates 3 infographics concurrently
    7. Analysis Writer - Writes professional narrative sections
    8. HTML Report Generator - Creates multi-page report with charts, infographics, and data tables

    Key Features:
    - ParallelAgent for concurrent data fetching (4x faster)
    - LoopAgent for generating multiple charts (5-10 per report)
    - Callback-based code execution (guaranteed single execution per chart)
    - AI-generated infographics using Gemini 3 Pro Image model
    - Professional multi-section HTML report with data tables

    Final Output: equity_report.html + chart_1.png, chart_2.png, ... + infographic_1.png, infographic_2.png, infographic_3.png
    """,
    sub_agents=[
        research_planner,               # 1. Plan metrics
        parallel_data_gatherers,        # 2. Fetch data (parallel)
        data_consolidator,              # 3. Merge & structure
        chart_generation_loop,          # 4. Generate all charts
        infographic_planner,            # 5. Plan 3 infographics
        parallel_infographic_generators, # 6. Generate infographics (parallel)
        analysis_writer,                # 7. Write analysis
        html_report_generator,          # 8. Create HTML report
    ],
)


# Root agent - entry point
root_agent = equity_research_pipeline
