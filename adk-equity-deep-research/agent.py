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
from datetime import datetime
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
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")


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


class QueryClassification(BaseModel):
    """Classification of user message as new query vs follow-up to previous query."""

    query_type: str = Field(
        description="Classification result: 'NEW_QUERY' or 'FOLLOW_UP'"
    )
    reasoning: str = Field(
        description="Brief explanation of why this classification was chosen"
    )
    detected_company: str = Field(
        default="",
        description="Company/stock ticker mentioned in message, if any"
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


class VisualContext(BaseModel):
    """Contextualization for a single visual using Setup→Visual→Interpretation pattern."""

    visual_id: str = Field(
        description="Identifier for the visual: 'chart_1', 'chart_2', 'infographic_1', etc."
    )
    visual_type: Literal["chart", "infographic", "table"] = Field(
        description="Type of visual"
    )
    setup_text: str = Field(
        description="1-2 sentences BEFORE the visual explaining what we're looking at and why it matters"
    )
    interpretation_text: str = Field(
        description="1-2 sentences AFTER the visual explaining insights, implications, and investment thesis connection"
    )


class AnalysisSections(BaseModel):
    """Narrative analysis sections with integrated visual contextualization."""

    executive_summary: str = Field(
        description="1-2 paragraph executive summary with investment recommendation"
    )

    # Company Overview Section
    company_overview_intro: str = Field(
        description="Opening paragraph introducing the company"
    )
    company_overview_visual_contexts: list[VisualContext] = Field(
        default_factory=list,
        description="Contextualization for infographics in company overview (business model, competitive landscape)"
    )
    company_overview_conclusion: str = Field(
        default="",
        description="Concluding paragraph after company overview visuals"
    )

    # Financial Performance Section
    financial_intro: str = Field(
        description="Introduction paragraph before financial charts"
    )
    financial_visual_contexts: list[VisualContext] = Field(
        default_factory=list,
        description="Setup+Interpretation for each financial chart (revenue, profit, margins, EPS)"
    )
    financial_conclusion: str = Field(
        description="Conclusion paragraph synthesizing financial performance insights"
    )

    # Valuation Analysis Section
    valuation_intro: str = Field(
        description="Introduction paragraph before valuation analysis"
    )
    valuation_visual_contexts: list[VisualContext] = Field(
        default_factory=list,
        description="Setup+Interpretation for each valuation chart (P/E, EV/EBITDA, etc.)"
    )
    valuation_conclusion: str = Field(
        description="Conclusion paragraph with fair value assessment"
    )

    # Growth Outlook Section
    growth_intro: str = Field(
        description="Introduction paragraph before growth analysis"
    )
    growth_visual_contexts: list[VisualContext] = Field(
        default_factory=list,
        description="Setup+Interpretation for growth charts and infographics"
    )
    growth_conclusion: str = Field(
        description="Conclusion paragraph on growth prospects"
    )

    # Risks & Concerns
    risks_concerns: str = Field(
        description="Comprehensive risk analysis with bullet points or paragraphs"
    )

    # Investment Recommendation
    investment_recommendation: str = Field(
        description="Buy/Hold/Sell recommendation with clear rationale and price target"
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
                    aspect_ratio="1:1",        # Square format for professional reports
                    image_size="2K"             # High quality for presentations
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


async def generate_all_infographics(
    infographic_plan: dict,  # JSON serialized InfographicPlan
    tool_context: ToolContext
) -> dict:
    """Generate ALL infographics from plan in parallel using asyncio.gather().

    This is the new batch tool that replaces 3 hardcoded generators.
    Handles 2-5 infographics dynamically based on plan.

    Args:
        infographic_plan: Complete infographic plan with 2-5 infographic specs
        tool_context: ADK tool context for state and artifact access

    Returns:
        dict with success status and list of generated infographics
    """
    from google import genai
    from google.genai import types as genai_types
    import asyncio

    print("\n" + "="*80)
    print("BATCH INFOGRAPHIC GENERATION - START")
    print("="*80)

    print(f"🔧 Tool Context - State access available: {hasattr(tool_context, 'state')}")

    # Extract infographics list from plan
    infographics_specs = infographic_plan.get("infographics", [])
    total_count = len(infographics_specs)

    print(f"📊 Plan contains {total_count} infographics to generate")
    print(f"📋 Infographic IDs: {[spec['infographic_id'] for spec in infographics_specs]}")
    print(f"📋 Titles: {[spec['title'] for spec in infographics_specs]}")

    if total_count == 0:
        print("⚠️  WARNING: No infographics in plan, skipping generation")
        return {
            "success": False,
            "error": "No infographics in plan",
            "total_requested": 0,
            "successfully_generated": 0,
            "results": []
        }

    # Initialize Vertex AI client (shared across all generations)
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    print(f"🔧 Initializing Vertex AI client (project={project_id}, location={location})")

    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location
    )

    async def generate_single(infographic_spec: dict, index: int) -> dict:
        """Generate one infographic asynchronously with detailed logging."""
        infographic_id = infographic_spec.get("infographic_id")
        title = infographic_spec.get("title", f"Infographic {infographic_id}")
        prompt = infographic_spec.get("prompt", "")
        infographic_type = infographic_spec.get("infographic_type", "unknown")

        print(f"\n🎨 [{index+1}/{total_count}] Starting generation for infographic #{infographic_id}")
        print(f"   Title: {title}")
        print(f"   Type: {infographic_type}")
        print(f"   Prompt length: {len(prompt)} chars")

        try:
            # Generate with Gemini 3 Pro Image
            print(f"   ⏳ Calling Gemini 3 Pro Image API...")
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=genai_types.ImageConfig(
                        aspect_ratio="1:1",
                        image_size="2K"
                    ),
                ),
            )

            print(f"   ✓ API response received for infographic #{infographic_id}")

            # Extract image bytes
            image_bytes = None
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    image_bytes = part.inline_data.data
                    print(f"   ✓ Image data extracted ({len(image_bytes)} bytes)")
                    break

            if not image_bytes:
                print(f"   ✗ ERROR: No image data in API response for infographic #{infographic_id}")
                return {
                    "success": False,
                    "error": "No image generated in API response",
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
            print(f"   ✓ Saved artifact '{filename}' (version {version})")

            # Encode as base64 for HTML embedding
            infographic_base64 = base64.b64encode(image_bytes).decode('utf-8')

            result = {
                "success": True,
                "infographic_id": infographic_id,
                "title": title,
                "filename": filename,
                "base64_data": infographic_base64,
                "infographic_type": infographic_type
            }

            print(f"   ✅ Infographic #{infographic_id} completed successfully!")
            return result

        except Exception as e:
            error_msg = str(e)
            print(f"   ✗ ERROR generating infographic #{infographic_id}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "infographic_id": infographic_id
            }

    # Generate all infographics in parallel using asyncio.gather
    print(f"\n🚀 Launching {total_count} parallel image generations...")
    print(f"⏱️  Start time: {datetime.now().strftime('%H:%M:%S')}")

    tasks = [
        generate_single(spec, idx)
        for idx, spec in enumerate(infographics_specs)
    ]

    results = await asyncio.gather(*tasks)

    print(f"⏱️  End time: {datetime.now().strftime('%H:%M:%S')}")

    # Filter successful results
    successful_results = [r for r in results if r.get("success")]
    failed_results = [r for r in results if not r.get("success")]

    success_count = len(successful_results)
    failure_count = len(failed_results)

    print(f"\n📈 GENERATION SUMMARY:")
    print(f"   ✅ Successful: {success_count}/{total_count}")
    print(f"   ✗ Failed: {failure_count}/{total_count}")

    if failed_results:
        print(f"\n⚠️  Failed infographics:")
        for failed in failed_results:
            print(f"   - Infographic #{failed.get('infographic_id')}: {failed.get('error')}")

    # Save all successful results to state
    tool_context.state["infographics_generated"] = successful_results
    print(f"\n💾 Saved {success_count} infographics to state['infographics_generated']")

    print("="*80)
    print("BATCH INFOGRAPHIC GENERATION - COMPLETE")
    print("="*80 + "\n")

    # Create lightweight summary for tool response (NO base64 data)
    # Base64 is already saved in state["infographics_generated"] for callback/HTML use
    summary_results = [
        {
            "infographic_id": r.get("infographic_id"),
            "title": r.get("title"),
            "infographic_type": r.get("infographic_type"),
            "filename": r.get("filename"),
            # Explicitly NOT including base64_data to keep conversation history clean
        }
        for r in successful_results
    ]

    print(f"📤 Tool response size: ~{len(str(summary_results))} chars (metadata only, no base64)")

    return {
        "success": success_count > 0,
        "total_requested": total_count,
        "successfully_generated": success_count,
        "failed": failure_count,
        "summary": summary_results,  # Only metadata, not full results
        "message": f"Generated {success_count}/{total_count} infographics successfully. Full data saved to state."
    }


# Create the batch FunctionTool
generate_all_infographics_tool = FunctionTool(generate_all_infographics)


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

    print("\n" + "="*80)
    print("CHART CODE EXECUTION CALLBACK - START")
    print("="*80)

    state = callback_context.state

    print(f"📋 Agent: {callback_context.agent_name}")
    print(f"🔑 Invocation ID: {callback_context.invocation_id}")

    # Get current chart index (1-indexed)
    charts_generated = state.get("charts_generated", [])
    chart_index = len(charts_generated) + 1

    print(f"📊 Processing chart #{chart_index}")
    print(f"   Charts generated so far: {len(charts_generated)}")

    # Get the generated code
    chart_code = state.get("current_chart_code", "")

    if not chart_code:
        print(f"⚠️  WARNING: No chart code found in state for chart #{chart_index}")
        print("="*80 + "\n")
        return

    print(f"   ✓ Retrieved chart code from state ({len(chart_code)} chars)")

    # Get current metric info
    consolidated = state.get("consolidated_data")
    metrics = []
    if consolidated:
        if isinstance(consolidated, dict):
            metrics = consolidated.get("metrics", [])
        elif hasattr(consolidated, "metrics"):
            metrics = consolidated.metrics

    print(f"   Total metrics in plan: {len(metrics)}")

    current_metric = None
    if chart_index <= len(metrics):
        m = metrics[chart_index - 1]
        current_metric = m if isinstance(m, dict) else m.model_dump() if hasattr(m, 'model_dump') else {}

    metric_name = current_metric.get("metric_name", f"metric_{chart_index}") if current_metric else f"metric_{chart_index}"
    section = current_metric.get("section", "financials") if current_metric else "financials"

    print(f"   Metric: {metric_name}")
    print(f"   Section: {section}")

    # Extract Python code from markdown code blocks
    code_match = re.search(r"```python\s*(.*?)\s*```", chart_code, re.DOTALL)
    if code_match:
        code_to_execute = code_match.group(1)
        print(f"   ✓ Extracted Python code from ```python block")
    else:
        code_match = re.search(r"```\s*(.*?)\s*```", chart_code, re.DOTALL)
        if code_match:
            code_to_execute = code_match.group(1)
            print(f"   ✓ Extracted code from ``` block")
        else:
            code_to_execute = chart_code
            print(f"   ⚠️  No code block found, using raw text")

    # Replace the generic filename with numbered filename
    code_to_execute = code_to_execute.replace(
        "financial_chart.png",
        f"chart_{chart_index}.png"
    )

    print(f"\n🔧 Executing chart code in sandbox...")
    print(f"   Code length: {len(code_to_execute)} chars")

    # Get sandbox configuration
    sandbox_name = os.environ.get("SANDBOX_RESOURCE_NAME")
    if not sandbox_name:
        print(f"✗ ERROR: SANDBOX_RESOURCE_NAME environment variable not set")
        print("="*80 + "\n")
        return

    print(f"   Sandbox: {sandbox_name}")

    try:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        print(f"   Project: {project_id}, Location: {location}")

        vertexai.init(project=project_id, location=location)
        client = vertexai.Client(project=project_id, location=location)

        print(f"   ⏳ Sending code to Agent Engine Sandbox...")

        # Execute the code in sandbox
        response = client.agent_engines.sandboxes.execute_code(
            name=sandbox_name,
            input_data={"code": code_to_execute}
        )

        print(f"   ✓ Code execution completed")

        chart_saved = False
        chart_base64 = ""
        filename = f"chart_{chart_index}.png"

        if response and hasattr(response, "outputs"):
            print(f"   Processing {len(response.outputs)} output(s)...")
            for idx, output in enumerate(response.outputs):
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

                    print(f"      Output {idx+1}: {file_name} (is_chart={is_our_chart})")

                    if is_our_chart:
                        image_bytes = output.data
                        print(f"      ✓ Found chart image: {file_name} ({len(image_bytes)} bytes)")

                        # Save as ADK artifact
                        image_artifact = types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=output.mime_type or "image/png"
                        )
                        version = await callback_context.save_artifact(
                            filename=filename,
                            artifact=image_artifact
                        )
                        print(f"   ✓ Saved artifact '{filename}' (version {version})")

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

            print(f"\n✅ Chart #{chart_index} SUCCESS")
            print(f"   Metric: {metric_name}")
            print(f"   Filename: {filename}")
            print(f"   Section: {section}")
            print(f"   Total charts generated: {len(charts_generated)}")
        else:
            print(f"\n⚠️  WARNING: Code executed but no chart image found in outputs")

        print("="*80 + "\n")

    except Exception as e:
        print(f"\n✗ ERROR executing chart #{chart_index}: {str(e)}")
        print("="*80 + "\n")


