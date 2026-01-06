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

"""Templatized rules and configuration modules for equity research agent.

Note: Using 'rules/' instead of 'config/' to avoid conflict with app/config.py.
"""

from .boundaries_config import (
    UNSUPPORTED_QUERY_TYPES,
    SYSTEM_CAPABILITIES,
    check_query_boundaries,
)
from .markets_config import (
    SUPPORTED_MARKETS,
    MARKET_DETECTION_HINTS,
    get_market_by_hint,
    get_market_config,
    is_market_supported,
)

__all__ = [
    "UNSUPPORTED_QUERY_TYPES",
    "SYSTEM_CAPABILITIES",
    "check_query_boundaries",
    "SUPPORTED_MARKETS",
    "MARKET_DETECTION_HINTS",
    "get_market_by_hint",
    "get_market_config",
    "is_market_supported",
]
