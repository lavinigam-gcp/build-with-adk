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

"""Pydantic schemas for equity research agent data structures."""

from .research import (
    # Phase 1 schemas
    MetricSpec,
    ResearchPlan,
    QueryClassification,
    # Phase 2 enums
    MetricCategory,
    AnalysisType,
    PlanResponseType,
    # Phase 2 schemas
    EnhancedMetricSpec,
    EnhancedResearchPlan,
    PlanResponseClassification,
)
from .data import DataPoint, MetricData, ConsolidatedResearchData
from .chart import ChartResult, VisualContext, AnalysisSections
from .infographic import InfographicSpec, InfographicPlan, InfographicResult

__all__ = [
    # Phase 1 schemas
    "MetricSpec",
    "ResearchPlan",
    "QueryClassification",
    # Phase 2 enums
    "MetricCategory",
    "AnalysisType",
    "PlanResponseType",
    # Phase 2 schemas
    "EnhancedMetricSpec",
    "EnhancedResearchPlan",
    "PlanResponseClassification",
    # Data schemas
    "DataPoint",
    "MetricData",
    "ConsolidatedResearchData",
    # Chart schemas
    "ChartResult",
    "VisualContext",
    "AnalysisSections",
    # Infographic schemas
    "InfographicSpec",
    "InfographicPlan",
    "InfographicResult",
]