async def initialize_charts_state_callback(callback_context):
    """Initialize or reset charts_generated, charts_summary, and infographics_summary based on query classification.

    Uses the query_classifier agent's output to determine if this is a NEW_QUERY (reset state) or FOLLOW_UP (preserve state).
    This ensures the template variables exist in state before the chart/infographic generation starts.
    """
    print("\n" + "="*80)
    print("INITIALIZE CHARTS STATE CALLBACK - START")
    print("="*80)

    state = callback_context.state

    print(f"📋 Agent: {callback_context.agent_name}")
    print(f"🔑 Invocation ID: {callback_context.invocation_id}")

    # NEW: Check query classification from classifier agent
    classification = state.get("query_classification")
    query_type = classification.get("query_type", "NEW_QUERY") if classification else "NEW_QUERY"
    reasoning = classification.get("reasoning", "No classification available") if classification else "No classification available"

    print(f"\n🔍 Query Classification: {query_type}")
    print(f"   Reasoning: {reasoning}")

    if query_type == "NEW_QUERY":
        # New query detected - reset visualization state
        print(f"\n🔄 NEW QUERY - Resetting visualization state")
        print("   Clearing old chart and infographic state for fresh analysis...")

        state["charts_generated"] = []
        state["charts_summary"] = []
        state["infographics_summary"] = []

        print("✓ Cleared all chart and infographic state for fresh analysis")
    else:  # FOLLOW_UP
        print(f"\n↪️  FOLLOW-UP QUERY - Preserving existing state")
        print(f"   Current state:")
        print(f"   - charts_generated: {len(state.get('charts_generated', []))} items")
        print(f"   - charts_summary: {len(state.get('charts_summary', []))} items")
        print(f"   - infographics_summary: {len(state.get('infographics_summary', []))} items")

    # Ensure state variables exist (defensive programming)
    if "charts_generated" not in state:
        state["charts_generated"] = []
    if "charts_summary" not in state:
        state["charts_summary"] = []
    if "infographics_summary" not in state:
        state["infographics_summary"] = []

    print("="*80 + "\n")


