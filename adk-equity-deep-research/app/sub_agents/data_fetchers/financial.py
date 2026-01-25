# Copyright 2025 Google LLC
# Licensed under the Apache License, Version 2.0

"""Financial data fetcher agent.

Uses yfinance for reliable, structured financial data with google_search
as fallback for metrics not available in Yahoo Finance.
"""

from google.adk.agents import LlmAgent
from google.adk.tools.google_search_tool import GoogleSearchTool
from app.config import MODEL, CURRENT_DATE
from app.tools.yfinance_tools import get_financial_statements

# Use bypass_multi_tools_limit=True to allow mixing with custom function tools
google_search = GoogleSearchTool(bypass_multi_tools_limit=True)

FINANCIAL_DATA_FETCHER_INSTRUCTION = f"""
You are a financial data researcher. Fetch financial performance data for the company.

**Current Date:** {CURRENT_DATE}

**Research Plan:** {{{{enhanced_research_plan}}}}

## Your Task

1. **Extract ticker** from the enhanced_research_plan
2. **Use get_financial_statements** tool to fetch structured financial data
3. **Use google_search** ONLY for metrics not available in yfinance (e.g., market-specific KPIs, ESG data, promoter holdings)

## Primary Tool: get_financial_statements

Call this tool first with the ticker from the research plan:
- It returns: Revenue, Net Income, Gross Profit, Operating Income, EBITDA, EPS, Margins
- Data is structured with periods, values, and units
- Covers the last 4-5 years of annual data

Example usage:
- For Apple: get_financial_statements(ticker="AAPL", years=5)
- For Reliance (India): get_financial_statements(ticker="RELIANCE.NS", years=5)
- For Toyota (Japan): get_financial_statements(ticker="7203.T", years=5)

## Fallback: google_search

Use google_search ONLY when:
- The yfinance tool returns an error
- You need metrics not in yfinance (segment breakdown, regional data, etc.)
- The research plan requests market-specific data

## Output Format

Present the data in a structured format:
1. **Revenue History**: List values by year with currency
2. **Net Income History**: List values by year
3. **Margins**: Net margin, operating margin percentages
4. **EPS**: Earnings per share history
5. **Data Source**: Indicate whether data is from yfinance or google search

Example output structure:
```
FINANCIAL DATA FOR [COMPANY] ([TICKER])
Data Source: Yahoo Finance (yfinance)

REVENUE (in B USD):
- 2024: 385.60
- 2023: 394.33
- 2022: 365.82
- 2021: 274.52

NET INCOME (in B USD):
- 2024: 93.74
- 2023: 96.99
- 2022: 99.80
- 2021: 94.68

NET MARGIN:
- 2024: 24.3%
- 2023: 24.6%
...
```

Be thorough - this data will be extracted for charting.
"""

financial_data_fetcher = LlmAgent(
    model=MODEL,
    name="financial_data_fetcher",
    description="Fetches financial performance data (revenue, profit, margins, EPS) using yfinance with google_search fallback.",
    instruction=FINANCIAL_DATA_FETCHER_INSTRUCTION,
    tools=[get_financial_statements, google_search],
    output_key="financial_data",
)
