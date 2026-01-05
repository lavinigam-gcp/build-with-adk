# Copyright 2025 Google LLC
# Licensed under the Apache License, Version 2.0

"""Financial data fetcher agent."""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from app.config import MODEL, CURRENT_DATE

FINANCIAL_DATA_FETCHER_INSTRUCTION = f"""
You are a financial data researcher. Fetch financial performance data for the company.

**Current Date:** {CURRENT_DATE}

**Research Plan:** {{{{research_plan}}}}

**Your Task:**
1. Look at the research_plan to identify the company
2. Search for financial metrics: Revenue, Net Income, Operating Margin, EPS
3. Find data for the last 5 years if available
4. Include quarterly data if relevant

**Search Strategy:**
- "[Company] annual revenue 2020 2021 2022 2023 2024"
- "[Company] quarterly earnings report"
- "[Company] profit margin history"
- "[Company] EPS earnings per share history"

**Output:**
Provide comprehensive data with:
- All numeric values with time periods
- Sources of information
- Any notable trends or changes

Be thorough - this data will be extracted for charting.
"""

financial_data_fetcher = LlmAgent(
    model=MODEL,
    name="financial_data_fetcher",
    description="Fetches financial performance data (revenue, profit, margins, EPS).",
    instruction=FINANCIAL_DATA_FETCHER_INSTRUCTION,
    tools=[google_search],
    output_key="financial_data",
)