async def create_infographics_summary_callback(callback_context):
    """Create infographics_summary without base64 data for later agents.

    This runs as after_agent_callback on infographic_generator, ensuring the summary
    exists in session state before analysis_writer tries to use it in its instruction template.
    """
    try:
        print("\n" + "="*80)
        print("CREATE INFOGRAPHICS SUMMARY CALLBACK - START")
        print("="*80)

        state = callback_context.state

        print(f"📋 Agent: {callback_context.agent_name}")
        print(f"🔑 Invocation ID: {callback_context.invocation_id}")

        infographics_generated = state.get("infographics_generated", [])
        print(f"🔍 DEBUG: infographics_generated type: {type(infographics_generated)}")
        print(f"🔍 DEBUG: infographics_generated length: {len(infographics_generated) if isinstance(infographics_generated, list) else 'N/A'}")

        print(f"📊 Found {len(infographics_generated)} generated infographics in state")

        # Calculate total base64 size for debugging
        total_base64_size = 0
        for infographic in infographics_generated:
            base64_data = infographic.get("base64_data", "")
            total_base64_size += len(base64_data)

        print(f"⚠️  Total base64 data size: {total_base64_size:,} chars (~{total_base64_size / (1024*1024):.2f} MB)")
        print(f"   This would exceed LLM context - creating summary without base64...")

        infographics_summary = []
        for infographic in infographics_generated:
            summary_item = {
                "infographic_id": infographic.get("infographic_id"),
                "title": infographic.get("title"),
                "infographic_type": infographic.get("infographic_type"),
                "filename": infographic.get("filename"),
            }
            infographics_summary.append(summary_item)
            print(f"   - Infographic {summary_item['infographic_id']}: {summary_item['title']} ({summary_item['filename']})")

        state["infographics_summary"] = infographics_summary

        # Debug: Check size of all state variables that will be passed to analysis_writer
        print(f"\n📏 STATE SIZE CHECK (for analysis_writer):")
        print(f"   research_plan: {len(str(state.get('research_plan', '')))} chars")
        print(f"   consolidated_data: {len(str(state.get('consolidated_data', '')))} chars")
        print(f"   charts_summary: {len(str(state.get('charts_summary', '')))} chars")
        print(f"   infographics_summary: {len(str(infographics_summary))} chars")

        total_state_size = (
            len(str(state.get('research_plan', ''))) +
            len(str(state.get('consolidated_data', ''))) +
            len(str(state.get('charts_summary', ''))) +
            len(str(infographics_summary))
        )
        print(f"   TOTAL (without base64): {total_state_size:,} chars (~{total_state_size / (1024*1024):.2f} MB)")

        if total_state_size > 500_000:  # ~500KB
            print(f"   ⚠️  WARNING: State size is large - may cause LLM errors")

        print(f"\n✅ Created infographics_summary with {len(infographics_summary)} items (no base64)")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n✗ ERROR in create_infographics_summary_callback: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*80 + "\n")
        # Create empty summary to prevent downstream errors
        callback_context.state["infographics_summary"] = []


