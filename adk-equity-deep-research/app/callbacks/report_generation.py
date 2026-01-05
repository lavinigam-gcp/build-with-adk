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

"""HTML and PDF report generation and artifact saving callback."""

import re

from google.genai import types

from ..config import ENABLE_PDF_EXPORT, PDF_REPORT_FILENAME

# Lazy import weasyprint to avoid startup failures if not installed
_weasyprint = None

# CSS to inject for proper PDF page sizing
# HTML uses max-width: 1100px, so we set page to 1100px + minimal margins
PDF_PAGE_CSS = """
@page {
    size: 1100px auto;  /* Exact content width, no extra margins */
    margin: 0.25in 0;   /* Minimal top/bottom margin, no side margins */
}

body {
    max-width: 100% !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 10px !important;
}

.container, .page, main, article, section {
    max-width: 100% !important;
    width: 100% !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
}
"""


def _get_weasyprint():
    """Lazily import weasyprint to handle cases where it's not installed."""
    global _weasyprint
    if _weasyprint is None:
        try:
            import weasyprint
            _weasyprint = weasyprint
        except ImportError:
            _weasyprint = False  # Mark as unavailable
    return _weasyprint if _weasyprint else None


def _inject_pdf_styles(html_content: str) -> str:
    """Inject PDF-specific styles into HTML for proper page sizing."""
    if "</style>" in html_content:
        # Inject before the last </style>
        parts = html_content.rsplit("</style>", 1)
        return parts[0] + PDF_PAGE_CSS + "</style>" + parts[1]
    elif "</head>" in html_content:
        # Inject as new style block before </head>
        return html_content.replace(
            "</head>",
            f"<style>{PDF_PAGE_CSS}</style></head>"
        )
    else:
        # Prepend style block
        return f"<style>{PDF_PAGE_CSS}</style>" + html_content


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

        # Generate PDF if enabled
        if ENABLE_PDF_EXPORT:
            print(f"\n📄 Generating PDF report...")
            weasyprint = _get_weasyprint()
            if weasyprint:
                try:
                    # Inject PDF-specific styles for proper page sizing
                    pdf_html_content = _inject_pdf_styles(html_content)
                    print(f"   ✓ Injected PDF page styles (1100px width)")

                    # WeasyPrint handles base64 data URIs automatically
                    pdf_bytes = weasyprint.HTML(string=pdf_html_content).write_pdf()
                    print(f"   ✓ PDF generated ({len(pdf_bytes)} bytes)")

                    pdf_artifact = types.Part.from_bytes(
                        data=pdf_bytes,
                        mime_type="application/pdf"
                    )

                    pdf_version = await callback_context.save_artifact(
                        filename=PDF_REPORT_FILENAME,
                        artifact=pdf_artifact
                    )
                    print(f"   ✅ Saved {PDF_REPORT_FILENAME} as version {pdf_version}")
                    state["report_result"] += f", {PDF_REPORT_FILENAME} (version {pdf_version})"
                except Exception as pdf_error:
                    print(f"   ⚠️  PDF generation failed: {pdf_error}")
                    print(f"   (HTML report was saved successfully)")
            else:
                print(f"   ⚠️  WeasyPrint not installed - skipping PDF generation")
                print(f"   Install with: pip install weasyprint")
        else:
            print(f"\n📄 PDF export disabled (ENABLE_PDF_EXPORT=false)")

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
