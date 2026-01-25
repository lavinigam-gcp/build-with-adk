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

"""Yahoo Finance data fetching tools for equity research.

This module provides structured, deterministic access to Yahoo Finance data
via the yfinance library. These tools replace unreliable google_search for
financial, valuation, and market data.

Tools:
    - get_financial_statements: Revenue, Net Income, Margins, EPS
    - get_valuation_metrics: P/E, P/B, P/S, EV/EBITDA, Market Cap
    - get_market_data: Stock price, 52-week range, volume, price history
    - get_analyst_data: Price targets, recommendations summary
"""

import time
from datetime import datetime
from functools import lru_cache, wraps
from typing import Any, Optional

import yfinance as yf

from .rate_limiter import YFINANCE_RATE_LIMITER, YFINANCE_SEMAPHORE


# =============================================================================
# Supported Metrics (for hybrid fallback logic)
# =============================================================================

YFINANCE_SUPPORTED_METRICS = {
    # Financial Statement Metrics
    "Revenue", "Net Income", "Gross Profit", "Operating Income",
    "EBITDA", "EPS", "Gross Margin", "Operating Margin", "Net Margin",
    # Balance Sheet Metrics
    "Total Assets", "Total Debt", "Total Equity", "Cash",
    "Current Ratio", "Debt to Equity",
    # Valuation Metrics
    "P/E Ratio", "Forward P/E", "P/B Ratio", "P/S Ratio",
    "EV/EBITDA", "Market Cap", "Enterprise Value",
    # Market Data
    "Stock Price", "52-Week High", "52-Week Low", "Volume",
    # Analyst Data
    "Analyst Price Target", "Analyst Recommendations",
}


def is_yfinance_supported(metric_name: str) -> bool:
    """Check if a metric can be fetched from yfinance.

    Args:
        metric_name: Name of the metric to check

    Returns:
        True if metric is supported by yfinance tools
    """
    normalized = metric_name.lower().replace("_", " ").replace("-", " ")
    return any(
        supported.lower() in normalized or normalized in supported.lower()
        for supported in YFINANCE_SUPPORTED_METRICS
    )


# =============================================================================
# Retry Decorator with Rate Limiting
# =============================================================================

def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for exponential backoff on errors with rate limiting.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries (doubles each attempt)

    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        @wraps(func)
        def wrapper(ticker: str, *args, **kwargs):
            last_error = None

            for attempt in range(max_retries):
                try:
                    # Acquire rate limiter and semaphore
                    with YFINANCE_SEMAPHORE:
                        YFINANCE_RATE_LIMITER.acquire()
                        return func(ticker, *args, **kwargs)

                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)

            # All retries exhausted
            return {
                "error": f"Failed after {max_retries} attempts: {str(last_error)}",
                "ticker": ticker
            }

        return wrapper
    return decorator


# =============================================================================
# Cache Key Generation
# =============================================================================

def _get_cache_key() -> str:
    """Generate hourly cache key for LRU cache.

    Financial data doesn't change frequently, so we cache for 1 hour.
    """
    return datetime.now().strftime("%Y-%m-%d-%H")


@lru_cache(maxsize=50)
def _get_cached_ticker(ticker: str, cache_key: str) -> yf.Ticker:
    """Get cached Ticker object.

    Args:
        ticker: Stock ticker symbol
        cache_key: Hourly cache key for TTL

    Returns:
        yfinance Ticker object
    """
    return yf.Ticker(ticker)


# =============================================================================
# Tool 1: Financial Statements
# =============================================================================

