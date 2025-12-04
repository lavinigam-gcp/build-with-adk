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

"""Sub-agents for the Location Strategy Pipeline.

This module exports all specialized agents that form the pipeline:
0. IntakeAgent - Parses user request to extract location and business type
1. MarketResearchAgent - Live web research with Google Search
2. CompetitorMappingAgent - Competitor mapping with Maps API
3. GapAnalysisAgent - Quantitative analysis with code execution
4. StrategyAdvisorAgent - Strategic synthesis with extended reasoning
5. ReportGeneratorAgent - HTML report generation
6. InfographicGeneratorAgent - Visual infographic generation
"""

from .intake_agent import intake_agent
from .market_research import market_research_agent
from .competitor_mapping import competitor_mapping_agent
from .gap_analysis import gap_analysis_agent
from .strategy_advisor import strategy_advisor_agent
from .report_generator import report_generator_agent
from .infographic_generator import infographic_generator_agent

__all__ = [
    "intake_agent",
    "market_research_agent",
    "competitor_mapping_agent",
    "gap_analysis_agent",
    "strategy_advisor_agent",
    "report_generator_agent",
    "infographic_generator_agent",
]
