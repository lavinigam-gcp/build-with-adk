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

This module exports all 17 agents used in the 8-stage research pipeline.
"""

from .classifier.agent import query_classifier
from .planner.agent import research_planner
from .data_fetchers.parallel_pipeline import parallel_data_gatherers
from .consolidator.agent import data_consolidator
from .chart_generator.loop_pipeline import chart_generation_loop
from .infographic.planner import infographic_planner
from .infographic.generator import infographic_generator
from .analysis.agent import analysis_writer
from .report_generator.agent import html_report_generator

__all__ = [
    "query_classifier",
    "research_planner",
    "parallel_data_gatherers",
    "data_consolidator",
    "chart_generation_loop",
    "infographic_planner",
    "infographic_generator",
    "analysis_writer",
    "html_report_generator",
]
