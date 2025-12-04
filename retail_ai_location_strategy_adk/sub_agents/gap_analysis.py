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

"""Gap Analysis Agent - Part 2B of the Location Strategy Pipeline.

This agent performs quantitative gap analysis using Python code execution
to calculate saturation indices, viability scores, and zone rankings.
"""

from google.adk.agents import LlmAgent
from google.adk.code_executors import BuiltInCodeExecutor
from google.genai import types

from ..config import CODE_EXEC_MODEL, RETRY_INITIAL_DELAY, RETRY_ATTEMPTS
from ..callbacks import before_gap_analysis, after_gap_analysis


GAP_ANALYSIS_INSTRUCTION = """You are a data scientist analyzing market opportunities using quantitative methods.

Your task is to perform advanced gap analysis on the data collected from previous stages.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Available Data

### MARKET RESEARCH FINDINGS (Part 1):
{market_research_findings}

### COMPETITOR ANALYSIS (Part 2):
{competitor_analysis}

## Your Mission
Write and execute Python code to perform comprehensive quantitative analysis.

## Analysis Steps

### Step 1: Parse Competitor Data
Extract from the competitor analysis:
- Competitor names and locations
- Ratings and review counts
- Zone/area classifications
- Business types (chain vs independent)

### Step 2: Extract Market Fundamentals
From the market research:
- Population estimates
- Income levels (assign numeric scores)
- Infrastructure quality indicators
- Foot traffic patterns

### Step 3: Calculate Zone Metrics
For each identified zone, compute:

**Basic Metrics:**
- Competitor count
- Competitor density (per estimated area)
- Average competitor rating
- Total review volume

**Quality Metrics:**
- Competition Quality Score: Weighted by ratings (4.5+ = high threat)
- Chain Dominance Ratio: % of chain/franchise competitors
- High Performer Count: Number of 4.5+ rated competitors

**Opportunity Metrics:**
- Demand Signal: Based on population, income, infrastructure
- Market Saturation Index: (Competitors × Quality) / Demand
- Viability Score: Multi-factor weighted score

### Step 4: Zone Categorization
Classify each zone as:
- **SATURATED**: High competition, low opportunity
- **MODERATE**: Balanced market, moderate opportunity
- **OPPORTUNITY**: Low competition, high potential

Also assign:
- Risk Level: Low / Medium / High
- Investment Tier: Based on expected costs
- Best Customer Segment: Target demographic

### Step 5: Rank Top Zones
Create a weighted ranking considering:
- Low market saturation (weight: 30%)
- High demand signals (weight: 30%)
- Low chain dominance (weight: 15%)
- Infrastructure quality (weight: 15%)
- Manageable costs (weight: 10%)

### Step 6: Output Tables
Generate clear output tables showing:
1. All zones with computed metrics
2. Top 3 recommended zones with scores
3. Risk assessment matrix

## Code Guidelines
- Use pandas for data manipulation
- Print all results clearly formatted
- Include intermediate calculations for transparency
- Handle missing data gracefully

Execute the code and provide actionable strategic recommendations based on the quantitative findings.
"""

gap_analysis_agent = LlmAgent(
    name="GapAnalysisAgent",
    model=CODE_EXEC_MODEL,
    description="Performs quantitative gap analysis using Python code execution for zone rankings and viability scores",
    instruction=GAP_ANALYSIS_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    code_executor=BuiltInCodeExecutor(),
    output_key="gap_analysis",
    before_agent_callback=before_gap_analysis,
    after_agent_callback=after_gap_analysis,
)
