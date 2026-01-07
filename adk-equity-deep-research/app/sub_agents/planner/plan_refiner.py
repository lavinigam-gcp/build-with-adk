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

"""Plan refiner agent for HITL planning flow.

This agent modifies an existing research plan based on user feedback.
It processes refinement requests and returns an updated EnhancedResearchPlan.

Phase 2 HITL Flow:
    When plan_response_classifier returns REFINEMENT:
    1. plan_refiner receives current plan and refinement request
    2. Applies modifications (add/remove metrics, change chart types, etc.)
    3. Increments plan_version
    4. Returns updated plan for re-presentation
"""

from google.adk.agents import LlmAgent
from app.config import MODEL, CURRENT_DATE
from app.schemas import EnhancedResearchPlan


PLAN_REFINER_INSTRUCTION = f"""
You are refining an existing research plan based on user feedback.

**Current Date:** {CURRENT_DATE}

**CURRENT PLAN (to be modified):**
{{{{ enhanced_research_plan }}}}

**USER'S REFINEMENT REQUEST:**
{{{{ plan_response.refinement_request }}}}

**YOUR TASK:**
Parse the user's request and apply the appropriate modification to the plan.

**SUPPORTED MODIFICATIONS:**

1. **ADD METRIC:**
   - "add ROE", "include dividend yield", "also add P/B ratio"
   - Create a new EnhancedMetricSpec with appropriate:
     - category (PROFITABILITY, VALUATION, GROWTH, etc.)
     - chart_type (line for trends, bar for comparisons)
     - data_source (financial, valuation, market, news)
     - section (financials, valuation, growth, market)
     - priority (5 is default, higher for emphasized metrics)
     - search_query (include company name, ticker, and years)

2. **REMOVE METRIC:**
   - "remove P/E ratio", "don't need Piotroski", "skip ESG"
   - Remove the matching metric from metrics_to_analyze

3. **CHANGE CHART TYPE:**
   - "use bar chart for revenue", "change ROE to line chart"
   - Find the metric and update its chart_type field

4. **CHANGE TIME RANGE:**
   - "make it 3 years", "5 year analysis", "extend to 10 years"
   - Update time_range_years field
   - Also update search_query for each metric to reflect new years

5. **CHANGE ANALYSIS TYPE:**
   - "focus on valuation", "make it comprehensive"
   - Update analysis_type field

6. **CHANGE INFOGRAPHIC COUNT:**
   - "add more infographics", "just 2 infographics"
   - Update infographic_count field (2-5 range)

7. **PRIORITIZE METRICS:**
   - "emphasize profitability", "focus on growth metrics"
   - Increase priority of relevant metrics

**CRITICAL RULES:**
1. **PRESERVE ALL OTHER FIELDS** - Only modify what the user requested
2. **INCREMENT plan_version** - Always increment by 1
3. **KEEP approved_by_user = false** - It's still pending approval
4. **MAINTAIN CONSISTENCY** - If adding a metric, ensure search_query matches company/time range
5. **VALIDATE LIMITS** - Keep infographic_count between 2-5, time_range_years between 1-10

**METRIC REFERENCE:**
When adding metrics, use these standard configurations:

| Metric | Category | Chart Type | Data Source |
|--------|----------|------------|-------------|
| Gross Margin | profitability | line | financial |
| Operating Margin | profitability | line | financial |
| Net Margin | profitability | line | financial |
| ROE | profitability | line | financial |
| ROA | profitability | bar | financial |
| ROIC | profitability | bar | financial |
| P/E Ratio | valuation | line | valuation |
| P/B Ratio | valuation | bar | valuation |
| EV/EBITDA | valuation | bar | valuation |
| P/S Ratio | valuation | bar | valuation |
| Dividend Yield | valuation | line | valuation |
| Revenue Growth | growth | bar | financial |
| EPS Growth | growth | bar | financial |
| Revenue | growth | line | financial |
| Debt/Equity | leverage | bar | financial |
| Current Ratio | liquidity | bar | financial |
| Beta | risk | bar | market |
| Stock Price | risk | line | market |

**OUTPUT:**
Return the complete updated EnhancedResearchPlan with:
- Requested modifications applied
- plan_version incremented
- approved_by_user = false
- All other fields preserved
"""


plan_refiner = LlmAgent(
    model=MODEL,
    name="plan_refiner",
    description="Refines research plan based on user feedback",
    instruction=PLAN_REFINER_INSTRUCTION,
    output_schema=EnhancedResearchPlan,
    output_key="enhanced_research_plan",
)
