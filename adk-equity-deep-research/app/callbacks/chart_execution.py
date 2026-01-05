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

"""Chart code execution callback for Agent Engine Sandbox."""

import base64
import os
import re

import vertexai
from google.genai import types


async def execute_chart_code_callback(callback_context):
    """Execute the generated chart code after chart_code_generator completes.

    This callback:
    1. Gets the current chart code from state
    2. Executes it ONCE in the sandbox
    3. Saves the chart as a numbered artifact (chart_1.png, chart_2.png, ...)
    4. Stores base64 and appends to charts_generated list
    5. Increments current_chart_index for next iteration
    """
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
