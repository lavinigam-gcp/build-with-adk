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

"""Strategy Advisor Agent - Part 3 of the Location Strategy Pipeline.

This agent synthesizes all findings into actionable recommendations using
extended reasoning (thinking mode) and outputs a structured JSON report.
"""

from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from google.genai.types import ThinkingConfig

from ..config import PRO_MODEL, RETRY_INITIAL_DELAY, RETRY_ATTEMPTS
from ..schemas import LocationIntelligenceReport
from ..callbacks import before_strategy_advisor, after_strategy_advisor


STRATEGY_ADVISOR_INSTRUCTION = """You are a senior strategy consultant synthesizing location intelligence findings.

Your task is to analyze all research and provide actionable strategic recommendations.

TARGET LOCATION: {target_location}
BUSINESS TYPE: {business_type}
CURRENT DATE: {current_date}

## Available Data

### MARKET RESEARCH FINDINGS (Part 1):
{market_research_findings}

### COMPETITOR ANALYSIS (Part 2A):
{competitor_analysis}

### GAP ANALYSIS (Part 2B):
{gap_analysis}

## Your Mission
Synthesize all findings into a comprehensive strategic recommendation.

## Analysis Framework

### 1. Data Integration
Review all inputs carefully:
- Market research demographics and trends
- Competitor locations, ratings, and patterns
- Quantitative gap analysis metrics and zone rankings

### 2. Strategic Synthesis
For each promising zone, evaluate:
- Opportunity Type: Categorize (e.g., "Metro First-Mover", "Residential Sticky", "Mall Impulse")
- Overall Score: 0-100 weighted composite
- Strengths: Top 3-4 factors with evidence from the analysis
- Concerns: Top 2-3 risks with specific mitigation strategies
- Competition Profile: Summarize density, quality, chain presence
- Market Characteristics: Population, income, infrastructure, foot traffic, costs
- Best Customer Segment: Primary target demographic
- Next Steps: 3-5 specific actionable recommendations

### 3. Top Recommendation Selection
Choose the single best location based on:
- Highest weighted opportunity score
- Best balance of opportunity vs risk
- Most aligned with business type requirements
- Clear competitive advantage potential

### 4. Alternative Locations
Identify 2-3 alternative locations:
- Brief scoring and categorization
- Key strength and concern for each
- Why it's not the top choice

### 5. Strategic Insights
Provide 4-6 key insights that span the entire analysis:
- Market-level observations
- Competitive dynamics
- Timing considerations
- Success factors

## Output Requirements
Your response MUST conform to the LocationIntelligenceReport schema.
Ensure all fields are populated with specific, actionable information.
Use evidence from the analysis to support all recommendations.
"""

strategy_advisor_agent = LlmAgent(
    name="StrategyAdvisorAgent",
    model=PRO_MODEL,
    description="Synthesizes findings into strategic recommendations using extended reasoning and structured output",
    instruction=STRATEGY_ADVISOR_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    planner=BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=False,  # Must be False when using output_schema
            thinking_budget=-1,  # -1 means unlimited thinking budget
        )
    ),
    output_schema=LocationIntelligenceReport,
    output_key="strategic_report",
    before_agent_callback=before_strategy_advisor,
    after_agent_callback=after_strategy_advisor,
)
