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

"""Templatized boundary configuration for query rejection.

Users can easily add, modify, or delete rejection rules by editing this file.
Each rule has:
- type: Category name for the rejection
- keywords: List of keywords that trigger rejection
- rejection_message: Message to show when rejecting

To add a new boundary:
1. Add a new dict to UNSUPPORTED_QUERY_TYPES with type, keywords, rejection_message
2. The system will automatically reject queries containing any of the keywords
"""

from __future__ import annotations

# Rejection rules - each rule has type, keywords, and rejection message
UNSUPPORTED_QUERY_TYPES: list[dict[str, str | list[str]]] = [
    {
        "type": "crypto",
        "keywords": [
            "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
            "nft", "defi", "blockchain token", "altcoin", "dogecoin", "solana",
            "binance coin", "bnb", "cardano", "polkadot", "ripple", "xrp",
        ],
        "rejection_message": "Cryptocurrency and blockchain token analysis is not supported.",
    },
    {
        "type": "trading_advice",
        "keywords": [
            "should i buy", "should i sell", "buy now", "sell now",
            "trading signal", "entry point", "exit point", "stop loss",
            "when to buy", "when to sell", "is it a good time",
            "target price", "price target", "will it go up", "will it go down",
        ],
        "rejection_message": "Real-time trading advice and buy/sell recommendations are not provided.",
    },
    {
        "type": "private_company",
        "keywords": [
            "private company", "startup valuation", "pre-ipo", "unlisted company",
            "private equity", "venture capital valuation", "series a", "series b",
            "seed funding", "angel investment",
        ],
        "rejection_message": "Private company analysis requires public financials which are not available.",
    },
    {
        "type": "personal_finance",
        "keywords": [
            "my portfolio", "my investment", "my stocks", "personal finance",
            "retirement planning", "my 401k", "my savings", "should i invest",
            "my ira", "my pension", "my money", "how much should i",
        ],
        "rejection_message": "Personal financial advice is not provided. Please consult a financial advisor.",
    },
    {
        "type": "non_financial",
        "keywords": [
            "weather", "recipe", "travel", "sports score", "movie review",
            "restaurant", "hotel", "flight booking", "news about politics",
            "celebrity", "entertainment", "music", "game",
        ],
        "rejection_message": "This system only handles equity research queries for listed companies.",
    },
    {
        "type": "penny_stocks",
        "keywords": [
            "penny stock", "otc market", "pink sheets", "otc stocks",
            "micro cap under $1", "sub-penny", "pump and dump",
        ],
        "rejection_message": "Penny stocks and OTC market securities are not supported due to limited data availability.",
    },
]

# What the system CAN do - shown when rejecting queries
SYSTEM_CAPABILITIES: str = """
This equity research system can help you with:

**Supported Analysis Types:**
- Comprehensive equity research for listed companies
- Fundamental analysis (revenue, margins, profitability)
- Valuation analysis (P/E, P/B, EV/EBITDA)
- Growth analysis (revenue growth, EPS trends)
- Company comparison (e.g., "Compare Apple vs Microsoft")
- Sector analysis (e.g., "Analyze US tech sector")

**Supported Markets:**
- United States (NYSE, NASDAQ)
- India (NSE, BSE)
- China (SSE, SZSE, HKEX)
- Japan (TSE)
- South Korea (KRX, KOSDAQ)
- Europe (LSE, Euronext, XETRA)

**Example Queries:**
- "Comprehensive analysis of Apple stock"
- "Fundamental analysis of Reliance Industries"
- "Compare Tesla vs Rivian on profitability"
- "Analyze Indian IT sector"
- "Valuation analysis of Toyota with 3-year data"
"""


def check_query_boundaries(query: str) -> tuple[bool, str | None]:
    """Check if query violates any boundary rules.

    Args:
        query: User's query string

    Returns:
        Tuple of (is_valid, rejection_message)
        - (True, None) if query is valid
        - (False, message) if query should be rejected
    """
    query_lower = query.lower()

    for rule in UNSUPPORTED_QUERY_TYPES:
        keywords = rule.get("keywords", [])
        if isinstance(keywords, list):
            for keyword in keywords:
                if isinstance(keyword, str) and keyword.lower() in query_lower:
                    return False, str(rule.get("rejection_message", "Query not supported."))

    return True, None