async def save_html_report_callback(callback_context):
    """Save the generated HTML report with all charts and infographics embedded.

    This callback:
    1. Gets the HTML report from state
    2. Injects all chart base64 images (CHART_1_PLACEHOLDER, CHART_2_PLACEHOLDER, etc.)
    3. Injects all infographic base64 images (INFOGRAPHIC_1_PLACEHOLDER, etc.)
    4. Saves as downloadable artifact
    """
    print("\n" + "="*80)
    print("SAVE HTML REPORT CALLBACK - START")
    print("="*80)

    state = callback_context.state

    print(f"📋 Agent: {callback_context.agent_name}")
    print(f"🔑 Invocation ID: {callback_context.invocation_id}")

    html_report = state.get("html_report", "")
    print(f"📄 HTML report length: {len(html_report)} chars")

    if not html_report:
        print("✗ ERROR: No HTML report was generated")
        state["report_result"] = "Error: No HTML report was generated"
        print("="*80 + "\n")
        return

    # Extract HTML from code blocks if wrapped
    print(f"📝 Extracting HTML content from report...")
    html_match = re.search(r"```html\s*(.*?)\s*```", html_report, re.DOTALL)
    if html_match:
        html_content = html_match.group(1)
        print(f"   ✓ Extracted from ```html``` code block")
    else:
        html_match = re.search(r"```\s*(.*?)\s*```", html_report, re.DOTALL)
        if html_match:
            html_content = html_match.group(1)
            print(f"   ✓ Extracted from ``` code block")
        else:
            html_content = html_report
            print(f"   ✓ Using raw HTML (no code blocks)")

    print(f"📏 Extracted HTML length: {len(html_content)} chars")

    # Inject all charts
    charts_generated = state.get("charts_generated", [])
    print(f"\n🖼️  Injecting {len(charts_generated)} charts...")
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
    print(f"\n🎨 Injecting {len(infographics_generated)} infographics...")
    for infographic in infographics_generated:
        infographic_id = infographic.get("infographic_id", 0)
        base64_data = infographic.get("base64_data", "")

        if base64_data:
            placeholder = f"INFOGRAPHIC_{infographic_id}_PLACEHOLDER"
            html_content = html_content.replace(
                placeholder,
                f"data:image/png;base64,{base64_data}"
            )
            print(f"   ✓ Injected infographic {infographic_id} into HTML")

    print(f"\n💾 Saving equity report HTML ({len(html_content)} chars) with {len(charts_generated)} charts and {len(infographics_generated)} infographics...")

    try:
        html_artifact = types.Part.from_bytes(
            data=html_content.encode('utf-8'),
            mime_type="text/html"
        )
        print(f"   📦 Created HTML artifact ({len(html_content.encode('utf-8'))} bytes)")

        version = await callback_context.save_artifact(
            filename="equity_report.html",
            artifact=html_artifact
        )
        print(f"   ✅ Saved equity_report.html as version {version}")
        state["report_result"] = f"Report saved: equity_report.html (version {version})"

        # NEW: Save query summary for next classification
        print(f"\n📝 Saving query summary for future classification...")
        research_plan = state.get("research_plan")
        if research_plan:
            company = research_plan.get("company_name", "Unknown")
            ticker = research_plan.get("ticker", "")
            state["last_query_summary"] = f"Company: {company} ({ticker}), Analysis completed"
            print(f"   ✓ Saved query summary: Company={company}, Ticker={ticker}")
        else:
            state["last_query_summary"] = "Previous analysis completed (no company details available)"
            print(f"   ⚠ No research plan found, saved generic summary")

        print("="*80 + "\n")

    except Exception as e:
        error_msg = f"Failed to save HTML report: {str(e)}"
        print(f"   ✗ ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        state["report_result"] = error_msg
        print("="*80 + "\n")


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

        /* Visual Contextualization - Setup → Visual → Interpretation */
        .visual-context {{
            margin: 30px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 12px;
            border-left: 4px solid #1a237e;
        }}
        .visual-context .setup-text {{
            color: #333;
            font-size: 1.05em;
            line-height: 1.7;
            margin-bottom: 20px;
            padding: 15px 20px;
            background: white;
            border-radius: 8px;
            font-style: italic;
        }}
        .visual-context .interpretation-text {{
            color: #1a237e;
            font-size: 1.05em;
            line-height: 1.7;
            margin-top: 20px;
            padding: 15px 20px;
            background: #e8eaf6;
            border-radius: 8px;
            font-weight: 500;
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

# --- Stage 0: Query Classifier Agent ---
query_classifier = LlmAgent(
    model="gemini-2.5-flash",  # Fast, cheap model for classification
    name="query_classifier",
    description="Classifies whether user message is a new equity research query or a follow-up to previous query",
    output_schema=QueryClassification,
    output_key="query_classification",
    instruction="""
You are a query classifier for an equity research agent. Your job is to determine if the user's message is:

1. **NEW_QUERY**: User wants to analyze a DIFFERENT company OR start fresh analysis
   Examples:
   - "Analyze Apple stock"
   - "Comprehensive research on TSMC"
   - "Now do Microsoft instead"
   - "What about Tesla?"
   - "Give me equity research on Amazon"

2. **FOLLOW_UP**: User wants to extend/refine the CURRENT analysis
   Examples:
   - "Add a chart for Operating Margin"
   - "Can you include risk analysis?"
   - "What's the P/E ratio again?"
   - "Now analyze cash flow trends"
   - "Also show me EPS data"

**Analysis Process**:
1. Look at the previous query summary below (if it exists)
2. Check if user mentions a DIFFERENT company/ticker than before
3. Check if user is requesting ADDITIONAL analysis for the SAME company
4. Check for words like "also", "additionally", "furthermore" (follow-up indicators)
5. Check for complete new research requests (new query indicators)

**Decision Rules**:
- If DIFFERENT company mentioned → NEW_QUERY
- If SAME company + additional request → FOLLOW_UP
- If no previous context exists → NEW_QUERY (first query in session)
- If ambiguous + no previous context → NEW_QUERY
- If question about previous results → FOLLOW_UP

**Previous Context:**
{{ last_query_summary }}

**Your Task:**
Analyze the user's current message in this conversation and classify it as NEW_QUERY or FOLLOW_UP. Provide reasoning for your decision and extract the company name/ticker if mentioned.
""",
)

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
    description="Plans 2-5 AI-generated infographics based on company research data and query complexity.",
    instruction="""
You are a visual communications specialist for a major investment bank. Plan infographics to enhance the equity research report.

**Inputs:**
- Research Plan: {research_plan}
- Consolidated Data: {consolidated_data}
- Company Overview from news: {news_data}

**Your Task:**
Create 2-5 infographic specifications based on query complexity and available data:
- **Minimum 2**: Business Model + one other (Competitive OR Growth)
- **Typical 3**: Business Model + Competitive Landscape + Growth Drivers (most common)
- **Maximum 5**: Add Market Position + Risk Landscape for comprehensive analyses

**Common Infographic Types:**

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

**CRITICAL Visual Requirements (MUST FOLLOW):**
- **Background**: ALWAYS use clean WHITE background (#FFFFFF or #F5F5F5)
- **Color Palette**: Professional corporate colors - Blues (#1a237e, #0d47a1, #2196f3), Greens (#2e7d32, #4caf50)
- **NO dark themes, NO black backgrounds, NO dark mode**
- **Typography**: Modern sans-serif fonts (Arial, Helvetica, Open Sans)
- **Style**: Minimalist, data-driven, high contrast for readability
- **Format**: Square (1:1) at 2K resolution - already handled by system

**Prompt Guidelines:**
- Be VERY specific about what to show visually
- Include actual company name and data from consolidated_data
- Describe the layout: icons, arrows, boxes, text placement
- **CRITICAL**: EVERY prompt MUST explicitly specify: "Use a clean WHITE background (#FFFFFF), professional corporate colors (blue and green tones), modern sans-serif typography, and minimalist design"
- Include key statistics and numbers from the data
- Request high contrast between text and background for readability

**Example Prompt:**
"Create a professional business infographic for [Company Name] on a clean WHITE background (#FFFFFF). Show their business model with:
- Header: 'How [Company] Makes Money' in dark blue (#1a237e)
- Three main revenue streams as light blue boxes (#2196f3) with dark text: [Stream 1] ($X billion), [Stream 2] ($Y billion), [Stream 3] ($Z billion)
- Use professional blue (#1a237e, #0d47a1) and green (#2e7d32) corporate colors
- Modern sans-serif font (Arial/Helvetica)
- Clean, minimalist design with dark blue arrows showing money flow
- High contrast, data-driven visualization
- White background throughout"

**Output:** An InfographicPlan object with 2-5 infographics (decide based on query complexity).
""",
    output_schema=InfographicPlan,
    output_key="infographic_plan",
    # No callback needed - batch tool handles state initialization
)


# Single batch infographic generator - dynamically handles 2-5 infographics
infographic_generator = LlmAgent(
    model=MODEL,
    name="infographic_generator",
    description="Generates all planned infographics (2-5) in parallel using batch generation tool.",
    instruction="""
You are an infographic batch generator for professional equity research reports.

**Input:**
- Infographic Plan: {infographic_plan} (contains 2-5 infographic specifications)

**Your Task:**
Call the generate_all_infographics tool ONCE with the entire infographic plan.

The tool will:
1. Extract all infographics from the plan (2, 3, 4, or 5 infographics)
2. Generate ALL of them in parallel using asyncio.gather()
3. Save each as an artifact (infographic_1.png, infographic_2.png, etc.)
4. Store results in state["infographics_generated"]

**CRITICAL INSTRUCTIONS:**
- Call the tool EXACTLY ONCE
- Do NOT retry or make multiple calls
- The tool handles all infographics automatically
- Pass the ENTIRE infographic_plan as parameter

**Output:** Confirmation message with count of successfully generated infographics.
""",
    tools=[generate_all_infographics_tool],
    after_agent_callback=create_infographics_summary_callback,  # Create summary without base64 after generation
)


# --- Stage 7: Analysis Writer Agent ---
analysis_writer = LlmAgent(
    model=MODEL,
    name="analysis_writer",
    description="Writes narrative analysis with visual contextualization using Setup→Visual→Interpretation pattern.",
    instruction="""
You are a senior equity research analyst at a major investment bank (Morgan Stanley / Goldman Sachs caliber).

**YOUR TASK**: Write professional analysis using the "Setup → Visual → Interpretation" pattern for ALL visuals.

**INPUTS**:
- Research Plan: {research_plan}
- Consolidated Data: {consolidated_data}
- Charts Summary: {charts_summary} (list of generated charts with section assignments)
- Infographics Summary: {infographics_summary} (list of generated infographics)

**CRITICAL PATTERN - Setup → Visual → Interpretation**:

For EVERY visual (chart, infographic), you MUST provide:
1. **Setup Text** (BEFORE visual): 1-2 sentences explaining:
   - What metric/concept this visual shows
   - Why it matters to the investment thesis
   - What time period/comparison we're examining

2. **[Visual appears here in HTML]**

3. **Interpretation Text** (AFTER visual): 1-2 sentences explaining:
   - What the visual reveals (trend, insight, conclusion)
   - Implications for valuation/recommendation
   - How this supports/contradicts the investment thesis

**EXAMPLE - Revenue Chart**:

Setup: "Microsoft's revenue trajectory over the past five fiscal years provides critical insight into the company's ability to maintain market leadership during the cloud transition. The chart below tracks total annual revenue from FY2020 through FY2025."

[CHART APPEARS]

Interpretation: "The consistent 14-15% compound annual growth rate, with FY2025 revenue reaching $281.7B, demonstrates Microsoft's successful pivot to recurring subscription revenue. This growth sustainability justifies a premium valuation multiple relative to peers."

**YOUR OUTPUT STRUCTURE**:

For each major section (Company Overview, Financial, Valuation, Growth), provide:

1. **Section Intro**: 1 paragraph setting up the section's analysis
2. **Visual Contexts**: For each chart/infographic in this section, create a VisualContext with:
   - visual_id: "chart_1", "chart_2", "infographic_1", etc.
   - visual_type: "chart", "infographic", or "table"
   - setup_text: The setup paragraph (1-2 sentences)
   - interpretation_text: The interpretation paragraph (1-2 sentences)
3. **Section Conclusion**: 1 paragraph synthesizing insights

**MAPPING VISUALS TO SECTIONS**:

From charts_summary and infographics_summary, assign visuals to sections based on their "section" field:

- **Company Overview** (company_overview_visual_contexts):
  - Business model infographics (type: "business_model")
  - Competitive landscape infographics (type: "competitive_landscape")
  - Market position infographics (if any)

- **Financial Performance** (financial_visual_contexts):
  - Charts with section="financials" (revenue, profit, margins, EPS)
  - Create visual context for EACH chart in order

- **Valuation Analysis** (valuation_visual_contexts):
  - Charts with section="valuation" (P/E, EV/EBITDA, price targets)

- **Growth Outlook** (growth_visual_contexts):
  - Charts with section="growth" (growth rates, market expansion)
  - Growth driver infographics (type: "growth_drivers")
  - Risk landscape infographics (if any) can go here or in risks section

**STYLE GUIDELINES**:
- Professional, objective, analytical tone (Morgan Stanley quality)
- Data-driven: cite specific numbers from consolidated_data
- Balanced: acknowledge both strengths and risks
- Investment-focused: always link back to buy/hold/sell thesis
- Setup text: Forward-looking ("The chart below shows...")
- Interpretation text: Analytical ("This trend indicates...")

**EXECUTIVE SUMMARY** (NO visual contexts, just text):
Write 2-3 paragraphs with:
- First sentence: Investment thesis (Buy/Hold/Sell with target price)
- Key financial highlights and growth trajectory
- Primary catalysts and risks
- Valuation assessment

**RISKS & CONCERNS** (NO visual contexts, just text):
Write comprehensive risk analysis with:
- 3-5 key risk factors as paragraphs or bullet points
- Industry-specific headwinds
- Company-specific vulnerabilities
- Format as HTML paragraphs or list items

**INVESTMENT RECOMMENDATION** (NO visual contexts, just text):
Write 2 paragraphs with:
- Clear Buy/Hold/Sell rating
- Price target with 12-month horizon
- Key reasons supporting recommendation
- Key takeaways for investors

**OUTPUT**: AnalysisSections object with ALL sections and visual contexts properly structured.
""",
    output_schema=AnalysisSections,
    output_key="analysis_sections",
)


# --- Stage 8: HTML Report Generator Agent ---
html_report_generator = LlmAgent(
    model=MODEL,
    name="html_report_generator",
    description="Generates professional equity research report HTML with Setup→Visual→Interpretation contextualization.",
    instruction=f"""
You are generating a professional equity research report with visual contextualization.

**INPUTS:**
- Research Plan: {{research_plan}}
- Consolidated Data: {{consolidated_data}}
- Charts Summary: {{charts_summary}} (list of generated charts)
- Infographics Summary: {{infographics_summary}} (list of generated infographics)
- Analysis Sections: {{analysis_sections}} (NOW INCLUDES VISUAL CONTEXTS)

**Template:**
{HTML_TEMPLATE}

**CRITICAL NEW REQUIREMENT - Visual Contextualization**:

For each section (Company Overview, Financial, Valuation, Growth), you MUST:

1. Get the intro/conclusion paragraphs from analysis_sections
2. For each visual in that section:
   - Find the matching VisualContext from analysis_sections
   - Create a visual-context container with:
     - setup-text paragraph (from visual_context.setup_text)
     - The visual itself (chart or infographic)
     - interpretation-text paragraph (from visual_context.interpretation_text)

**EXAMPLE - Financial Performance Section**:

```html
<div class="section">
    <h2>Financial Performance</h2>
    {{{{ analysis_sections.financial_intro }}}}

    <!-- For each chart in financial section -->
    <div class="visual-context">
        <p class="setup-text">{{{{ visual_context.setup_text }}}}</p>
        <div class="chart-container">
            <div class="chart-title">Annual Revenue (FY2020-FY2025)</div>
            <img src="CHART_1_PLACEHOLDER" alt="Revenue Trend">
        </div>
        <p class="interpretation-text">{{{{ visual_context.interpretation_text }}}}</p>
    </div>

    <!-- Repeat for each financial chart -->

    {{{{ analysis_sections.financial_conclusion }}}}
</div>
```

**MAPPING VISUALS TO SECTIONS**:

**Company Overview Section:**
- Use analysis_sections.company_overview_intro
- For each context in analysis_sections.company_overview_visual_contexts:
  - Create visual-context container with setup/interpretation
  - Use infographic placeholders for infographics in this section
- Use analysis_sections.company_overview_conclusion

**Financial Performance Section:**
- Use analysis_sections.financial_intro
- For each context in analysis_sections.financial_visual_contexts:
  - Match visual_id to chart from charts_summary
  - Create visual-context with setup + chart + interpretation
- Use analysis_sections.financial_conclusion

**Valuation Analysis Section:**
- Use analysis_sections.valuation_intro
- For each context in analysis_sections.valuation_visual_contexts:
  - Create contextualized chart containers
- Use analysis_sections.valuation_conclusion

**Growth Outlook Section:**
- Use analysis_sections.growth_intro
- For each context in analysis_sections.growth_visual_contexts:
  - Include both charts AND growth-related infographics
- Use analysis_sections.growth_conclusion

**STANDARD PLACEHOLDERS (unchanged):**

1. **Header:** COMPANY_NAME_PLACEHOLDER, TICKER_PLACEHOLDER, EXCHANGE_PLACEHOLDER, DATE_PLACEHOLDER: {CURRENT_DATE}, SECTOR_PLACEHOLDER, RATING_PLACEHOLDER, RATING_CLASS_PLACEHOLDER

2. **Executive Summary:** analysis_sections.executive_summary (wrap in <p> tags)

3. **Key Metrics:** KEY_METRICS_PLACEHOLDER - create 4-6 metric cards from consolidated_data

4. **Risks & Concerns:** analysis_sections.risks_concerns (format as <li> items or paragraphs)

5. **Investment Recommendation:** analysis_sections.investment_recommendation (wrap in <p> tags)

6. **Data Tables (Appendix):** DATA_TABLES_PLACEHOLDER - create tables from consolidated_data.metrics

**IMAGE PLACEHOLDERS** (callback injects base64):
- Charts: CHART_1_PLACEHOLDER, CHART_2_PLACEHOLDER, etc.
- Infographics: INFOGRAPHIC_1_PLACEHOLDER, INFOGRAPHIC_2_PLACEHOLDER, etc. (up to 5)

**OUTPUT**: Complete HTML document with ALL visuals properly contextualized. No markdown blocks.
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
    5. Infographic Planner - Plans 2-5 AI-generated infographics (dynamic based on query complexity)
    6. Infographic Generator - Batch generates all infographics in parallel (asyncio.gather)
    7. Analysis Writer - Writes professional narrative sections
    8. HTML Report Generator - Creates multi-page report with charts, infographics, and data tables

    Key Features:
    - ParallelAgent for concurrent data fetching (4x faster)
    - LoopAgent for generating multiple charts (5-10 per report)
    - Dynamic infographic count (2-5) based on query complexity
    - Batch parallel infographic generation (asyncio.gather for true parallelism)
    - Callback-based code execution (guaranteed single execution per chart)
    - AI-generated infographics using Gemini 3 Pro Image model (1:1, 2K, white theme)
    - Professional multi-section HTML report with Setup→Visual→Interpretation pattern

    Final Output: equity_report.html + chart_1.png, chart_2.png, ... + infographic_1.png to infographic_5.png
    """,
    sub_agents=[
        research_planner,               # 1. Plan metrics
        parallel_data_gatherers,        # 2. Fetch data (parallel)
        data_consolidator,              # 3. Merge & structure
        chart_generation_loop,          # 4. Generate all charts
        infographic_planner,            # 5. Plan 2-5 infographics (dynamic)
        infographic_generator,          # 6. Batch generate all infographics (parallel)
        analysis_writer,                # 7. Write analysis with visual context
        html_report_generator,          # 8. Create HTML report
    ],
)

async def ensure_classifier_state_callback(callback_context):
    """Ensure last_query_summary exists before query_classifier runs.

    On the first query in a session, last_query_summary won't exist yet and
    template variable injection will fail with KeyError. Initialize with
    default value if missing.
    """
    state = callback_context.state

    if "last_query_summary" not in state:
        state["last_query_summary"] = "No previous query context (first query in session)"
        print("✓ Initialized last_query_summary for first query in session")


# --- Wrapper Pipeline with Query Classification ---
equity_research_with_classifier = SequentialAgent(
    name="equity_research_with_classifier",
    description="""
    Equity research pipeline with intelligent query classification for multi-query sessions.

    Stage 0: Query Classifier - Classifies user message as NEW_QUERY or FOLLOW_UP
        - NEW_QUERY: Different company → resets visualization state (charts, infographics)
        - FOLLOW_UP: Same company, additional request → preserves state

    Stages 1-8: Standard equity research pipeline

    This wrapper enables:
    - Multiple companies analyzed in same session without chart collisions
    - Follow-up queries like "Add Operating Margin chart" preserve existing state
    - Intelligent semantic detection using company name comparison
    """,
    before_agent_callback=ensure_classifier_state_callback,  # Initialize state before classifier runs
    sub_agents=[
        query_classifier,              # Stage 0: Classify query type
        equity_research_pipeline,      # Stages 1-8: Main pipeline
    ],
)


# Root agent - entry point (with query classification)
root_agent = equity_research_with_classifier
