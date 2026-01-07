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

"""Equity Research Agent - Root Agent Definition.

A professional multi-stage agent pipeline that generates comprehensive equity
research reports with charts, infographics, and analysis.

Architecture (Phase 2 - HITL):
    The agent uses callback-based routing with Human-In-The-Loop planning:
    - Stage 0: Query Validation (rejects crypto, trading advice, etc.)
    - Stage 1: Query Classification (NEW_QUERY vs FOLLOW_UP with market detection)
    - Stage 2: HITL Planning (generates plan, presents for approval, handles refinement)
    - Stages 3-10: Research pipeline (only runs after plan is approved)

    HITL Flow:
    1. metric_planner generates EnhancedResearchPlan with 10-15 metrics
    2. Plan presented to user as markdown table
    3. User can approve ("looks good"), refine ("add ROE"), or start over
    4. On approval, pipeline executes with the approved plan

Supported Markets:
    - US (NYSE, NASDAQ)
    - India (NSE, BSE)
    - China (SSE, SZSE, HKEX)
    - Japan (TSE)
    - Korea (KRX, KOSDAQ)
    - Europe (LSE, Euronext, XETRA)

Final Output:
    - equity_report.html (multi-page report with embedded charts/infographics)
    - chart_1.png, chart_2.png, ... (individual chart artifacts)
    - infographic_1.png, infographic_2.png, ... (individual infographic artifacts)

Usage:
    Run with: adk web app

    The agent expects a natural language query like:
    "Analyze Tesla stock with focus on profitability and valuation"
"""

from google.adk.agents import SequentialAgent, LlmAgent
from google.genai import types

from .config import APP_NAME, MODEL
from .sub_agents import (
    query_validator,
    query_classifier,
    research_planner,
    metric_planner,
    plan_response_classifier,
    plan_refiner,
    parallel_data_gatherers,
    data_consolidator,
    chart_generation_loop,
    infographic_planner,
    infographic_generator,
    analysis_writer,
    html_report_generator,
)
from .callbacks import (
    ensure_classifier_state_callback,
    check_validation_callback,
    check_classification_callback,
    skip_if_rejected_callback,
    check_plan_state_callback,
    present_plan_callback,
    process_plan_response_callback,
    skip_if_not_approved_callback,
)


# =============================================================================
# PHASE 1: Validation and Classification (unchanged)
# =============================================================================

# Wrap query_validator with after_agent_callback for validation check
query_validator_with_routing = LlmAgent(
    model=MODEL,
    name="query_validator",
    description=query_validator.description,
    instruction=query_validator.instruction,
    output_schema=query_validator.output_schema,
    output_key=query_validator.output_key,
    after_agent_callback=check_validation_callback,
)

# Wrap query_classifier with after_agent_callback for classification check
query_classifier_with_routing = LlmAgent(
    model=MODEL,
    name="query_classifier",
    description=query_classifier.description,
    instruction=query_classifier.instruction,
    output_schema=query_classifier.output_schema,
    output_key=query_classifier.output_key,
    after_agent_callback=check_classification_callback,
)


# =============================================================================
# PHASE 2: HITL Planning Agents with Conditional Callbacks
# =============================================================================

async def skip_if_plan_exists(callback_context):
    """Skip metric_planner if plan already exists (pending or approved)."""
    state = callback_context.state
    plan_state = state.get("plan_state", "none")

    if plan_state in ("pending", "approved"):
        print(f"⏭️  Skipping metric_planner - plan_state is '{plan_state}'")
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text="")]
        )
    return None  # Continue to generate plan


async def skip_if_not_pending(callback_context):
    """Skip plan_response_classifier if plan is not pending approval.

    CRITICAL: Also skip if plan was JUST presented this turn.
    This prevents the classifier from running immediately after plan presentation,
    before the user has a chance to respond.
    """
    state = callback_context.state
    plan_state = state.get("plan_state", "none")

    # Skip if plan is not pending
    if plan_state != "pending":
        print(f"⏭️  Skipping plan_response_classifier - plan_state is '{plan_state}'")
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text="")]
        )

    # CRITICAL: Skip if plan was just presented THIS turn
    # The classifier should only run on the NEXT turn when user responds
    if state.get("plan_presented_this_turn"):
        print(f"⏭️  Skipping plan_response_classifier - plan was just presented this turn")
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text="")]
        )

    return None  # Continue to classify response


