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

"""State management callbacks for query classification and session state."""


async def initialize_charts_state_callback(callback_context):
    """Initialize/reset charts state for new query.

    Always resets state since FOLLOW_UP queries are no longer supported.
    This ensures the template variables exist in state before the chart/infographic
    generation starts.
    """
    print("\n" + "="*80)
    print("INITIALIZE CHARTS STATE CALLBACK - START")
    print("="*80)

    state = callback_context.state

    print(f"📋 Agent: {callback_context.agent_name}")
    print(f"🔑 Invocation ID: {callback_context.invocation_id}")

    # Always reset visualization state for fresh analysis
    # (FOLLOW_UP queries are rejected before reaching this point)
    print("\n🔄 Resetting visualization state for new analysis...")

    state["charts_generated"] = []
    state["charts_summary"] = []
    state["infographics_summary"] = []

    print("✓ State reset complete")
    print("="*80 + "\n")


async def ensure_classifier_state_callback(callback_context):
    """Ensure last_query_summary exists before query_classifier runs.

    On the first query in a session, last_query_summary won't exist yet and
    template variable injection will fail with KeyError. Initialize with
    default value if missing.
    """
    state = callback_context.state

    if "last_query_summary" not in state:
        state["last_query_summary"] = "No previous query context (first query in session)"
        print("✓ Initialized last_query_summary for first query in session")
