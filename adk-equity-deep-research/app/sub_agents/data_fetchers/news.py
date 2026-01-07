# Copyright 2025 Google LLC
# Licensed under the Apache License, Version 2.0

"""News and sentiment fetcher agent."""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from app.config import MODEL, CURRENT_DATE

NEWS_SENTIMENT_FETCHER_INSTRUCTION = f"""
You are a news and sentiment analyst. Fetch recent news and analyst sentiment for the company.

**Current Date:** {CURRENT_DATE}

**Research Plan:** {{{{enhanced_research_plan}}}}

**Your Task:**
1. Search for recent news (last 3 months)
2. Find analyst ratings and recommendations
3. Look for major company announcements
4. Identify key risks and opportunities mentioned

**Search Strategy:**
- "[Company] news latest 2024"
- "[Company] analyst ratings"
- "[Company] stock news recent"
- "[Company] risks challenges"

**Output:**
Provide:
- Summary of recent news (3-5 key items)
- Analyst consensus rating
- Key risks mentioned in news
- Any catalysts or upcoming events
"""

news_sentiment_fetcher = LlmAgent(
    model=MODEL,
    name="news_sentiment_fetcher",
    description="Fetches recent news and analyst sentiment.",
    instruction=NEWS_SENTIMENT_FETCHER_INSTRUCTION,
    tools=[google_search],
    output_key="news_data",
)
