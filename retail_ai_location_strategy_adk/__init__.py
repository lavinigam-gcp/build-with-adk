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

"""Retail AI Location Strategy Agent - ADK Implementation.

A multi-agent pipeline for retail location intelligence analysis,
built with Google's Agent Development Kit (ADK).

This package provides:
- Market research using Google Search grounding
- Competitor mapping using Google Maps Places API
- Quantitative gap analysis with Python code execution
- Strategic recommendations with extended reasoning
- Professional HTML executive reports
- Visual infographic generation

Usage:
    adk web retail_ai_location_strategy_adk
"""

from .agent import root_agent, get_initial_state

__all__ = ["root_agent", "get_initial_state"]
__version__ = "1.0.0"