async def skip_if_not_refinement(callback_context):
    """Skip plan_refiner if response is not a refinement request."""
    state = callback_context.state

    # Skip if plan was just presented this turn (no response yet)
    if state.get("plan_presented_this_turn"):
        print(f"⏭️  Skipping plan_refiner - plan was just presented this turn")
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text="")]
        )

    plan_response = state.get("plan_response")

    # Handle None case (reset after new_query or not set yet)
    if plan_response is None:
        print(f"⏭️  Skipping plan_refiner - plan_response is None")
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text="")]
        )

    if hasattr(plan_response, "model_dump"):
        plan_response = plan_response.model_dump()

    response_type = plan_response.get("response_type", "")
    if hasattr(response_type, "value"):
        response_type = response_type.value

    if response_type != "refinement":
        print(f"⏭️  Skipping plan_refiner - response_type is '{response_type}'")
        return types.Content(
            role="model",
            parts=[types.Part.from_text(text="")]
        )
    return None  # Continue to refine plan


async def re_present_plan_after_refinement(callback_context):
    """Re-present the refined plan after plan_refiner updates it."""
    # This is the same as present_plan_callback but also runs after refinement
    return await present_plan_callback(callback_context)


# Wrap metric_planner to skip if plan already exists, present plan after generation
metric_planner_with_callbacks = LlmAgent(
    model=MODEL,
    name="metric_planner",
    description=metric_planner.description,
    instruction=metric_planner.instruction,
    output_schema=metric_planner.output_schema,
    output_key=metric_planner.output_key,
    before_agent_callback=skip_if_plan_exists,
    after_agent_callback=present_plan_callback,  # Presents plan and STOPS
)

# Wrap plan_response_classifier to skip if not pending
plan_response_classifier_with_callbacks = LlmAgent(
    model=MODEL,
    name="plan_response_classifier",
    description=plan_response_classifier.description,
    instruction=plan_response_classifier.instruction,
    output_schema=plan_response_classifier.output_schema,
    output_key=plan_response_classifier.output_key,
    before_agent_callback=skip_if_not_pending,
    after_agent_callback=process_plan_response_callback,
)

# Wrap plan_refiner to skip if not refinement, re-present after refinement
plan_refiner_with_callbacks = LlmAgent(
    model=MODEL,
    name="plan_refiner",
    description=plan_refiner.description,
    instruction=plan_refiner.instruction,
    output_schema=plan_refiner.output_schema,
    output_key=plan_refiner.output_key,
    before_agent_callback=skip_if_not_refinement,
    after_agent_callback=re_present_plan_after_refinement,  # Re-presents and STOPS
)

# HITL Planning Agent - handles the plan → approve → execute flow
hitl_planning_agent = SequentialAgent(
    name="hitl_planning_agent",
    description="""
    Human-In-The-Loop planning stage that:
    1. Generates research plan (if none exists)
    2. Presents plan for user approval
    3. Handles plan refinement requests
    4. Proceeds to execution only after approval

    Plan States:
    - "none": Generate new plan via metric_planner
    - "pending": Waiting for user approval, classify response
    - "approved": Plan approved, skip to pipeline execution
    """,
    before_agent_callback=check_plan_state_callback,
    sub_agents=[
        metric_planner_with_callbacks,           # Generate plan (skipped if exists)
        plan_response_classifier_with_callbacks,  # Classify response (skipped if not pending)
        plan_refiner_with_callbacks,             # Refine plan (skipped if not refinement)
    ],
)


# =============================================================================
# PHASE 2: Updated Pipeline with skip_if_not_approved
# =============================================================================

