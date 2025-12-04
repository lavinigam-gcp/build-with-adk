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

"""Pipeline callbacks for logging and artifact management."""

from .pipeline_callbacks import (
    # Before callbacks
    before_market_research,
    before_competitor_mapping,
    before_gap_analysis,
    before_strategy_advisor,
    before_report_generator,
    before_infographic_generator,
    # After callbacks
    after_market_research,
    after_competitor_mapping,
    after_gap_analysis,
    after_strategy_advisor,
    after_report_generator,
    after_infographic_generator,
)

__all__ = [
    "before_market_research",
    "before_competitor_mapping",
    "before_gap_analysis",
    "before_strategy_advisor",
    "before_report_generator",
    "before_infographic_generator",
    "after_market_research",
    "after_competitor_mapping",
    "after_gap_analysis",
    "after_strategy_advisor",
    "after_report_generator",
    "after_infographic_generator",
]
