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

"""Ad Campaign Agent Test Suite.

This package contains tests for the ad-campaign-agent:

- tests/unit/ - Unit tests for individual tools (no LLM calls)
- tests/integration/ - Integration tests with real LLM using EvalSets
- tests/e2e/ - End-to-end workflow tests

Run tests with:
    make test           # Unit + Integration (default)
    make test-unit      # Fast, no LLM (~5 sec)
    make test-all       # Everything including slow Veo tests
"""
