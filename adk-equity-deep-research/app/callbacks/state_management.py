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
    """Initialize or reset charts_generated, charts_summary, and infographics_summary based on query classification.

    Uses the query_classifier agent's output to determine if this is a NEW_QUERY (reset state)
    or FOLLOW_UP (preserve state). This ensures the template variables exist in state before
    the chart/infographic generation starts.
    """
    print("\n" + "="*80)
    print("INITIALIZE CHARTS STATE CALLBACK - START")
    print("="*80)

    state = callback_context.state

    print(f"📋 Agent: {callback_context.agent_name}")
    print(f"🔑 Invocation ID: {callback_context.invocation_id}")

    # Check query classification from classifier agent
    classification = state.get("query_classification")
    query_type = classification.get("query_type", "NEW_QUERY") if classification else "NEW_QUERY"
    reasoning = classification.get("reasoning", "No classification available") if classification else "No classification available"

    print(f"\n🔍 Query Classification: {query_type}")
    print(f"   Reasoning: {reasoning}")

    if query_type == "NEW_QUERY":
        # New query detected - reset visualization state
        print(f"\n🔄 NEW QUERY - Resetting visualization state")
        print("   Clearing old chart and infographic state for fresh analysis...")

        state["charts_generated"] = []
        state["charts_summary"] = []
        state["infographics_summary"] = []

        print("✓ Cleared all chart and infographic state for fresh analysis")
    else:  # FOLLOW_UP
        print(f"\n↪️  FOLLOW-UP QUERY - Preserving existing state")
        print(f"   Current state:")
        print(f"   - charts_generated: {len(state.get('charts_generated', []))} items")
        print(f"   - charts_summary: {len(state.get('charts_summary', []))} items")
        print(f"   - infographics_summary: {len(state.get('infographics_summary', []))} items")

    # Ensure state variables exist (defensive programming)
    if "charts_generated" not in state:
        state["charts_generated"] = []
    if "charts_summary" not in state:
        state["charts_summary"] = []
    if "infographics_summary" not in state:
        state["infographics_summary"] = []

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
