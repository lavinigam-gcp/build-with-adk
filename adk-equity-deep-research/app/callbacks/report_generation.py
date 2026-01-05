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

"""HTML report generation and artifact saving callback."""

import re

from google.genai import types


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
            print(f"   ✓ Injected chart {chart_index} into HTML")

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

        # Save query summary for next classification
        print(f"\n📝 Saving query summary for future classification...")
        research_plan = state.get("research_plan")
        if research_plan:
            company = research_plan.get("company_name", "Unknown")
            ticker = research_plan.get("ticker", "")
            state["last_query_summary"] = f"Company: {company} ({ticker}), Analysis completed"
            print(f"   ✓ Saved query summary: Company={company}, Ticker={ticker}")
        else:
            state["last_query_summary"] = "Previous analysis completed (no company details available)"
            print(f"   ⚠️  No research plan found, saved generic summary")

        print("="*80 + "\n")

    except Exception as e:
        error_msg = f"Failed to save HTML report: {str(e)}"
        print(f"   ✗ ERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        state["report_result"] = error_msg
        print("="*80 + "\n")
