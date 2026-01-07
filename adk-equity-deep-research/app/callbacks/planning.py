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

"""HITL planning callbacks for the equity research agent.

These callbacks manage the Human-In-The-Loop planning flow:
- check_plan_state_callback: Routes based on plan_state (none/pending/approved)
- present_plan_callback: Formats plan as markdown and presents to user
- process_plan_response_callback: Handles user response (approval/refinement/new_query)
- skip_if_not_approved_callback: Skips pipeline if plan not yet approved

Phase 2 HITL Flow:
    1. User query arrives
    2. If plan_state == "none": metric_planner runs, present_plan_callback shows plan
    3. If plan_state == "pending": plan_response_classifier runs
    4. Based on response: approve → pipeline, refine → update plan, new → reset
    5. If plan_state == "approved": pipeline executes
"""

from google.genai import types


async def check_plan_state_callback(callback_context):
    """Check and log plan state before HITL planning stage.

    This callback runs before the HITL planning agent to determine routing.
    If skip_pipeline is True (set by rejection callbacks), skip the entire
    HITL planning stage.

    Args:
        callback_context: ADK callback context with state access

    Returns:
        Content to skip if pipeline was stopped, None to continue
    """
    state = callback_context.state
    plan_state = state.get("plan_state", "none")

    print("\n" + "=" * 80)
    print("HITL PLANNING - CHECK STATE")
    print("=" * 80)

    # CRITICAL: Skip if pipeline was stopped by validation/classification rejection
    # This prevents HITL planning from running after a rejection message was shown
    if state.get("skip_pipeline"):
        print("⏭️  Skipping HITL planning - pipeline was stopped by rejection")
        print("=" * 80 + "\n")
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text="")]
        )

    print(f"📋 Current plan_state: {plan_state}")

    if plan_state == "none":
        print("   → Will generate new plan via metric_planner")
    elif plan_state == "pending":
        print("   → Plan awaiting approval, will classify user response")
    elif plan_state == "approved":
        print("   → Plan approved, will skip to pipeline")
    else:
        print(f"   → Unknown state: {plan_state}, treating as 'none'")
        state["plan_state"] = "none"

    print("=" * 80 + "\n")
    return None  # Continue to next agent


async def present_plan_callback(callback_context):
    """Format plan as markdown and present to user.

    This callback runs after metric_planner generates a plan.
    It formats the plan as a readable markdown table and returns
    a Content object to stop execution and show the plan to the user.

    Args:
        callback_context: ADK callback context with state access

    Returns:
        types.Content with formatted plan, or None if no plan exists
    """
    state = callback_context.state
    plan = state.get("enhanced_research_plan")

    print("\n" + "=" * 80)
    print("HITL PLANNING - PRESENT PLAN")
    print("=" * 80)

    if not plan:
        print("❌ No plan found in state")
        print("=" * 80 + "\n")
        return None

    # Handle both dict and Pydantic model
    if hasattr(plan, "model_dump"):
        plan_dict = plan.model_dump()
    else:
        plan_dict = plan

    # Format plan as structured markdown
    markdown = format_plan_as_markdown(plan_dict)

    # Set state to pending approval
    state["plan_state"] = "pending"

    # CRITICAL: Set turn-based flag to skip remaining agents THIS turn
    # This prevents plan_response_classifier and plan_refiner from running
    # in the same turn as the plan presentation.
    # The flag is reset at the start of the next turn by ensure_classifier_state_callback.
    state["plan_presented_this_turn"] = True

    company = plan_dict.get("company_name", "Unknown")
    metrics_count = len(plan_dict.get("metrics_to_analyze", []))
    print(f"✓ Plan for {company} with {metrics_count} metrics presented")
    print(f"📋 plan_state set to 'pending', plan_presented_this_turn=True")
    print("=" * 80 + "\n")

    # Return plan presentation to user (stops execution)
    return types.Content(
        role="model",
        parts=[types.Part.from_text(text=markdown)]
    )


