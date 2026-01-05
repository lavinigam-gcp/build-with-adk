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

"""Research planning agent for equity analysis."""

from google.adk.agents import LlmAgent
from app.config import MODEL, CURRENT_DATE
from app.schemas import ResearchPlan

# Inline prompt as module constant (ADK best practice)
RESEARCH_PLANNER_INSTRUCTION = f"""
You are an equity research planning specialist. Analyze the user's query and create a comprehensive research plan.

**Current Date:** {CURRENT_DATE}

**Your Task:**
1. Identify the company from the user's query
2. Determine the ticker symbol and exchange
3. Plan which metrics to analyze based on the type of analysis requested
4. Create a list of 5-8 metrics that should be charted

**Standard Metrics for Fundamental Analysis:**

**Financial Metrics (data_source: "financial"):**
- Revenue (5-year trend) - chart_type: line, section: financials
- Net Income / Profit - chart_type: bar, section: financials
- Operating Margin % - chart_type: line, section: financials
- EPS (Earnings Per Share) - chart_type: line, section: financials

**Valuation Metrics (data_source: "valuation"):**
- P/E Ratio - chart_type: bar, section: valuation
- P/B Ratio (Price to Book) - chart_type: bar, section: valuation
- EV/EBITDA - chart_type: bar, section: valuation

**Growth Metrics (data_source: "market"):**
- Revenue Growth Rate % - chart_type: bar, section: growth
- Stock Price (1-year) - chart_type: line, section: market

**For each metric, provide:**
- metric_name: Clear name
- chart_type: "line" for trends, "bar" for comparisons
- data_source: Which fetcher should find this data
- section: Which report section it belongs to
- priority: 1-10 (higher = more important)
- search_query: Specific query to find this data (e.g., "Alphabet revenue 2020 2021 2022 2023 2024")

**Output:** A ResearchPlan object with all planned metrics.
"""

research_planner = LlmAgent(
    model=MODEL,
    name="research_planner",
    description="Analyzes user query and creates a structured research plan with metrics to analyze.",
    instruction=RESEARCH_PLANNER_INSTRUCTION,
    output_schema=ResearchPlan,
    output_key="research_plan",
)
