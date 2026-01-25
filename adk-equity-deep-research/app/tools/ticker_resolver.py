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

"""Ticker resolution utilities for converting company names to Yahoo Finance tickers."""

from functools import lru_cache
from typing import Optional

import yfinance as yf


# =============================================================================
# Known Ticker Mappings (Fallback)
# =============================================================================

# Common company name to ticker mappings for major international markets
KNOWN_TICKERS = {
    # US - Major Tech
    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "amazon": "AMZN",
    "meta": "META",
    "facebook": "META",
    "nvidia": "NVDA",
    "tesla": "TSLA",

    # US - Finance
    "jpmorgan": "JPM",
    "goldman sachs": "GS",
    "bank of america": "BAC",
    "berkshire hathaway": "BRK-B",

    # India - Major Companies
    "reliance industries": "RELIANCE.NS",
    "reliance": "RELIANCE.NS",
    "tata consultancy": "TCS.NS",
    "tcs": "TCS.NS",
    "infosys": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS",
    "icici bank": "ICICIBANK.NS",
    "wipro": "WIPRO.NS",
    "bharti airtel": "BHARTIARTL.NS",
    "itc": "ITC.NS",
    "hindustan unilever": "HINDUNILVR.NS",
    "maruti suzuki": "MARUTI.NS",
    "asian paints": "ASIANPAINT.NS",

    # Japan
    "toyota": "7203.T",
    "toyota motor": "7203.T",
    "sony": "6758.T",
    "sony group": "6758.T",
    "honda": "7267.T",
    "softbank": "9984.T",
    "nintendo": "7974.T",
    "keyence": "6861.T",
    "mitsubishi": "8058.T",

    # Korea
    "samsung electronics": "005930.KS",
    "samsung": "005930.KS",
    "sk hynix": "000660.KS",
    "hyundai motor": "005380.KS",
    "lg electronics": "066570.KS",
    "naver": "035420.KS",
    "kakao": "035720.KS",

    # Europe
    "asml": "ASML.AS",
    "nestle": "NESN.SW",
    "lvmh": "MC.PA",
    "sap": "SAP.DE",
    "siemens": "SIE.DE",
    "unilever": "ULVR.L",
    "astrazeneca": "AZN.L",
    "shell": "SHEL.L",
    "novartis": "NOVN.SW",
    "roche": "ROG.SW",

    # China / Hong Kong
    "alibaba": "9988.HK",
    "tencent": "0700.HK",
    "meituan": "3690.HK",
    "jd.com": "9618.HK",
    "byd": "1211.HK",
    "xiaomi": "1810.HK",
    "baidu": "9888.HK",
}

# Market-specific suffixes for Yahoo Finance
MARKET_SUFFIXES = {
    "US": "",
    "India": ".NS",      # NSE (default), .BO for BSE
    "Japan": ".T",       # Tokyo Stock Exchange
    "Korea": ".KS",      # KRX (default), .KQ for KOSDAQ
    "Europe": "",        # Varies: .L (London), .DE (Frankfurt), .PA (Paris), .AS (Amsterdam)
    "UK": ".L",
    "Germany": ".DE",
    "France": ".PA",
    "Netherlands": ".AS",
    "Switzerland": ".SW",
    "China": ".HK",      # Hong Kong listings more accessible
    "Hong Kong": ".HK",
    "Australia": ".AX",
    "Canada": ".TO",
    "Brazil": ".SA",
}


