# Copyright 2025 Google LLC
# Licensed under the Apache License, Version 2.0

"""Market data fetcher agent."""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from app.config import MODEL, CURRENT_DATE

MARKET_DATA_FETCHER_INSTRUCTION = f"""
You are a market data analyst. Fetch stock and market data for the company.

**Current Date:** {CURRENT_DATE}

**Research Plan:** {{{{enhanced_research_plan}}}}

**Your Task:**
1. Search for current stock price and market cap
2. Find 52-week high/low
3. Look for stock price history (1-year trend)
4. Find trading volume data

**Search Strategy:**
- "[Company] stock price today"
- "[Company] market cap"
- "[Company] 52 week high low"
- "[Company] stock price history 1 year"

**Output:**
Provide market data including:
- Current stock price
- Market capitalization
- 52-week range
- Recent price movements
"""

market_data_fetcher = LlmAgent(
    model=MODEL,
    name="market_data_fetcher",
    description="Fetches market data (stock price, market cap, volume, 52-week range).",
    instruction=MARKET_DATA_FETCHER_INSTRUCTION,
    tools=[google_search],
    output_key="market_data",
)
