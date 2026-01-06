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

"""Templatized market configuration for multi-market support.

Users can add new markets or modify existing ones by editing this file.
Each market has:
- name: Display name of the market
- exchanges: List of stock exchanges
- currency: Currency code (USD, INR, etc.)
- currency_symbol: Currency symbol ($, etc.)
- major_indices: Major market indices
- specific_metrics: Market-specific metrics to include in reports

To add a new market:
1. Add a new entry to SUPPORTED_MARKETS with market code as key
2. Add detection hints to MARKET_DETECTION_HINTS
"""

from __future__ import annotations

SUPPORTED_MARKETS: dict[str, dict] = {
    "US": {
        "name": "United States",
        "exchanges": ["NYSE", "NASDAQ", "AMEX"],
        "currency": "USD",
        "currency_symbol": "$",
        "major_indices": ["S&P 500", "Dow Jones", "NASDAQ Composite"],
        "specific_metrics": [],  # Standard metrics apply
    },
    "India": {
        "name": "India",
        "exchanges": ["NSE", "BSE"],
        "currency": "INR",
        "currency_symbol": "\u20b9",  # Rupee symbol
        "major_indices": ["NIFTY 50", "SENSEX"],
        "specific_metrics": ["Promoter Holding %", "FII/DII Flows", "Promoter Pledge %"],
    },
    "China": {
        "name": "China",
        "exchanges": ["SSE", "SZSE", "HKEX"],
        "currency": "CNY",
        "currency_symbol": "\u00a5",  # Yuan symbol
        "major_indices": ["SSE Composite", "CSI 300", "Hang Seng"],
        "specific_metrics": ["State Ownership %", "A-Share vs H-Share Premium"],
    },
    "Japan": {
        "name": "Japan",
        "exchanges": ["TSE", "OSE"],
        "currency": "JPY",
        "currency_symbol": "\u00a5",  # Yen symbol
        "major_indices": ["Nikkei 225", "TOPIX"],
        "specific_metrics": ["Keiretsu Affiliation", "Cross-Shareholding %"],
    },
    "Korea": {
        "name": "South Korea",
        "exchanges": ["KRX", "KOSDAQ"],
        "currency": "KRW",
        "currency_symbol": "\u20a9",  # Won symbol
        "major_indices": ["KOSPI", "KOSDAQ"],
        "specific_metrics": ["Chaebol Affiliation", "Foreign Ownership Limit"],
    },
    "Europe": {
        "name": "Europe",
        "exchanges": ["LSE", "Euronext", "XETRA", "SIX"],
        "currency": "EUR",
        "currency_symbol": "\u20ac",  # Euro symbol
        "major_indices": ["FTSE 100", "DAX", "CAC 40", "Euro Stoxx 50"],
        "specific_metrics": ["ESG Compliance Score", "EU Taxonomy Alignment"],
    },
}

# Keywords that hint at specific markets
MARKET_DETECTION_HINTS: dict[str, list[str]] = {
    "US": [
        "nyse", "nasdaq", "american", "us stock", "wall street",
        "s&p 500", "dow jones", "us market", "united states",
        # Common US companies
        "apple", "microsoft", "google", "alphabet", "amazon", "meta", "tesla", "nvidia",
        "jpmorgan", "goldman sachs", "berkshire", "johnson & johnson", "visa",
        "mastercard", "walmart", "exxon", "chevron", "pfizer", "merck",
    ],
    "India": [
        "nse", "bse", "sensex", "nifty", "indian", "india stock", "india market",
        "mumbai stock", "bombay stock",
        # Common Indian companies
        "reliance", "tata", "infosys", "wipro", "hdfc", "icici", "bharti",
        "adani", "bajaj", "mahindra", "maruti", "itc", "hcl", "sbi",
        "kotak", "axis bank", "ultratech", "titan", "nestle india",
    ],
    "China": [
        "shanghai", "shenzhen", "hkex", "hong kong", "chinese", "china stock",
        "sse", "szse", "a-share", "h-share", "china market", "mainland china",
        # Common Chinese companies
        "alibaba", "tencent", "baidu", "jd.com", "pinduoduo", "nio", "byd",
        "xiaomi", "huawei", "lenovo", "meituan", "bytedance", "didi",
        "netease", "trip.com", "li auto", "xpeng",
    ],
    "Japan": [
        "tokyo", "tse", "nikkei", "topix", "japanese", "japan stock", "japan market",
        "tokyo stock",
        # Common Japanese companies
        "toyota", "sony", "honda", "nintendo", "softbank", "mitsubishi",
        "panasonic", "canon", "hitachi", "suzuki", "nissan", "mazda",
        "fast retailing", "uniqlo", "keyence", "daikin", "shin-etsu",
    ],
    "Korea": [
        "kospi", "kosdaq", "korean", "korea stock", "seoul", "korea market",
        "south korea", "korean stock",
        # Common Korean companies
        "samsung", "hyundai", "sk hynix", "lg", "kia", "posco", "naver",
        "kakao", "celltrion", "samsung biologics", "lg chem", "lg energy",
        "hyundai motor", "samsung sdi", "kb financial",
    ],
    "Europe": [
        "london", "lse", "euronext", "xetra", "european", "europe stock",
        "ftse", "dax", "cac", "stoxx", "europe market", "eu stock",
        "frankfurt", "paris", "amsterdam", "brussels", "swiss",
        # Common European companies
        "nestle", "shell", "asml", "lvmh", "sap", "siemens", "novartis",
        "astrazeneca", "unilever", "volkswagen", "bmw", "bp", "total",
        "roche", "hsbc", "ubs", "airbus", "mercedes", "bayer",
    ],
}


def get_market_by_hint(query: str) -> str | None:
    """Detect market from query using keyword hints.

    Args:
        query: User's query string

    Returns:
        Market code (US, India, China, etc.) or None if not detected
    """
    query_lower = query.lower()

    # Check each market's hints
    for market_code, hints in MARKET_DETECTION_HINTS.items():
        for hint in hints:
            if hint.lower() in query_lower:
                return market_code

    return None


def get_market_config(market_code: str) -> dict | None:
    """Get full configuration for a market.

    Args:
        market_code: Market code (US, India, etc.)

    Returns:
        Market configuration dict or None if not found
    """
    return SUPPORTED_MARKETS.get(market_code)


def is_market_supported(market_code: str) -> bool:
    """Check if a market is supported.

    Args:
        market_code: Market code to check

    Returns:
        True if market is supported, False otherwise
    """
    return market_code in SUPPORTED_MARKETS


def get_all_market_codes() -> list[str]:
    """Get list of all supported market codes.

    Returns:
        List of market codes (e.g., ["US", "India", "China", ...])
    """
    return list(SUPPORTED_MARKETS.keys())