def _validate_ticker(ticker: str) -> bool:
    """Check if ticker exists in Yahoo Finance.

    Args:
        ticker: Yahoo Finance ticker symbol

    Returns:
        True if valid ticker, False otherwise
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        # Check for valid response (has price data)
        return info.get("regularMarketPrice") is not None or info.get("previousClose") is not None
    except Exception:
        return False


@lru_cache(maxsize=100)
def resolve_ticker(company_name: str, market: str = "US") -> dict:
    """Resolve company name to Yahoo Finance ticker symbol.

    Uses a multi-stage resolution strategy:
    1. Check if input is already a valid ticker
    2. Look up in known mappings
    3. Use yfinance search functionality
    4. Fall back to input + market suffix

    Args:
        company_name: Company name or ticker symbol (e.g., "Apple", "AAPL", "Reliance Industries")
        market: Market region ("US", "India", "Japan", "Korea", "Europe", etc.)

    Returns:
        dict with keys:
            - ticker: Resolved Yahoo Finance ticker
            - validated: True if ticker was validated against Yahoo Finance
            - warning: Optional warning message if validation failed
            - company_name: Original input
            - market: Market region
    """
    original_input = company_name.strip()
    normalized = original_input.lower().strip()

    # Step 1: Check if already a valid ticker (with market suffix if needed)
    test_ticker = original_input.upper()
    if market != "US" and "." not in test_ticker:
        test_ticker_with_suffix = test_ticker + MARKET_SUFFIXES.get(market, "")
    else:
        test_ticker_with_suffix = test_ticker

    if _validate_ticker(test_ticker_with_suffix):
        return {
            "ticker": test_ticker_with_suffix,
            "validated": True,
            "company_name": original_input,
            "market": market
        }

    # Also try without suffix for US tickers
    if _validate_ticker(test_ticker):
        return {
            "ticker": test_ticker,
            "validated": True,
            "company_name": original_input,
            "market": market
        }

    # Step 2: Check known mappings
    if normalized in KNOWN_TICKERS:
        ticker = KNOWN_TICKERS[normalized]
        return {
            "ticker": ticker,
            "validated": True,  # Known mappings are pre-validated
            "company_name": original_input,
            "market": market
        }

    # Step 3: Use yfinance search
    try:
        search_results = yf.Search(company_name, max_results=5)
        quotes = getattr(search_results, 'quotes', [])

        if quotes:
            # Filter by market preference
            for quote in quotes:
                symbol = quote.get("symbol", "")
                quote_market = quote.get("exchange", "")

                # Match market-specific tickers
                if market == "US" and "." not in symbol:
                    return {
                        "ticker": symbol,
                        "validated": True,
                        "company_name": original_input,
                        "market": market
                    }
                elif market == "India" and symbol.endswith((".NS", ".BO")):
                    return {
                        "ticker": symbol,
                        "validated": True,
                        "company_name": original_input,
                        "market": market
                    }
                elif market == "Japan" and symbol.endswith(".T"):
                    return {
                        "ticker": symbol,
                        "validated": True,
                        "company_name": original_input,
                        "market": market
                    }
                elif market == "Korea" and symbol.endswith((".KS", ".KQ")):
                    return {
                        "ticker": symbol,
                        "validated": True,
                        "company_name": original_input,
                        "market": market
                    }

            # Return first result as fallback if no market-specific match
            first_symbol = quotes[0].get("symbol")
            if first_symbol:
                return {
                    "ticker": first_symbol,
                    "validated": True,
                    "company_name": original_input,
                    "market": market
                }

    except Exception:
        pass  # Fall through to fallback

    # Step 4: Fallback - construct ticker with market suffix
    fallback_ticker = original_input.upper().replace(" ", "")
    if market in MARKET_SUFFIXES and MARKET_SUFFIXES[market]:
        fallback_ticker += MARKET_SUFFIXES[market]

    return {
        "ticker": fallback_ticker,
        "validated": False,
        "warning": f"Ticker '{fallback_ticker}' not validated. Data may be unavailable.",
        "company_name": original_input,
        "market": market
    }


def get_ticker_info(ticker: str) -> Optional[dict]:
    """Get basic info for a ticker to verify it's valid.

    Args:
        ticker: Yahoo Finance ticker symbol

    Returns:
        dict with company info or None if invalid
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if info.get("regularMarketPrice") is None and info.get("previousClose") is None:
            return None

        return {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "currency": info.get("currency"),
            "exchange": info.get("exchange"),
        }
    except Exception:
        return None
