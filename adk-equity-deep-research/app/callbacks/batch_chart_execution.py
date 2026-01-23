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

"""Batch chart code execution callback for Agent Engine Sandbox.

This callback executes a single Python script that generates ALL charts at once,
providing ~5-10x speedup compared to sequential chart generation.

Key differences from sequential callback:
1. Execute ONE script that generates ALL charts (chart_1.png through chart_N.png)
2. Loop through response.outputs to find all chart_*.png files
3. Update charts_generated and charts_summary with all results at once
"""

import base64
import os
import re

import vertexai
from google.genai import types


async def execute_batch_charts_callback(callback_context):
    """Execute batch chart code after batch_chart_generator completes.

    This callback:
    1. Gets the batch chart code from state (all_charts_code)
    2. Executes it ONCE in the sandbox to generate ALL charts
    3. Extracts all chart_*.png files from response.outputs
    4. Saves each chart as a numbered artifact
    5. Populates charts_generated and charts_summary lists
    """
    print("\n" + "="*80)
    print("BATCH CHART EXECUTION CALLBACK - START")
    print("="*80)

    state = callback_context.state

    print(f"📋 Agent: {callback_context.agent_name}")
    print(f"🔑 Invocation ID: {callback_context.invocation_id}")

    # Get the generated batch code
    batch_code = state.get("all_charts_code", "")

    if not batch_code:
        print(f"⚠️  WARNING: No batch chart code found in state")
        print("="*80 + "\n")
        return

    print(f"   ✓ Retrieved batch chart code from state ({len(batch_code)} chars)")

    # Get metrics from consolidated data for mapping
    consolidated = state.get("consolidated_data")
    metrics = []
    if consolidated:
        if isinstance(consolidated, dict):
            metrics = consolidated.get("metrics", [])
        elif hasattr(consolidated, "metrics"):
            metrics = consolidated.metrics

    print(f"   Total metrics in plan: {len(metrics)}")

    # Extract Python code from markdown code blocks
    code_match = re.search(r"```python\s*(.*?)\s*```", batch_code, re.DOTALL)
    if code_match:
        code_to_execute = code_match.group(1)
        print(f"   ✓ Extracted Python code from ```python block")
    else:
        code_match = re.search(r"```\s*(.*?)\s*```", batch_code, re.DOTALL)
        if code_match:
            code_to_execute = code_match.group(1)
            print(f"   ✓ Extracted code from ``` block")
        else:
            code_to_execute = batch_code
            print(f"   ⚠️  No code block found, using raw text")

    print(f"\n🔧 Executing BATCH chart code in sandbox...")
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

        print(f"   ⏳ Sending batch code to Agent Engine Sandbox...")

        # Execute the batch code in sandbox
        response = client.agent_engines.sandboxes.execute_code(
            name=sandbox_name,
            input_data={"code": code_to_execute}
        )

        print(f"   ✓ Batch code execution completed")

        # Initialize result lists
        charts_generated = []
        charts_summary = []

        if response and hasattr(response, "outputs"):
            print(f"   Processing {len(response.outputs)} output(s)...")

            # Collect all chart files
            chart_files = {}  # {chart_index: output}

            for idx, output in enumerate(response.outputs):
                if output.metadata and output.metadata.attributes:
                    file_name = output.metadata.attributes.get("file_name")
                    if isinstance(file_name, bytes):
                        file_name = file_name.decode("utf-8")

                    # Check if it's a chart file (chart_N.png pattern)
                    if file_name:
                        chart_match = re.match(r"chart_(\d+)\.png", file_name)
                        if chart_match:
                            chart_index = int(chart_match.group(1))
                            chart_files[chart_index] = output
                            print(f"      Found chart_{chart_index}.png")

            print(f"\n   📊 Found {len(chart_files)} chart files")

            # Process charts in order
            for chart_index in sorted(chart_files.keys()):
                output = chart_files[chart_index]
                file_name = f"chart_{chart_index}.png"

                # Get metric info for this chart
                current_metric = None
                if chart_index <= len(metrics):
                    m = metrics[chart_index - 1]
                    current_metric = (
                        m if isinstance(m, dict)
                        else m.model_dump() if hasattr(m, 'model_dump')
                        else {}
                    )

                metric_name = (
                    current_metric.get("metric_name", f"metric_{chart_index}")
                    if current_metric else f"metric_{chart_index}"
                )
                section = (
                    current_metric.get("section", "financials")
                    if current_metric else "financials"
                )

                # Get image bytes
                image_bytes = output.data

                # Save as ADK artifact
                image_artifact = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=output.mime_type or "image/png"
                )
                version = await callback_context.save_artifact(
                    filename=file_name,
                    artifact=image_artifact
                )
                print(f"      ✓ Saved artifact '{file_name}' (version {version})")

                # Store base64 for HTML embedding
                chart_base64 = base64.b64encode(image_bytes).decode('utf-8')

                # Create chart result
                chart_result = {
                    "chart_index": chart_index,
                    "metric_name": metric_name,
                    "filename": file_name,
                    "base64_data": chart_base64,
                    "section": section
                }
                charts_generated.append(chart_result)

                # Create summary entry (without base64)
                charts_summary.append({
                    "chart_index": chart_index,
                    "metric_name": metric_name,
                    "section": section,
                    "filename": file_name,
                })

            # Update state with all charts
            state["charts_generated"] = charts_generated
            state["charts_summary"] = charts_summary

            print(f"\n✅ BATCH CHART GENERATION SUCCESS")
            print(f"   Total charts generated: {len(charts_generated)}")
            for cs in charts_summary:
                print(f"      - {cs['filename']}: {cs['metric_name']} ({cs['section']})")
        else:
            print(f"\n⚠️  WARNING: No outputs in sandbox response")

        print("="*80 + "\n")

    except Exception as e:
        print(f"\n✗ ERROR executing batch charts: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*80 + "\n")
