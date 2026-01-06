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

    If FOLLOW_UP query, respond with guidance and stop pipeline.
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

    print(f"📋 Classification: type={query_type}, company={detected_company}, market={detected_market}")
    print(f"   Reasoning: {reasoning}")

    if query_type == "FOLLOW_UP":
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
    print(f"✓ NEW_QUERY detected, market={detected_market}, continuing to pipeline...")
    print("="*80 + "\n")
    return None  # Continue to pipeline


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
