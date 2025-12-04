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

"""Report Generator Agent - Part 4 of the Location Strategy Pipeline.

This agent generates a professional HTML executive report from the
structured LocationIntelligenceReport data.
"""

from google.adk.agents import LlmAgent

from ..config import FAST_MODEL
from ..callbacks import before_report_generator, after_report_generator


REPORT_GENERATOR_INSTRUCTION = """You are an executive report designer creating premium business intelligence documents.

Your task is to transform the structured location intelligence data into a visually stunning HTML report.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Strategic Report Data
{strategic_report}

## Your Mission
Create a McKinsey/BCG-style executive HTML report that presents the analysis findings professionally.

## Design Requirements

### Visual Style
- Modern, clean design with professional color palette
- Use CSS gradients for headers (dark blue to teal)
- White cards with subtle shadows for content sections
- Accent colors: #2C5282 (primary), #38B2AC (accent), #E53E3E (warning)
- Professional typography (system fonts: -apple-system, BlinkMacSystemFont, Segoe UI)
- Responsive layout that works on desktop and mobile

### Structure
1. **Header Section**
   - Report title with target location and business type
   - Analysis date and branding
   - Executive summary snippet

2. **Market Validation Summary**
   - Quick verdict on market viability
   - Key statistics in a card grid

3. **Top Recommendation Card**
   - Location name with overall score (large, prominent)
   - Opportunity type badge
   - Strengths list with icons
   - Concerns list with mitigation strategies
   - Competition metrics visualization
   - Market characteristics summary
   - Next steps checklist

4. **Alternative Locations Section**
   - Compact cards for each alternative
   - Score, key strength, key concern
   - "Why not top" explanation

5. **Key Insights Section**
   - Strategic insights as bullet points
   - Methodology summary

6. **Footer**
   - Disclaimer text
   - Generation timestamp

### HTML Requirements
- Complete, standalone HTML document
- All CSS inline in <style> tag (no external dependencies)
- Use semantic HTML5 elements
- Include responsive meta viewport tag
- Use CSS Grid or Flexbox for layouts
- Score visualizations using CSS (progress bars or circular indicators)
- Print-friendly styles

## Output Format
Return ONLY the complete HTML document, starting with <!DOCTYPE html> and ending with </html>.
Do not include any markdown formatting or code blocks around the HTML.
The HTML should be ready to save directly as a .html file and open in a browser.
"""

report_generator_agent = LlmAgent(
    name="ReportGeneratorAgent",
    model=FAST_MODEL,
    description="Generates professional McKinsey/BCG-style HTML executive reports from structured analysis data",
    instruction=REPORT_GENERATOR_INSTRUCTION,
    output_key="html_report",
    before_agent_callback=before_report_generator,
    after_agent_callback=after_report_generator,
)