@with_retry(max_retries=3)
def get_financial_statements(ticker: str, years: int = 5) -> dict:
    """Fetch financial statement data from Yahoo Finance.

    Retrieves income statement data including revenue, net income, margins,
    and earnings per share for the specified number of years.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "RELIANCE.NS")
        years: Number of years of historical data (default: 5, max: ~4 annual)

    Returns:
        dict with keys:
            - ticker: The ticker symbol
            - currency: Reporting currency
            - revenue: List of {period, value, unit} dicts
            - net_income: List of {period, value, unit} dicts
            - gross_profit: List of {period, value, unit} dicts
            - operating_income: List of {period, value, unit} dicts
            - ebitda: List of {period, value, unit} dicts
            - eps_basic: Basic EPS values
            - eps_diluted: Diluted EPS values
            - margins: Computed margin ratios
            - error: Error message if data unavailable
    """
    cache_key = _get_cache_key()
    stock = _get_cached_ticker(ticker, cache_key)

    try:
        income = stock.income_stmt
        info = stock.info

        if income is None or income.empty:
            return {
                "ticker": ticker,
                "error": "No income statement data available",
                "data_available": False
            }

        currency = info.get("currency", "USD")

        # Helper to extract time series data
        def extract_metric(
            df,
            row_names: list[str],
            years_limit: int,
            scale: float = 1e9
        ) -> list[dict]:
            """Extract metric from DataFrame with fallback row names."""
            result = []

            # Find the first matching row name
            actual_row = None
            for name in row_names:
                if name in df.index:
                    actual_row = name
                    break

            if actual_row is None:
                return result

            for col in list(df.columns)[:years_limit]:
                try:
                    value = df.loc[actual_row, col]
                    if value is not None and not (isinstance(value, float) and value != value):  # NaN check
                        period = col.strftime("%Y") if hasattr(col, 'strftime') else str(col)[:4]
                        result.append({
                            "period": period,
                            "value": round(float(value) / scale, 2),
                            "unit": f"B {currency}"
                        })
                except Exception:
                    continue

            return result

        # Extract key metrics
        result = {
            "ticker": ticker,
            "currency": currency,
            "data_available": True,
            "revenue": extract_metric(
                income,
                ["Total Revenue", "Revenue", "Operating Revenue"],
                years
            ),
            "net_income": extract_metric(
                income,
                ["Net Income", "Net Income Common Stockholders", "Net Income From Continuing Operations"],
                years
            ),
            "gross_profit": extract_metric(
                income,
                ["Gross Profit"],
                years
            ),
            "operating_income": extract_metric(
                income,
                ["Operating Income", "Operating Profit"],
                years
            ),
            "ebitda": extract_metric(
                income,
                ["EBITDA", "Normalized EBITDA"],
                years
            ),
        }

        # Extract EPS (different scale - no division by billions)
        eps_data = []
        for row_name in ["Basic EPS", "Diluted EPS"]:
            if row_name in income.index:
                for col in list(income.columns)[:years]:
                    try:
                        value = income.loc[row_name, col]
                        if value is not None and not (isinstance(value, float) and value != value):
                            period = col.strftime("%Y") if hasattr(col, 'strftime') else str(col)[:4]
                            eps_data.append({
                                "period": period,
                                "value": round(float(value), 2),
                                "type": row_name,
                                "unit": currency
                            })
                    except Exception:
                        continue
                break  # Use first available EPS type

        result["eps"] = eps_data

        # Compute margins if we have revenue and income
        margins = []
        if result["revenue"] and result["net_income"]:
            for rev, ni in zip(result["revenue"], result["net_income"]):
                if rev["period"] == ni["period"] and rev["value"] > 0:
                    net_margin = round((ni["value"] / rev["value"]) * 100, 1)
                    margins.append({
                        "period": rev["period"],
                        "net_margin_pct": net_margin
                    })
        result["margins"] = margins

        return result

    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
            "data_available": False
        }


# =============================================================================
# Tool 2: Valuation Metrics
# =============================================================================

