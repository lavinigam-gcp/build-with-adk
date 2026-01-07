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

"""Routing callbacks for validation and classification checks.

These callbacks run after validation/classification agents and handle:
1. Rejected queries (crypto, trading advice, etc.) - respond with rejection message
2. FOLLOW_UP queries - respond with guidance to create new query
3. Valid NEW_QUERY - allow pipeline to continue
"""

from google.genai import types

from app.rules.boundaries_config import SYSTEM_CAPABILITIES


async def check_validation_callback(callback_context):
    """Check validation result after query_validator runs.

    If query is invalid, respond with rejection message and stop pipeline.
    """
    print("\n" + "="*80)
    print("CHECK VALIDATION CALLBACK")
    print("="*80)

    state = callback_context.state

    # Get validation result from state
    validation = state.get("query_validation", {})
    is_valid = validation.get("is_valid", True)
    rejection_reason = validation.get("rejection_reason")
    query_type = validation.get("detected_query_type", "unknown")

    print(f"📋 Validation result: is_valid={is_valid}, type={query_type}")

    if not is_valid:
        print(f"❌ Query rejected: {rejection_reason}")

        # Build rejection response
        rejection_message = f"""I cannot process this query.

**Reason:** {rejection_reason}

{SYSTEM_CAPABILITIES}
"""
        # Set flag to skip remaining pipeline stages
        state["skip_pipeline"] = True
        state["pipeline_response"] = rejection_message

        print("="*80 + "\n")

        # Return response content to stop and respond
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text=rejection_message)]
        )

    print("✓ Query is valid, continuing to classification...")
    print("="*80 + "\n")
    return None  # Continue to next agent


async def check_classification_callback(callback_context):
    """Check classification result after query_classifier runs.

    Handles:
    1. FOLLOW_UP queries when no plan exists - reject with guidance
    2. FOLLOW_UP queries when plan is pending - treat as plan refinement
    3. Post-approval queries for same company - reject
    4. Post-approval queries for new company - reset state for fresh HITL flow
    5. Valid NEW_QUERY - continue to HITL planning
    """
    print("\n" + "="*80)
    print("CHECK CLASSIFICATION CALLBACK")
    print("="*80)

    state = callback_context.state

    # Skip if already rejected by validation
    if state.get("skip_pipeline"):
        print("⏭️  Pipeline already stopped by validation")
        print("="*80 + "\n")
        return None

    # Get classification result from state
    classification = state.get("query_classification", {})
    query_type = classification.get("query_type", "NEW_QUERY")
    detected_company = classification.get("detected_company", "")
    detected_market = classification.get("detected_market", "US")
    reasoning = classification.get("reasoning", "")

    # Get current plan state
    plan_state = state.get("plan_state", "none")

    print(f"📋 Classification: type={query_type}, company={detected_company}, market={detected_market}")
    print(f"   Plan state: {plan_state}")
    print(f"   Reasoning: {reasoning}")

    # PHASE 2: Handle post-approval rejection for same company
    if plan_state == "approved":
        approved_plan = state.get("enhanced_research_plan", {})
        if hasattr(approved_plan, "model_dump"):
            approved_plan = approved_plan.model_dump()

        approved_company = approved_plan.get("company_name", "").lower() if approved_plan else ""

        if detected_company and approved_company:
            detected_lower = detected_company.lower()

            # Check for same company (fuzzy match)
            is_same_company = (
                detected_lower in approved_company or
                approved_company in detected_lower or
                _are_similar_companies(detected_lower, approved_company)
            )

            if is_same_company:
                print(f"❌ Same company query after approval - rejecting")

                rejection_message = f"""The analysis for **{approved_plan.get('company_name', detected_company)}** has already been approved and is being generated.

I cannot add more metrics or modify the plan at this point.

**Options:**
1. **Wait** for the current analysis to complete
2. **Start a new session** with a comprehensive query that includes everything you need from the beginning

For a **different company**, simply ask your question and I'll create a new research plan.
"""
                state["skip_pipeline"] = True
                state["pipeline_response"] = rejection_message

                print("="*80 + "\n")

                return types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=rejection_message)]
                )
            else:
                # New company after approval - reset for fresh HITL flow
                print(f"🔄 New company detected ({detected_company}), resetting for fresh HITL flow")
                state["plan_state"] = "none"
                state["enhanced_research_plan"] = None
                state["plan_response"] = None
                # Continue to HITL planning with new company

    # PHASE 2: Handle FOLLOW_UP when plan is pending (treat as refinement)
    if query_type == "FOLLOW_UP" and plan_state == "pending":
        print("✓ FOLLOW_UP with pending plan - will be treated as refinement")
        # Don't reject - let HITL planning handle it
        state["detected_market"] = detected_market
        print("="*80 + "\n")
        return None  # Continue to HITL planning

    # Handle FOLLOW_UP when no plan exists
    if query_type == "FOLLOW_UP" and plan_state not in ("pending", "approved"):
        print("❌ FOLLOW_UP query detected - providing guidance")

        # Build follow-up rejection response
        follow_up_message = f"""I understand you'd like to extend the previous analysis.

Currently, I can only process complete, fresh queries. Follow-up queries that extend previous analyses are not supported.

**To include additional metrics or analysis:**
Please create a new comprehensive query that includes everything you need, for example:
- "Comprehensive analysis of {detected_company or '[Company Name]'} including revenue, margins, AND the additional metrics you wanted"

This will generate a complete report with all the data you need in one go.
"""
        # Set flag to skip remaining pipeline stages
        state["skip_pipeline"] = True
        state["pipeline_response"] = follow_up_message

        print("="*80 + "\n")

        # Return response content to stop and respond
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text=follow_up_message)]
        )

    # Store market in state for pipeline to use
    state["detected_market"] = detected_market
    print(f"✓ NEW_QUERY detected, market={detected_market}, continuing to HITL planning...")
    print("="*80 + "\n")
    return None  # Continue to HITL planning


def _are_similar_companies(name1: str, name2: str) -> bool:
    """Check if two company names are likely the same.

    Uses simple heuristics to match variations like:
    - "apple" vs "apple inc"
    - "alphabet" vs "google"
    - "meta" vs "facebook"
    """
    # Direct containment already handled in caller

    # Common variations
    variations = {
        "google": ["alphabet", "googl"],
        "alphabet": ["google", "googl"],
        "meta": ["facebook", "fb"],
        "facebook": ["meta", "fb"],
    }

    for key, aliases in variations.items():
        if key in name1:
            for alias in aliases:
                if alias in name2:
                    return True
        if key in name2:
            for alias in aliases:
                if alias in name1:
                    return True

    return False


async def skip_if_rejected_callback(callback_context):
    """Check if pipeline should be skipped due to validation/classification rejection.

    This runs before each pipeline stage to skip if already rejected.
    """
    state = callback_context.state

    if state.get("skip_pipeline"):
        print(f"⏭️  Skipping {callback_context.agent_name} - pipeline was stopped")
        # Return the stored response to end processing
        response = state.get("pipeline_response", "Query could not be processed.")
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text=response)]
        )

    return None  # Continue normally
