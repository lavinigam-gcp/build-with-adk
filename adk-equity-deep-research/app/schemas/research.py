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

from typing import Literal
from pydantic import BaseModel, Field


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
