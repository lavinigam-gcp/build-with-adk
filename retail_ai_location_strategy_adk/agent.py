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

"""Retail Location Strategy Agent - Root Agent Definition.

This module defines the root agent for the Location Strategy Pipeline.
It uses a SequentialAgent to orchestrate 6 specialized sub-agents:

1. MarketResearchAgent - Live web research with Google Search
2. CompetitorMappingAgent - Competitor mapping with Maps Places API
3. GapAnalysisAgent - Quantitative analysis with Python code execution
4. StrategyAdvisorAgent - Strategic synthesis with extended reasoning
5. ReportGeneratorAgent - HTML executive report generation
6. InfographicGeneratorAgent - Visual infographic generation

The pipeline analyzes a target location for a specific business type and
produces comprehensive location intelligence including recommendations,
an HTML report, and an infographic.

Authentication:
    Uses Google AI Studio (API key) instead of Vertex AI.
    Set environment variables:
        GOOGLE_API_KEY=your_api_key
        GOOGLE_GENAI_USE_VERTEXAI=FALSE
        MAPS_API_KEY=your_maps_api_key

Usage:
    Run with: adk web retail_ai_location_strategy_adk

    The agent expects initial state variables:
    - target_location: The geographic area to analyze (e.g., "Bangalore, India")
    - business_type: Type of business to open (e.g., "coffee shop")

    Optional state variables:
    - maps_api_key: Google Maps API key for Places search
"""

from datetime import datetime

from google.adk.agents import SequentialAgent

from .sub_agents import (
    intake_agent,
    market_research_agent,
    competitor_mapping_agent,
    gap_analysis_agent,
    strategy_advisor_agent,
    report_generator_agent,
    infographic_generator_agent,
)


# Root agent orchestrating the complete location strategy pipeline
root_agent = SequentialAgent(
    name="LocationStrategyPipeline",
    description="""Comprehensive retail location strategy analysis pipeline.

This agent analyzes a target location for a specific business type and produces:
1. Market research findings from live web data
2. Competitor mapping from Google Maps Places API
3. Quantitative gap analysis with zone rankings
4. Strategic recommendations with structured JSON output
5. Professional HTML executive report
6. Visual infographic summary

To use, provide:
- target_location: Geographic area to analyze (e.g., "Indiranagar, Bangalore")
- business_type: Type of business (e.g., "coffee shop", "bakery", "gym")

The analysis runs automatically through all stages and produces artifacts
including JSON report, HTML report, and infographic image.
""",
    sub_agents=[
        intake_agent,               # Part 0: Parse user request
        market_research_agent,      # Part 1: Market research with search
        competitor_mapping_agent,   # Part 2A: Competitor mapping with Maps
        gap_analysis_agent,         # Part 2B: Gap analysis with code exec
        strategy_advisor_agent,     # Part 3: Strategy synthesis
        report_generator_agent,     # Part 4: HTML report generation
        infographic_generator_agent,  # Part 5: Infographic generation
    ],
)


def get_initial_state(
    target_location: str,
    business_type: str,
    maps_api_key: str = "",
) -> dict:
    """Create initial state for the pipeline.

    Args:
        target_location: The geographic area to analyze
        business_type: The type of business to open
        maps_api_key: Google Maps API key (optional, for Places search)

    Returns:
        dict: Initial state dictionary with all required variables
    """
    return {
        "target_location": target_location,
        "business_type": business_type,
        "current_date": datetime.now().strftime("%Y-%m-%d"),
        "maps_api_key": maps_api_key,
    }