@with_retry(max_retries=3)
def get_valuation_metrics(ticker: str) -> dict:
    """Fetch current valuation ratios from Yahoo Finance.

    Retrieves key valuation multiples including P/E, P/B, P/S, EV/EBITDA,
    and market capitalization.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "RELIANCE.NS")

    Returns:
        dict with keys:
            - ticker: The ticker symbol
            - pe_ratio: Trailing P/E ratio
            - forward_pe: Forward P/E ratio
            - pb_ratio: Price to Book ratio
            - ps_ratio: Price to Sales ratio
            - ev_ebitda: Enterprise Value to EBITDA
            - market_cap: Market capitalization (formatted)
            - enterprise_value: Enterprise value (formatted)
            - dividend_yield: Dividend yield percentage
            - peg_ratio: PEG ratio
            - error: Error message if data unavailable
    """
    cache_key = _get_cache_key()
    stock = _get_cached_ticker(ticker, cache_key)

    try:
        info = stock.info

        if not info or info.get("regularMarketPrice") is None:
            return {
                "ticker": ticker,
                "error": "No valuation data available",
                "data_available": False
            }

        currency = info.get("currency", "USD")

        def format_large_number(value: Optional[float], currency: str = "USD") -> Optional[dict]:
            """Format large numbers with appropriate scale."""
            if value is None:
                return None
            if value >= 1e12:
                return {"value": round(value / 1e12, 2), "unit": f"T {currency}"}
            elif value >= 1e9:
                return {"value": round(value / 1e9, 2), "unit": f"B {currency}"}
            elif value >= 1e6:
                return {"value": round(value / 1e6, 2), "unit": f"M {currency}"}
            else:
                return {"value": round(value, 2), "unit": currency}

        return {
            "ticker": ticker,
            "currency": currency,
            "data_available": True,
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "ev_revenue": info.get("enterpriseToRevenue"),
            "market_cap": format_large_number(info.get("marketCap"), currency),
            "enterprise_value": format_large_number(info.get("enterpriseValue"), currency),
            "dividend_yield": (
                round(info.get("dividendYield", 0), 2)
                if info.get("dividendYield")
                else None
            ),
            "peg_ratio": info.get("pegRatio"),
            "beta": info.get("beta"),
            "trailing_eps": info.get("trailingEps"),
            "forward_eps": info.get("forwardEps"),
            "book_value": info.get("bookValue"),
        }

    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
            "data_available": False
        }


# =============================================================================
# Tool 3: Market Data
# =============================================================================

