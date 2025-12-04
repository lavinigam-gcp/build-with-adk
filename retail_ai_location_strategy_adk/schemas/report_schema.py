# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Pydantic schemas for Location Intelligence Report structured output."""

from typing import List
from pydantic import BaseModel, Field


class StrengthAnalysis(BaseModel):
    """Detailed strength with evidence."""

    factor: str = Field(description="The strength factor name")
    description: str = Field(description="Description of the strength")
    evidence_from_analysis: str = Field(description="Evidence from the analysis supporting this strength")


class ConcernAnalysis(BaseModel):
    """Detailed concern with mitigation strategy."""

    risk: str = Field(description="The risk or concern name")
    description: str = Field(description="Description of the concern")
    mitigation_strategy: str = Field(description="Strategy to mitigate this concern")


class CompetitionProfile(BaseModel):
    """Competition characteristics in the zone."""

    total_competitors: int = Field(description="Total number of competitors in the zone")
    density_per_km2: float = Field(description="Competitor density per square kilometer")
    chain_dominance_pct: float = Field(description="Percentage of chain/franchise competitors")
    avg_competitor_rating: float = Field(description="Average rating of competitors")
    high_performers_count: int = Field(description="Number of high-performing competitors (4.5+ rating)")


class MarketCharacteristics(BaseModel):
    """Market fundamentals for the zone."""

    population_density: str = Field(description="Population density level (Low/Medium/High)")
    income_level: str = Field(description="Income level of the area (Low/Medium/High)")
    infrastructure_access: str = Field(description="Description of infrastructure access")
    foot_traffic_pattern: str = Field(description="Description of foot traffic patterns")
    rental_cost_tier: str = Field(description="Rental cost tier (Low/Medium/High)")


class LocationRecommendation(BaseModel):
    """Complete recommendation for a specific location."""

    location_name: str = Field(description="Name of the recommended location/zone")
    area: str = Field(description="Broader area or neighborhood")
    overall_score: int = Field(description="Overall score out of 100", ge=0, le=100)
    opportunity_type: str = Field(description="Type of opportunity (e.g., 'Metro First-Mover', 'Residential Sticky')")
    strengths: List[StrengthAnalysis] = Field(description="List of strengths with evidence")
    concerns: List[ConcernAnalysis] = Field(description="List of concerns with mitigation strategies")
    competition: CompetitionProfile = Field(description="Competition profile for this location")
    market: MarketCharacteristics = Field(description="Market characteristics for this location")
    best_customer_segment: str = Field(description="Best customer segment to target")
    estimated_foot_traffic: str = Field(description="Estimated foot traffic description")
    next_steps: List[str] = Field(description="Actionable next steps")


class AlternativeLocation(BaseModel):
    """Brief summary of alternative location."""

    location_name: str = Field(description="Name of the alternative location")
    area: str = Field(description="Broader area or neighborhood")
    overall_score: int = Field(description="Overall score out of 100", ge=0, le=100)
    opportunity_type: str = Field(description="Type of opportunity")
    key_strength: str = Field(description="Key strength of this location")
    key_concern: str = Field(description="Key concern for this location")
    why_not_top: str = Field(description="Reason why this is not the top recommendation")


class LocationIntelligenceReport(BaseModel):
    """Complete location intelligence analysis report."""

    target_location: str = Field(description="The target location being analyzed")
    business_type: str = Field(description="The type of business being planned")
    analysis_date: str = Field(description="Date of the analysis")
    market_validation: str = Field(description="Overall market validation summary")
    total_competitors_found: int = Field(description="Total number of competitors found")
    zones_analyzed: int = Field(description="Number of zones analyzed")
    top_recommendation: LocationRecommendation = Field(description="Top recommended location")
    alternative_locations: List[AlternativeLocation] = Field(description="Alternative location options")
    key_insights: List[str] = Field(description="Key strategic insights from the analysis")
    methodology_summary: str = Field(description="Summary of the analysis methodology")
