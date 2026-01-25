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

"""Tool functions for data fetching and infographic generation."""

from .infographic_tools import generate_infographic, generate_all_infographics
from .yfinance_tools import (
    get_financial_statements,
    get_valuation_metrics,
    get_market_data,
    get_analyst_data,
    is_yfinance_supported,
)
from .ticker_resolver import resolve_ticker, get_ticker_info

__all__ = [
    # Infographic tools
    "generate_infographic",
    "generate_all_infographics",
    # yfinance data tools
    "get_financial_statements",
    "get_valuation_metrics",
    "get_market_data",
    "get_analyst_data",
    "is_yfinance_supported",
    # Ticker resolution
    "resolve_ticker",
    "get_ticker_info",
]
