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

"""Sub-agents for the equity research pipeline.

This module exports all agents used in the equity research system:
- Validation and classification agents (query_validator, query_classifier, follow_up_handler)
- Planning and data gathering agents
- Chart and infographic generation agents
- Analysis and report generation agents
"""

from .validator.agent import query_validator
from .classifier.agent import query_classifier
from .classifier.follow_up_handler import follow_up_handler
from .planner.agent import research_planner
from .planner.metric_planner import metric_planner
from .planner.plan_response_classifier import plan_response_classifier
from .planner.plan_refiner import plan_refiner
from .data_fetchers.parallel_pipeline import parallel_data_gatherers
from .consolidator.agent import data_consolidator
from .chart_generator.loop_pipeline import chart_generation_loop
from .infographic.planner import infographic_planner
from .infographic.generator import infographic_generator
from .analysis.agent import analysis_writer
from .report_generator.agent import html_report_generator

__all__ = [
    # Validation and classification
    "query_validator",
    "query_classifier",
    "follow_up_handler",
    # Phase 1 Planning
    "research_planner",
    # Phase 2 HITL Planning
    "metric_planner",
    "plan_response_classifier",
    "plan_refiner",
    # Data gathering
    "parallel_data_gatherers",
    "data_consolidator",
    # Chart and infographic generation
    "chart_generation_loop",
    "infographic_planner",
    "infographic_generator",
    # Analysis and report generation
    "analysis_writer",
    "html_report_generator",
]