def format_plan_as_markdown(plan: dict) -> str:
    """Format EnhancedResearchPlan as readable markdown.

    Args:
        plan: EnhancedResearchPlan as dictionary

    Returns:
        Formatted markdown string for presentation
    """
    company = plan.get("company_name", "Unknown")
    ticker = plan.get("ticker", "")
    exchange = plan.get("exchange", "")
    market = plan.get("market", "US")
    analysis_type = plan.get("analysis_type", "comprehensive")
    time_range = plan.get("time_range_years", 5)
    metrics = plan.get("metrics_to_analyze", [])
    infographic_count = plan.get("infographic_count", 3)
    plan_version = plan.get("plan_version", 1)

    # Build markdown
    md = f"""## 📊 Research Plan for {company} ({ticker})

**Exchange:** {exchange} | **Market:** {market} | **Analysis Type:** {analysis_type.upper() if isinstance(analysis_type, str) else analysis_type}

**Time Range:** {time_range} years | **Metrics:** {len(metrics)} | **Infographics:** {infographic_count}

---

### Planned Metrics

| # | Metric | Category | Chart | Priority | Market-Specific |
|---|--------|----------|-------|----------|-----------------|
"""

    for i, m in enumerate(metrics, 1):
        metric_name = m.get("metric_name", "Unknown")
        category = m.get("category", "unknown")
        chart_type = m.get("chart_type", "line")
        priority = m.get("priority", 5)
        is_market_specific = "✓" if m.get("is_market_specific", False) else ""

        # Handle enum values
        if hasattr(category, "value"):
            category = category.value

        md += f"| {i} | {metric_name} | {category} | {chart_type} | {priority} | {is_market_specific} |\n"

    # Add sections info
    sections = plan.get("report_sections", [])
    if sections:
        md += f"\n**Report Sections:** {', '.join(sections)}\n"

    # Add version info
    if plan_version > 1:
        md += f"\n*Plan version: {plan_version}*\n"

    # Add instructions
    md += """
---

### What would you like to do?

**To approve:** Say "looks good", "proceed", or "approved"
**To modify:** Say "add X", "remove Y", or "change chart type for Z"
**To start over:** Describe a different company or analysis
"""

    return md


async def process_plan_response_callback(callback_context):
    """Handle user response after classification.

    This callback runs after plan_response_classifier to process the result.
    Based on response type, it either approves, triggers refinement, or resets.

    Args:
        callback_context: ADK callback context with state access

    Returns:
        None to continue, or Content to stop with message
    """
    state = callback_context.state
    response = state.get("plan_response")

    print("\n" + "=" * 80)
    print("HITL PLANNING - PROCESS RESPONSE")
    print("=" * 80)

    if not response:
        print("❌ No plan_response found in state")
        print("=" * 80 + "\n")
        return None

    # Handle both dict and Pydantic model
    if hasattr(response, "model_dump"):
        response_dict = response.model_dump()
    else:
        response_dict = response

    response_type = response_dict.get("response_type", "")
    reasoning = response_dict.get("reasoning", "")

    # Handle enum values
    if hasattr(response_type, "value"):
        response_type = response_type.value

    print(f"📋 Response type: {response_type}")
    print(f"   Reasoning: {reasoning}")

    if response_type == "approval":
        # Mark plan as approved
        state["plan_state"] = "approved"

        # Update the plan's approved flag
        plan = state.get("enhanced_research_plan")
        if plan:
            if hasattr(plan, "approved_by_user"):
                plan.approved_by_user = True
            elif isinstance(plan, dict):
                plan["approved_by_user"] = True
            state["enhanced_research_plan"] = plan

        print("✓ Plan approved! Proceeding to pipeline...")
        print("=" * 80 + "\n")
        return None  # Continue to pipeline

    elif response_type == "refinement":
        # Stay in pending, plan_refiner will update the plan
        refinement_request = response_dict.get("refinement_request", "")
        print(f"🔄 Refinement requested: {refinement_request}")
        print("   → plan_refiner will modify the plan")
        print("=" * 80 + "\n")
        return None  # Continue to refiner, then re-present

    elif response_type == "new_query":
        # Reset state for fresh query
        state["plan_state"] = "none"
        state["enhanced_research_plan"] = None
        state["plan_response"] = None
        print("🔄 New query detected, resetting state...")
        print("=" * 80 + "\n")
        return None  # Continue to metric_planner for new plan

    else:
        print(f"⚠️ Unknown response type: {response_type}, treating as approval")
        state["plan_state"] = "approved"
        print("=" * 80 + "\n")
        return None


async def skip_if_not_approved_callback(callback_context):
    """Skip pipeline execution if plan is not yet approved.

    This callback runs before the equity_research_pipeline to ensure
    the plan has been approved by the user before proceeding.

    Also skips if skip_pipeline flag is set (rejection occurred).

    Args:
        callback_context: ADK callback context with state access

    Returns:
        None to continue, or Content to stop with message
    """
    state = callback_context.state

    # Skip if pipeline was stopped by validation/classification rejection
    if state.get("skip_pipeline"):
        print("⏭️  Skipping pipeline - skip_pipeline flag is set (rejection occurred)")
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text="")]
        )

    plan_state = state.get("plan_state", "none")

    if plan_state != "approved":
        print(f"⏭️  Skipping pipeline - plan_state is '{plan_state}' (not approved)")

        if plan_state == "pending":
            # Shouldn't reach here, but just in case
            return types.Content(
                role="model",
                parts=[types.Part.from_text(
                    text="Please approve or modify the research plan before I can proceed with the analysis."
                )]
            )

        # For "none" state, we should have gone through metric_planner
        return types.Content(
            role="model",
            parts=[types.Part.from_text(
                text="I need to create a research plan first. Please tell me which company you'd like to analyze."
            )]
        )

    print("✓ Plan approved, proceeding to pipeline execution...")
    return None  # Continue to pipeline
