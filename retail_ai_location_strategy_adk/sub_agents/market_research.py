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

"""Market Research Agent - Part 1 of the Location Strategy Pipeline.

This agent validates macro market viability using live web data from Google Search.
It researches demographics, market trends, and commercial viability.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.genai import types

from ..config import FAST_MODEL, RETRY_INITIAL_DELAY, RETRY_ATTEMPTS
from ..callbacks import before_market_research, after_market_research


MARKET_RESEARCH_INSTRUCTION = """You are a market research analyst specializing in retail location intelligence.

Your task is to research and validate the target market for a new business location.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Research Focus Areas

### 1. DEMOGRAPHICS
- Age distribution (identify key age groups)
- Income levels and purchasing power
- Lifestyle indicators (professionals, students, families)
- Population density and growth trends

### 2. MARKET GROWTH
- Population trends (growing, stable, declining)
- New residential and commercial developments
- Infrastructure improvements (metro, roads, tech parks)
- Economic growth indicators

### 3. INDUSTRY PRESENCE
- Existing similar businesses in the area
- Consumer preferences and spending patterns
- Market saturation indicators
- Success stories or failures of similar businesses

### 4. COMMERCIAL VIABILITY
- Foot traffic patterns (weekday vs weekend)
- Commercial real estate trends
- Typical rental costs (qualitative: low/medium/high)
- Business environment and regulations

## Instructions
1. Use Google Search to find current, verifiable data
2. Cite specific data points with sources where possible
3. Focus on information from the last 1-2 years for relevance
4. Be factual and data-driven, avoid speculation

## Output Format
Provide a structured analysis covering all four focus areas.
Conclude with a clear verdict: Is this a strong market for {business_type}? Why or why not?
Include specific recommendations for market entry strategy.
"""

market_research_agent = LlmAgent(
    name="MarketResearchAgent",
    model=FAST_MODEL,
    description="Researches market viability using Google Search for real-time demographics, trends, and commercial data",
    instruction=MARKET_RESEARCH_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    tools=[google_search],
    output_key="market_research_findings",
    before_agent_callback=before_market_research,
    after_agent_callback=after_market_research,
)