# Main equity research pipeline (8 stages)
# Now uses skip_if_not_approved_callback to ensure plan is approved before execution
equity_research_pipeline = SequentialAgent(
    name="equity_research_pipeline",
    description="""
    An 8-stage pipeline for comprehensive equity research reports with AI-generated infographics:

    1. Research Planner - Analyzes query, plans metrics to chart (Phase 1 fallback)
    2. Parallel Data Gatherers - 4 concurrent fetchers (financial, valuation, market, news)
    3. Data Consolidator - Merges data into structured format
    4. Chart Generation Loop - Creates multiple charts (one per metric)
    5. Infographic Planner - Plans 2-5 AI-generated infographics (dynamic based on query complexity)
    6. Infographic Generator - Batch generates all infographics in parallel (asyncio.gather)
    7. Analysis Writer - Writes professional narrative sections with Setup→Visual→Interpretation
    8. HTML Report Generator - Creates multi-page report with charts, infographics, and data tables

    Key Features:
    - ParallelAgent for concurrent data fetching (4x faster)
    - LoopAgent for generating multiple charts (5-10 per report)
    - Dynamic infographic count (2-5) based on query complexity
    - Batch parallel infographic generation (asyncio.gather for true parallelism)
    - Callback-based code execution (guaranteed single execution per chart)
    - AI-generated infographics using Gemini 3 Pro Image model (1:1, 2K, white theme)
    - Professional multi-section HTML report with Setup→Visual→Interpretation pattern

    Final Output: equity_report.html + chart_1.png, chart_2.png, ... + infographic_1.png to infographic_5.png
    """,
    before_agent_callback=skip_if_not_approved_callback,  # PHASE 2: Only run if plan approved
    sub_agents=[
        research_planner,               # 1. Plan metrics (Phase 1 fallback if no enhanced plan)
        parallel_data_gatherers,        # 2. Fetch data (parallel)
        data_consolidator,              # 3. Merge & structure
        chart_generation_loop,          # 4. Generate all charts
        infographic_planner,            # 5. Plan 2-5 infographics (dynamic)
        infographic_generator,          # 6. Batch generate all infographics (parallel)
        analysis_writer,                # 7. Write analysis with visual context
        html_report_generator,          # 8. Create HTML report
    ],
)


# =============================================================================
# ROOT AGENT: Complete HITL Flow
# =============================================================================

# Root agent with callback-based routing and HITL planning
# Flow: validator -> classifier -> HITL planning -> pipeline (if approved)
root_agent = SequentialAgent(
    name="equity_research_agent",
    description=f"""
    Professional equity research agent ({APP_NAME}) with Human-In-The-Loop planning.

    Features:
    - Boundary validation (rejects crypto, trading advice, private companies, etc.)
    - Multi-market support (US, India, China, Japan, Korea, Europe)
    - Market auto-detection from query context
    - HITL planning with plan approval before execution
    - Full plan refinement (add/remove metrics, change chart types, time range)

    Flow:
    1. Query Validator → checks boundary rules (crypto, trading advice, etc.)
       - If invalid: responds with rejection message and stops
    2. Query Classifier → classifies as NEW_QUERY/FOLLOW_UP, detects market
       - If FOLLOW_UP with no plan: responds with guidance and stops
    3. HITL Planning → generates plan, presents for approval
       - User can approve, refine, or start over
       - Loop continues until plan is approved
    4. Equity Research Pipeline → generates comprehensive report
       - Only runs after plan is approved

    Example queries:
    - "Analyze Apple stock focusing on financial performance"
    - "Comprehensive analysis of Reliance Industries" (India market detected)
    - "Compare Toyota vs Honda" (Japan market detected)
    - "Generate equity research report for ASML" (Europe market detected)
    """,
    before_agent_callback=ensure_classifier_state_callback,
    sub_agents=[
        query_validator_with_routing,    # Stage 0: Validate + routing callback
        query_classifier_with_routing,   # Stage 1: Classify + routing callback
        hitl_planning_agent,             # Stage 2: HITL Planning (NEW)
        equity_research_pipeline,        # Stages 3-10: Main pipeline (skipped if not approved)
    ],
)


# Export root agent (for adk web app)
__all__ = ["root_agent", "equity_research_pipeline", "hitl_planning_agent"]
