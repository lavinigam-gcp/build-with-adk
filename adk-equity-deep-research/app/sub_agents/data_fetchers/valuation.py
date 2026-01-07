# Copyright 2025 Google LLC
# Licensed under the Apache License, Version 2.0

"""Valuation data fetcher agent."""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from app.config import MODEL, CURRENT_DATE

VALUATION_DATA_FETCHER_INSTRUCTION = f"""
You are a valuation analyst. Fetch valuation metrics for the company.

**Current Date:** {CURRENT_DATE}

**Research Plan:** {{{{enhanced_research_plan}}}}

**Your Task:**
1. Search for valuation ratios: P/E, P/B, P/S, EV/EBITDA
2. Find current values and historical comparisons
3. Compare to industry averages if available
4. Look for analyst price targets

**Search Strategy:**
- "[Company] P/E ratio current"
- "[Company] valuation multiples"
- "[Company] EV EBITDA"
- "[Company] analyst price target"

**Output:**
Provide valuation data including:
- Current ratios with dates
- Historical values for comparison
- Industry benchmarks if found
- Analyst ratings summary
"""

valuation_data_fetcher = LlmAgent(
    model=MODEL,
    name="valuation_data_fetcher",
    description="Fetches valuation metrics (P/E, P/B, EV/EBITDA, fair value).",
    instruction=VALUATION_DATA_FETCHER_INSTRUCTION,
    tools=[google_search],
    output_key="valuation_data",
)
