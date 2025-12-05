# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""HTML Report Generator tool for creating executive reports.

Uses direct text generation (same as original notebook Part 4) to create
McKinsey/BCG style 7-slide HTML presentations from strategic report data.
Saves the generated HTML as an artifact for download in adk web.
"""

import logging
from datetime import datetime
from google.adk.tools import ToolContext
from google.genai import types
from google.genai.errors import ServerError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import PRO_MODEL

logger = logging.getLogger("LocationStrategyPipeline")


async def generate_html_report(report_data: str, tool_context: ToolContext) -> dict:
    """Generate a McKinsey/BCG style HTML executive report and save as artifact.

    This tool creates a professional 7-slide HTML presentation from the
    location intelligence report data using direct text generation with Gemini.
    The generated HTML is automatically saved as an artifact for viewing in adk web.

    Args:
        report_data: The strategic report data in a formatted string containing
                    analysis overview, top recommendation, competition metrics,
                    market characteristics, alternatives, insights, and methodology.
        tool_context: ADK ToolContext for saving artifacts.

    Returns:
        dict: A dictionary containing:
            - status: "success" or "error"
            - message: Status message
            - artifact_filename: Name of saved artifact (if successful)
            - artifact_version: Version number of artifact (if successful)
            - html_length: Character count of generated HTML
            - error_message: Error details (if failed)
    """
    try:
        from google import genai

        # Initialize client (uses GOOGLE_API_KEY from env)
        client = genai.Client()

        current_date = datetime.now().strftime("%Y-%m-%d")

        # Comprehensive prompt for multi-slide HTML generation
        # Adapted from original notebook Part 4
        prompt = f"""Generate a comprehensive, professional HTML report for a location intelligence analysis.

This report should be in the style of McKinsey/BCG consulting presentations:
- Multi-slide format using full-screen scrollable sections
- Modern, clean, executive-ready design
- Data-driven visualizations
- Professional color scheme and typography

CRITICAL REQUIREMENTS:

1. STRUCTURE - Create 7 distinct slides (full-screen sections):

   SLIDE 1 - EXECUTIVE SUMMARY & TOP RECOMMENDATION
   - Large, prominent display of recommended location and score
   - Business type and target location
   - High-level market validation
   - Eye-catching hero section

   SLIDE 2 - TOP RECOMMENDATION DETAILS
   - All strengths with evidence (cards/boxes)
   - All concerns with mitigation strategies
   - Opportunity type and target customer segment

   SLIDE 3 - COMPETITION ANALYSIS
   - Competition metrics (total competitors, density, chain dominance)
   - Visual representation of key numbers (large stat boxes)
   - Average ratings, high performers count

   SLIDE 4 - MARKET CHARACTERISTICS
   - Population density, income level, infrastructure
   - Foot traffic patterns, rental costs
   - Grid/card layout for each characteristic

   SLIDE 5 - ALTERNATIVE LOCATIONS
   - Each alternative in a comparison card
   - Scores, opportunity types, strengths/concerns
   - Why each is not the top choice

   SLIDE 6 - KEY INSIGHTS & NEXT STEPS
   - Strategic insights (bullet points or cards)
   - Actionable next steps (numbered list)

   SLIDE 7 - METHODOLOGY
   - How the analysis was performed
   - Data sources and approach

2. DESIGN:
   - Use professional consulting color palette:
     * Primary: Navy blue (#1e3a8a, #3b82f6) for headers/trust
     * Success: Green (#059669, #10b981) for positive metrics
     * Warning: Amber (#d97706, #f59e0b) for concerns
     * Neutral: Grays (#6b7280, #e5e7eb) for backgrounds
   - Modern sans-serif fonts (system: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto)
   - Cards with subtle shadows and rounded corners
   - Generous white space and padding
   - Responsive grid layouts

3. TECHNICAL:
   - Self-contained: ALL CSS embedded in <style> tag
   - No external dependencies (no CDNs, no external images)
   - Each slide: min-height: 100vh; page-break-after: always;
   - Smooth scroll behavior
   - Print-friendly

4. DATA TO INCLUDE (use EXACTLY this data, do not invent):

{report_data}

5. OUTPUT:
   - Generate ONLY the complete HTML code
   - Start with <!DOCTYPE html>
   - End with </html>
   - NO explanations before or after the HTML
   - NO markdown code fences

Make it visually stunning, data-rich, and executive-ready.

Current date: {current_date}
"""

        logger.info("Generating HTML report using Gemini...")

        # Retry wrapper for handling model overload errors
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=2, min=2, max=30),
            retry=retry_if_exception_type(ServerError),
            before_sleep=lambda retry_state: logger.warning(
                f"Gemini API error, retrying in {retry_state.next_action.sleep} seconds... "
                f"(attempt {retry_state.attempt_number}/3)"
            ),
        )
        def generate_with_retry():
            return client.models.generate_content(
                model=PRO_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=1.0),
            )

        # Direct text generation (NOT code execution)
        # Same as original notebook: types.GenerateContentConfig(temperature=1.0)
        response = generate_with_retry()

        # Extract HTML from response.text
        html_code = response.text
        # Strip markdown code fences if present
        if html_code.startswith("```"):
            # Remove opening fence (```html or ```)
            if html_code.startswith("```html"):
                html_code = html_code[7:]
            elif html_code.startswith("```HTML"):
                html_code = html_code[7:]
            else:
                html_code = html_code[3:]

            # Remove closing fence
            if html_code.rstrip().endswith("```"):
                html_code = html_code.rstrip()[:-3]

            html_code = html_code.strip()

        # Validate we got HTML
        if not html_code.strip().startswith("<!DOCTYPE") and not html_code.strip().startswith("<html"):
            logger.warning("Generated content may not be valid HTML")

        # Save as artifact with proper MIME type so it appears in ADK web UI
        html_artifact = types.Part.from_bytes(
            data=html_code.encode('utf-8'),
            mime_type="text/html"
        )
        artifact_filename = "executive_report.html"

        version = await tool_context.save_artifact(
            filename=artifact_filename,
            artifact=html_artifact
        )

        # Also store in state for AG-UI frontend display
        tool_context.state["html_report_content"] = html_code

        logger.info(f"Saved HTML report artifact: {artifact_filename} (version {version})")

        return {
            "status": "success",
            "message": f"HTML report generated and saved as artifact '{artifact_filename}'",
            "artifact_filename": artifact_filename,
            "artifact_version": version,
            "html_length": len(html_code),
        }

    except Exception as e:
        logger.error(f"Failed to generate HTML report: {e}")
        return {
            "status": "error",
            "error_message": f"Failed to generate HTML report: {str(e)}",
        }
