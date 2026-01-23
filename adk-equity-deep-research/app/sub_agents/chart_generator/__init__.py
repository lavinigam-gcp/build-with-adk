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

"""Chart generation with conditional batch/sequential mode.

This module exports the chart generation agent based on the ENABLE_BATCH_CHARTS flag:
- When ENABLE_BATCH_CHARTS=true: Uses batch_chart_generator (1 LLM + 1 sandbox call)
- When ENABLE_BATCH_CHARTS=false: Uses chart_generation_loop (N LLM + N sandbox calls)

The batch mode provides ~5-10x speedup for chart generation.
"""

from app.config import ENABLE_BATCH_CHARTS

# Always export the sequential loop for backwards compatibility
from .loop_pipeline import chart_generation_loop

# Conditional export based on feature flag
if ENABLE_BATCH_CHARTS:
    from .batch_agent import batch_chart_generator as chart_generation_agent
    print("📊 Chart generation mode: BATCH (experimental)")
else:
    chart_generation_agent = chart_generation_loop
    print("📊 Chart generation mode: SEQUENTIAL (default)")

__all__ = [
    "chart_generation_loop",    # Always available for explicit use
    "chart_generation_agent",   # Feature-flag controlled agent
]
