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

"""Chart generation and visual context schemas."""

from typing import Literal
from pydantic import BaseModel, Field


class ChartResult(BaseModel):
    """Result of chart generation."""

    chart_index: int = Field(
        description="Chart number (1-indexed)"
    )
    metric_name: str = Field(
        description="Name of the metric charted"
    )
    filename: str = Field(
        description="Artifact filename (e.g., 'chart_1.png')"
    )
    base64_data: str = Field(
        description="Base64 encoded chart image"
    )
    section: str = Field(
        description="Report section this chart belongs to"
    )


class VisualContext(BaseModel):
    """Contextualization for a single visual using Setup→Visual→Interpretation pattern."""

    visual_id: str = Field(
        description="Identifier for the visual: 'chart_1', 'chart_2', 'infographic_1', etc."
    )
    visual_type: Literal["chart", "infographic", "table"] = Field(
        description="Type of visual"
    )
    setup_text: str = Field(
        description="1-2 sentences BEFORE the visual explaining what we're looking at and why it matters"
    )
    interpretation_text: str = Field(
        description="1-2 sentences AFTER the visual explaining insights, implications, and investment thesis connection"
    )


class AnalysisSections(BaseModel):
    """Narrative analysis sections with integrated visual contextualization."""

    executive_summary: str = Field(
        description="1-2 paragraph executive summary with investment recommendation"
    )

    # Company Overview Section
    company_overview_intro: str = Field(
        description="Opening paragraph introducing the company"
    )
    company_overview_visual_contexts: list[VisualContext] = Field(
        default_factory=list,
        description="Contextualization for infographics in company overview (business model, competitive landscape)"
    )
    company_overview_conclusion: str = Field(
        default="",
        description="Concluding paragraph after company overview visuals"
    )

    # Financial Performance Section
    financial_intro: str = Field(
        description="Introduction paragraph before financial charts"
    )
    financial_visual_contexts: list[VisualContext] = Field(
        default_factory=list,
        description="Setup+Interpretation for each financial chart (revenue, profit, margins, EPS)"
    )
    financial_conclusion: str = Field(
        description="Conclusion paragraph synthesizing financial performance insights"
    )

    # Valuation Analysis Section
    valuation_intro: str = Field(
        description="Introduction paragraph before valuation analysis"
    )
    valuation_visual_contexts: list[VisualContext] = Field(
        default_factory=list,
        description="Setup+Interpretation for each valuation chart (P/E, EV/EBITDA, etc.)"
    )
    valuation_conclusion: str = Field(
        description="Conclusion paragraph with fair value assessment"
    )

    # Growth Outlook Section
    growth_intro: str = Field(
        description="Introduction paragraph before growth analysis"
    )
    growth_visual_contexts: list[VisualContext] = Field(
        default_factory=list,
        description="Setup+Interpretation for growth charts and infographics"
    )
    growth_conclusion: str = Field(
        description="Conclusion paragraph on growth prospects"
    )

    # Risks & Concerns
    risks_concerns: str = Field(
        description="Comprehensive risk analysis with bullet points or paragraphs"
    )

    # Investment Recommendation
    investment_recommendation: str = Field(
        description="Buy/Hold/Sell recommendation with clear rationale and price target"
    )
