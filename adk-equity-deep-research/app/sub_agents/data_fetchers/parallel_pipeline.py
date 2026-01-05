# Copyright 2025 Google LLC
# Licensed under the Apache License, Version 2.0

"""Parallel data gathering pipeline - runs 4 fetchers concurrently."""

from google.adk.agents import ParallelAgent
from .financial import financial_data_fetcher
from .valuation import valuation_data_fetcher
from .market import market_data_fetcher
from .news import news_sentiment_fetcher

parallel_data_gatherers = ParallelAgent(
    name="parallel_data_gatherers",
    description="Fetches data from 4 sources concurrently (financial, valuation, market, news)",
    sub_agents=[
        financial_data_fetcher,
        valuation_data_fetcher,
        market_data_fetcher,
        news_sentiment_fetcher,
    ],
)