@with_retry(max_retries=3)
def get_market_data(ticker: str, history_period: str = "1y") -> dict:
    """Fetch market data and price history from Yahoo Finance.

    Retrieves current stock price, market cap, 52-week range, volume,
    and historical price data.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "RELIANCE.NS")
        history_period: Period for price history ("1mo", "3mo", "6mo", "1y", "2y")

    Returns:
        dict with keys:
            - ticker: The ticker symbol
            - current_price: Current stock price
            - currency: Price currency
            - market_cap: Market capitalization
            - fifty_two_week_high: 52-week high price
            - fifty_two_week_low: 52-week low price
            - fifty_two_week_change: Percentage change over 52 weeks
            - avg_volume: Average trading volume
            - price_history: List of {date, open, high, low, close, volume} dicts
            - error: Error message if data unavailable
    """
    cache_key = _get_cache_key()
    stock = _get_cached_ticker(ticker, cache_key)

    try:
        info = stock.info
        hist = stock.history(period=history_period)

        if hist is None or hist.empty:
            return {
                "ticker": ticker,
                "error": "No market data available",
                "data_available": False
            }

        currency = info.get("currency", "USD")

        # Get fast_info for real-time data if available
        try:
            fast = stock.fast_info
            current_price = fast.last_price
            market_cap = fast.market_cap
            year_high = fast.year_high
            year_low = fast.year_low
        except Exception:
            # Fall back to info dict
            current_price = info.get("regularMarketPrice") or info.get("previousClose")
            market_cap = info.get("marketCap")
            year_high = info.get("fiftyTwoWeekHigh")
            year_low = info.get("fiftyTwoWeekLow")

        # Calculate 52-week change
        fifty_two_week_change = None
        if year_low and current_price and year_low > 0:
            fifty_two_week_change = round(((current_price - year_low) / year_low) * 100, 2)

        # Extract price history (sample to avoid huge payloads)
        # Get weekly data points for 1-year history
        price_history = []
        step = max(1, len(hist) // 52)  # ~52 data points for a year

        for idx in range(0, len(hist), step):
            row = hist.iloc[idx]
            date_val = hist.index[idx]
            price_history.append({
                "date": date_val.strftime("%Y-%m-%d") if hasattr(date_val, 'strftime') else str(date_val)[:10],
                "open": round(float(row.get("Open", 0)), 2),
                "high": round(float(row.get("High", 0)), 2),
                "low": round(float(row.get("Low", 0)), 2),
                "close": round(float(row.get("Close", 0)), 2),
                "volume": int(row.get("Volume", 0))
            })

        def format_large_number(value: Optional[float], currency: str = "USD") -> Optional[dict]:
            """Format large numbers with appropriate scale."""
            if value is None:
                return None
            if value >= 1e12:
                return {"value": round(value / 1e12, 2), "unit": f"T {currency}"}
            elif value >= 1e9:
                return {"value": round(value / 1e9, 2), "unit": f"B {currency}"}
            elif value >= 1e6:
                return {"value": round(value / 1e6, 2), "unit": f"M {currency}"}
            else:
                return {"value": round(value, 2), "unit": currency}

        return {
            "ticker": ticker,
            "currency": currency,
            "data_available": True,
            "current_price": round(current_price, 2) if current_price else None,
            "previous_close": info.get("previousClose"),
            "day_high": info.get("dayHigh"),
            "day_low": info.get("dayLow"),
            "market_cap": format_large_number(market_cap, currency),
            "fifty_two_week_high": round(year_high, 2) if year_high else None,
            "fifty_two_week_low": round(year_low, 2) if year_low else None,
            "fifty_two_week_change_pct": fifty_two_week_change,
            "avg_volume": info.get("averageVolume"),
            "avg_volume_10day": info.get("averageVolume10days"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "float_shares": info.get("floatShares"),
            "price_history": price_history,
            "price_history_period": history_period,
        }

    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
            "data_available": False
        }


# =============================================================================
# Tool 4: Analyst Data
# =============================================================================

@with_retry(max_retries=3)
def get_analyst_data(ticker: str) -> dict:
    """Fetch analyst recommendations and price targets from Yahoo Finance.

    Retrieves analyst price targets, recommendation summaries, and
    earnings estimates.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "RELIANCE.NS")

    Returns:
        dict with keys:
            - ticker: The ticker symbol
            - price_targets: Dict with current, low, high, mean, median
            - recommendations: Recommendation breakdown (buy/hold/sell)
            - recommendation_trend: Recent recommendation changes
            - target_mean_price: Mean analyst target price
            - current_price: Current stock price for comparison
            - upside_potential: Percentage upside to mean target
            - error: Error message if data unavailable
    """
    cache_key = _get_cache_key()
    stock = _get_cached_ticker(ticker, cache_key)

    try:
        info = stock.info
        currency = info.get("currency", "USD")
        current_price = info.get("regularMarketPrice") or info.get("previousClose")

        # Get analyst price targets
        price_targets = {}
        try:
            targets = stock.get_analyst_price_targets()
            if targets is not None:
                price_targets = {
                    "current": targets.get("current"),
                    "low": targets.get("low"),
                    "high": targets.get("high"),
                    "mean": targets.get("mean"),
                    "median": targets.get("median"),
                }
        except Exception:
            # Fallback to info dict
            price_targets = {
                "low": info.get("targetLowPrice"),
                "high": info.get("targetHighPrice"),
                "mean": info.get("targetMeanPrice"),
                "median": info.get("targetMedianPrice"),
            }

        # Get recommendations summary
        recommendations = {}
        try:
            recs = stock.get_recommendations_summary()
            if recs is not None and not recs.empty:
                # Convert DataFrame to dict
                for col in recs.columns:
                    if col != 'period':
                        recommendations[col] = int(recs[col].sum())
        except Exception:
            pass

        # Calculate upside potential
        upside_potential = None
        mean_target = price_targets.get("mean") or info.get("targetMeanPrice")
        if mean_target and current_price and current_price > 0:
            upside_potential = round(((mean_target - current_price) / current_price) * 100, 2)

        # Get analyst recommendation
        recommendation_key = info.get("recommendationKey")  # e.g., "buy", "hold", "sell"
        recommendation_mean = info.get("recommendationMean")  # 1.0 (strong buy) to 5.0 (sell)
        number_of_analysts = info.get("numberOfAnalystOpinions")

        return {
            "ticker": ticker,
            "currency": currency,
            "data_available": True,
            "current_price": round(current_price, 2) if current_price else None,
            "price_targets": price_targets,
            "target_mean_price": mean_target,
            "upside_potential_pct": upside_potential,
            "recommendations": recommendations,
            "recommendation_key": recommendation_key,
            "recommendation_mean": recommendation_mean,  # 1=Strong Buy, 5=Sell
            "number_of_analysts": number_of_analysts,
            "earnings_estimate": {
                "current_year_eps": info.get("forwardEps"),
                "trailing_eps": info.get("trailingEps"),
            },
        }

    except Exception as e:
        return {
            "ticker": ticker,
            "error": str(e),
            "data_available": False
        }
