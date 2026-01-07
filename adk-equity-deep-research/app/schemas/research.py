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

"""Research planning and classification schemas."""

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


# =============================================================================
# PHASE 2: Enhanced Enums for HITL Planning
# =============================================================================

class MetricCategory(str, Enum):
    """Categories for professional equity metrics."""
    PROFITABILITY = "profitability"  # Margins, ROE, ROA, ROIC
    VALUATION = "valuation"          # P/E, P/B, EV/EBITDA
    LIQUIDITY = "liquidity"          # Current ratio, quick ratio
    LEVERAGE = "leverage"            # D/E, interest coverage
    EFFICIENCY = "efficiency"        # Asset turnover, inventory turnover
    GROWTH = "growth"                # Revenue growth, EPS growth
    QUALITY = "quality"              # Piotroski F-Score, Altman Z
    RISK = "risk"                    # Beta, volatility
    MARKET_SPECIFIC = "market_specific"  # Promoter %, State Ownership %, etc.


class AnalysisType(str, Enum):
    """Type of equity analysis to perform."""
    FUNDAMENTAL = "fundamental"
    VALUATION = "valuation"
    GROWTH = "growth"
    COMPREHENSIVE = "comprehensive"
    COMPARISON = "comparison"
    SECTOR = "sector"


class PlanResponseType(str, Enum):
    """Classification of user response to plan."""
    APPROVAL = "approval"      # "looks good", "proceed", "approved"
    REFINEMENT = "refinement"  # "add X", "remove Y", "change to bar chart"
    NEW_QUERY = "new_query"    # Different company or fresh analysis


# =============================================================================
# PHASE 1: Original Schemas (kept for backward compatibility)
# =============================================================================


class MetricSpec(BaseModel):
    """Specification for a single metric to analyze and chart."""

    metric_name: str = Field(
        description="Name of the metric (e.g., 'Revenue', 'P/E Ratio', 'Profit Margin')"
    )
    chart_type: Literal["line", "bar", "area"] = Field(
        default="line",
        description="Chart type: 'line' for trends, 'bar' for comparisons, 'area' for cumulative"
    )
    data_source: Literal["financial", "valuation", "market", "news"] = Field(
        description="Which parallel fetcher provides data for this metric"
    )
    section: Literal["financials", "valuation", "growth", "market"] = Field(
        description="Which report section this metric belongs to"
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Priority 1-10, higher = more important (determines chart order)"
    )
    search_query: str = Field(
        description="Specific search query to find data for this metric"
    )


class ResearchPlan(BaseModel):
    """Plan for the equity research report."""

    company_name: str = Field(
        description="Full company name (e.g., 'Alphabet Inc.')"
    )
    ticker: str = Field(
        description="Stock ticker symbol (e.g., 'GOOGL')"
    )
    exchange: str = Field(
        default="NASDAQ",
        description="Stock exchange (e.g., 'NASDAQ', 'NYSE', 'BSE')"
    )
    metrics_to_analyze: list[MetricSpec] = Field(
        description="List of metrics to analyze and chart (typically 5-8 metrics)"
    )
    report_sections: list[str] = Field(
        default=["overview", "financials", "valuation", "growth", "risks", "recommendation"],
        description="Sections to include in the final report"
    )


class QueryClassification(BaseModel):
    """Classification of user message as new query vs follow-up to previous query."""

    query_type: str = Field(
        description="Classification result: 'NEW_QUERY' or 'FOLLOW_UP'"
    )
    reasoning: str = Field(
        description="Brief explanation of why this classification was chosen"
    )
    detected_company: str = Field(
        default="",
        description="Company/stock ticker mentioned in message, if any"
    )
    detected_market: str = Field(
        default="US",
        description="Detected market: US, India, China, Japan, Korea, or Europe"
    )


# =============================================================================
# PHASE 2: Enhanced Schemas for HITL Planning
# =============================================================================

class EnhancedMetricSpec(BaseModel):
    """Enhanced metric specification with category and market awareness.

    Extends MetricSpec with professional categorization and market-specific flags.
    Used by the HITL planning flow for interactive plan presentation.
    """

    metric_name: str = Field(
        description="Name of the metric (e.g., 'Revenue', 'P/E Ratio', 'ROE')"
    )
    category: MetricCategory = Field(
        description="Category of the metric for grouping in the report"
    )
    chart_type: Literal["line", "bar", "area"] = Field(
        default="line",
        description="Chart type: 'line' for trends, 'bar' for comparisons, 'area' for cumulative"
    )
    data_source: Literal["financial", "valuation", "market", "news"] = Field(
        description="Which parallel fetcher provides data for this metric"
    )
    section: str = Field(
        description="Which report section this metric belongs to"
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Priority 1-10, higher = more important (determines chart order)"
    )
    search_query: str = Field(
        description="Specific search query to find data for this metric"
    )
    calculation_formula: str | None = Field(
        default=None,
        description="Optional formula for calculated metrics (e.g., 'Net Income / Revenue')"
    )
    is_market_specific: bool = Field(
        default=False,
        description="True if this is a market-specific metric (e.g., Promoter % for India)"
    )


class EnhancedResearchPlan(BaseModel):
    """Enhanced research plan with HITL support.

    This is the primary plan schema used in Phase 2 HITL flow.
    Contains market awareness, time range configuration, and approval tracking.
    """

    # Company info
    company_name: str = Field(
        description="Full company name (e.g., 'Apple Inc.')"
    )
    ticker: str = Field(
        description="Stock ticker symbol (e.g., 'AAPL')"
    )
    exchange: str = Field(
        default="NASDAQ",
        description="Stock exchange (e.g., 'NASDAQ', 'NYSE', 'NSE', 'BSE')"
    )
    market: str = Field(
        default="US",
        description="Market region: US, India, China, Japan, Korea, or Europe"
    )

    # Analysis configuration
    analysis_type: AnalysisType = Field(
        default=AnalysisType.COMPREHENSIVE,
        description="Type of analysis to perform"
    )
    time_range_years: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of years of historical data to analyze"
    )

    # Metrics (10-15 for comprehensive analysis)
    metrics_to_analyze: list[EnhancedMetricSpec] = Field(
        description="List of metrics to analyze and chart (typically 10-15 for comprehensive)"
    )

    # Report structure
    report_sections: list[str] = Field(
        default=["overview", "financials", "valuation", "growth", "risks", "recommendation"],
        description="Sections to include in the final report"
    )
    infographic_count: int = Field(
        default=3,
        ge=2,
        le=5,
        description="Number of AI-generated infographics to include (2-5)"
    )

    # HITL tracking
    plan_version: int = Field(
        default=1,
        ge=1,
        description="Version number, incremented on each refinement"
    )
    approved_by_user: bool = Field(
        default=False,
        description="True when user has explicitly approved the plan"
    )


class PlanResponseClassification(BaseModel):
    """Classification of user's response to the presented plan.

    Used by plan_response_classifier to determine next action:
    - APPROVAL: Proceed to execution
    - REFINEMENT: Modify plan based on feedback
    - NEW_QUERY: Start fresh with different company/analysis
    """

    response_type: PlanResponseType = Field(
        description="Type of response: approval, refinement, or new_query"
    )
    reasoning: str = Field(
        description="Brief explanation of why this classification was chosen"
    )
    refinement_request: str | None = Field(
        default=None,
        description="If REFINEMENT, describes what changes the user wants"
    )
