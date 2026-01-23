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

"""Callback functions for agent lifecycle hooks."""

from .chart_execution import execute_chart_code_callback
from .batch_chart_execution import execute_batch_charts_callback
from .state_management import (
    initialize_charts_state_callback,
    ensure_classifier_state_callback,
)
from .infographic_summary import create_infographics_summary_callback
from .report_generation import save_html_report_callback
from .routing import (
    check_validation_callback,
    check_classification_callback,
    skip_if_rejected_callback,
)
from .planning import (
    check_plan_state_callback,
    present_plan_callback,
    process_plan_response_callback,
    skip_if_not_approved_callback,
)

__all__ = [
    # Chart execution (sequential)
    "execute_chart_code_callback",
    # Chart execution (batch)
    "execute_batch_charts_callback",
    # State management
    "initialize_charts_state_callback",
    "ensure_classifier_state_callback",
    # Infographic
    "create_infographics_summary_callback",
    # Report generation
    "save_html_report_callback",
    # Phase 1 routing
    "check_validation_callback",
    "check_classification_callback",
    "skip_if_rejected_callback",
    # Phase 2 HITL planning
    "check_plan_state_callback",
    "present_plan_callback",
    "process_plan_response_callback",
    "skip_if_not_approved_callback",
]
