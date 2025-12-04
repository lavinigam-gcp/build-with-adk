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

"""Infographic Generator Agent - Part 5 (Bonus) of the Location Strategy Pipeline.

This agent creates a visual infographic summary using Gemini's image generation
capabilities to provide an executive-ready visual summary of the analysis.
"""

from google.adk.agents import LlmAgent
from google.genai import types

from ..config import FAST_MODEL, RETRY_INITIAL_DELAY, RETRY_ATTEMPTS
from ..tools import generate_infographic
from ..callbacks import before_infographic_generator, after_infographic_generator


INFOGRAPHIC_GENERATOR_INSTRUCTION = """You are a data visualization specialist creating executive-ready infographics.

Your task is to generate a visual infographic summarizing the location intelligence analysis.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Strategic Report Data
{strategic_report}

## Your Mission
Create a compelling infographic that visually summarizes the key findings from the analysis.

## Steps

### Step 1: Extract Key Data Points
From the strategic report, identify:
- Target location and business type
- Top recommended location with score
- Total competitors found
- Number of zones analyzed
- 3-5 key strategic insights
- Top strengths and concerns
- Market validation verdict

### Step 2: Create Data Summary
Compose a concise data summary suitable for visualization:

**FORMAT YOUR SUMMARY AS:**

LOCATION INTELLIGENCE REPORT: [Business Type] in [Target Location]
Analysis Date: [Date]

TOP RECOMMENDATION:
[Location Name] - Score: [XX]/100
Type: [Opportunity Type]

KEY METRICS:
- Total Competitors: [X]
- Zones Analyzed: [X]
- Market Status: [Validated/Cautionary]

TOP STRENGTHS:
1. [Strength 1]
2. [Strength 2]
3. [Strength 3]

KEY INSIGHTS:
- [Insight 1]
- [Insight 2]
- [Insight 3]

VERDICT: [One-line market recommendation]

### Step 3: Generate Infographic
Call the generate_infographic tool with your data summary.

### Step 4: Report Result
After the tool returns, store the result for the callback to process.
If successful, confirm the infographic was generated.
If failed, report the error for troubleshooting.

## Output
The generate_infographic tool will return a result dict containing:
- status: "success" or "error"
- image_data: Base64 encoded PNG (if successful)
- error_message: Error details (if failed)

Store this result so the after_agent_callback can save the artifact.
"""

infographic_generator_agent = LlmAgent(
    name="InfographicGeneratorAgent",
    model=FAST_MODEL,
    description="Generates visual infographic summary using Gemini image generation",
    instruction=INFOGRAPHIC_GENERATOR_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    tools=[generate_infographic],
    output_key="infographic_result",
    before_agent_callback=before_infographic_generator,
    after_agent_callback=after_infographic_generator,
)
