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

"""Data models for research data extraction and consolidation."""

from typing import Literal
from pydantic import BaseModel, Field


class DataPoint(BaseModel):
    """A single data point for a metric."""

    period: str = Field(
        description="Time period (e.g., '2023', 'Q1 2024', 'Jan 2024')"
    )
    value: float = Field(
        description="Numeric value for this period"
    )
    unit: str = Field(
        default="USD",
        description="Unit of measurement (USD, %, millions, billions, etc.)"
    )


class MetricData(BaseModel):
    """Extracted data for one metric."""

    metric_name: str = Field(
        description="Name of the metric"
    )
    data_points: list[DataPoint] = Field(
        description="List of data points with period and value"
    )
    chart_type: Literal["line", "bar", "area"] = Field(
        default="line",
        description="Chart type for visualization"
    )
    chart_title: str = Field(
        description="Descriptive title for the chart"
    )
    y_axis_label: str = Field(
        description="Label for the Y-axis"
    )
    section: str = Field(
        description="Report section this belongs to"
    )
    notes: str | None = Field(
        default=None,
        description="Any notes or caveats about the data"
    )


class ConsolidatedResearchData(BaseModel):
    """All research data consolidated from parallel fetchers."""

    company_name: str = Field(
        description="Company name"
    )
    ticker: str = Field(
        description="Stock ticker"
    )
    metrics: list[MetricData] = Field(
        description="List of extracted metrics with data"
    )
    company_overview: str = Field(
        description="Brief company description and business model"
    )
    news_summary: str = Field(
        description="Summary of recent news and developments"
    )
    analyst_ratings: str = Field(
        description="Analyst ratings and price targets"
    )
    key_risks: list[str] = Field(
        default_factory=list,
        description="Key risk factors for the company"
    )
