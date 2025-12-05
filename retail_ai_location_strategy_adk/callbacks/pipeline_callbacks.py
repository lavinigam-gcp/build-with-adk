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

"""Pipeline callbacks for logging, state tracking, and artifact management.

This module provides before/after callbacks for each agent in the
Location Strategy Pipeline. Callbacks handle:
- Logging stage transitions
- Tracking pipeline progress in state
- Saving artifacts (JSON report, HTML report, infographic)
"""

import json
import logging
from datetime import datetime
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("LocationStrategyPipeline")


# ============================================================================
# BEFORE AGENT CALLBACKS
# ============================================================================

def before_market_research(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log start of market research phase and initialize pipeline tracking."""
    logger.info("=" * 60)
    logger.info("STAGE 1: MARKET RESEARCH - Starting")
    logger.info(f"  Target Location: {callback_context.state.get('target_location', 'Not set')}")
    logger.info(f"  Business Type: {callback_context.state.get('business_type', 'Not set')}")
    logger.info("=" * 60)

    # Set current date for state injection in agent instruction
    callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d")

    # Initialize pipeline tracking
    callback_context.state["pipeline_stage"] = "market_research"
    callback_context.state["pipeline_start_time"] = datetime.now().isoformat()
    # Don't reset stages_completed - intake stage may already be tracked
    if "stages_completed" not in callback_context.state:
        callback_context.state["stages_completed"] = []

    return None  # Allow agent to proceed


def before_competitor_mapping(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log start of competitor mapping phase."""
    logger.info("=" * 60)
    logger.info("STAGE 2A: COMPETITOR MAPPING - Starting")
    logger.info("  Using Google Maps Places API for real competitor data...")
    logger.info("=" * 60)

    # Set current date for state injection in agent instruction
    callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d")
    callback_context.state["pipeline_stage"] = "competitor_mapping"

    # Workaround for AG-UI middleware issue: initialize state variable
    # The middleware may end agent prematurely after tool calls, preventing output_key from being set
    if "competitor_analysis" not in callback_context.state:
        callback_context.state["competitor_analysis"] = "Competitor data being collected via Google Maps API..."

    return None


def before_gap_analysis(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log start of gap analysis phase."""
    logger.info("=" * 60)
    logger.info("STAGE 2B: GAP ANALYSIS - Starting")
    logger.info("  Executing Python code for quantitative market analysis...")
    logger.info("=" * 60)

    # Set current date for state injection in agent instruction
    callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d")
    callback_context.state["pipeline_stage"] = "gap_analysis"

    # Workaround for AG-UI middleware issue: initialize state variable
    if "gap_analysis" not in callback_context.state:
        callback_context.state["gap_analysis"] = "Gap analysis being computed..."

    return None


def before_strategy_advisor(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log start of strategy synthesis phase."""
    logger.info("=" * 60)
    logger.info("STAGE 3: STRATEGY SYNTHESIS - Starting")
    logger.info("  Using extended reasoning with thinking mode...")
    logger.info("  Generating structured LocationIntelligenceReport...")
    logger.info("=" * 60)

    # Set current date for state injection in agent instruction
    callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d")
    callback_context.state["pipeline_stage"] = "strategy_synthesis"

    return None


def before_report_generator(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log start of report generation phase."""
    logger.info("=" * 60)
    logger.info("STAGE 4: REPORT GENERATION - Starting")
    logger.info("  Generating McKinsey/BCG style HTML executive report...")
    logger.info("=" * 60)

    # Set current date for state injection in agent instruction
    callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d")
    callback_context.state["pipeline_stage"] = "report_generation"

    return None


def before_infographic_generator(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log start of infographic generation phase."""
    logger.info("=" * 60)
    logger.info("STAGE 5: INFOGRAPHIC GENERATION - Starting")
    logger.info("  Calling Gemini image generation API...")
    logger.info("=" * 60)

    # Set current date for state injection in agent instruction
    callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d")
    callback_context.state["pipeline_stage"] = "infographic_generation"

    return None


# ============================================================================
# AFTER AGENT CALLBACKS
# ============================================================================

def after_market_research(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log completion of market research and update tracking."""
    findings = callback_context.state.get("market_research_findings", "")
    findings_len = len(findings) if isinstance(findings, str) else 0

    logger.info(f"STAGE 1: COMPLETE - Market research findings: {findings_len} characters")

    # Update stages completed
    stages = callback_context.state.get("stages_completed", [])
    stages.append("market_research")
    callback_context.state["stages_completed"] = stages

    return None


def after_competitor_mapping(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log completion of competitor mapping."""
    analysis = callback_context.state.get("competitor_analysis", "")
    analysis_len = len(analysis) if isinstance(analysis, str) else 0

    logger.info(f"STAGE 2A: COMPLETE - Competitor analysis: {analysis_len} characters")

    stages = callback_context.state.get("stages_completed", [])
    stages.append("competitor_mapping")
    callback_context.state["stages_completed"] = stages

    return None


def after_gap_analysis(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log completion of gap analysis and extract executed Python code."""
    gap = callback_context.state.get("gap_analysis", "")
    gap_len = len(gap) if isinstance(gap, str) else 0

    logger.info(f"STAGE 2B: COMPLETE - Gap analysis: {gap_len} characters")

    # Extract Python code from the gap_analysis content first
    extracted_code = _extract_python_code_from_content(gap)

    # Try to extract from invocation context (BuiltInCodeExecutor uses executable_code parts)
    if not extracted_code:
        extracted_code = _extract_code_from_invocation(callback_context)

    if extracted_code:
        callback_context.state["gap_analysis_code"] = extracted_code
        logger.info(f"  Extracted Python code: {len(extracted_code)} characters")
    else:
        logger.info("  No Python code blocks found to extract")

    stages = callback_context.state.get("stages_completed", [])
    stages.append("gap_analysis")
    callback_context.state["stages_completed"] = stages

    return None


def _extract_code_from_invocation(callback_context: CallbackContext) -> str:
    """Extract Python code from invocation context session events."""
    code_blocks = []

    try:
        # Access via the private _invocation_context as shown in ADK docs
        invocation = getattr(callback_context, '_invocation_context', None) or \
                     getattr(callback_context, 'invocation_context', None)

        if not invocation:
            logger.debug("No invocation context available")
            return ""

        # Access session from invocation context
        session = getattr(invocation, 'session', None)
        if not session:
            logger.debug("No session in invocation context")
            return ""

        # Get events from session
        events = getattr(session, 'events', None) or []
        logger.debug(f"Found {len(events)} events in session")

        for event in events:
            # Get content from event
            content = getattr(event, 'content', None)
            if not content:
                continue

            # Get parts from content
            parts = getattr(content, 'parts', None) or []
            for part in parts:
                # Check for executable_code (Gemini native code execution)
                exec_code = getattr(part, 'executable_code', None)
                if exec_code:
                    code = getattr(exec_code, 'code', None)
                    if code and code.strip():
                        code_blocks.append(code.strip())
                        logger.debug(f"Found executable_code: {len(code)} chars")

        if code_blocks:
            logger.info(f"  Found {len(code_blocks)} code blocks from session events")

    except Exception as e:
        logger.warning(f"Error extracting code from invocation context: {e}")
        import traceback
        logger.debug(traceback.format_exc())

    return "\n\n# --- Next Code Block ---\n\n".join(code_blocks)


def _extract_python_code_from_content(content: str) -> str:
    """Extract Python code blocks from markdown content."""
    import re

    if not content:
        return ""

    # Match fenced code blocks with python language specifier
    code_blocks = []
    pattern = r'```(?:python|py)\s*\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

    for match in matches:
        code = match.strip()
        if code:
            code_blocks.append(code)

    return "\n\n# ---\n\n".join(code_blocks)


def after_strategy_advisor(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log completion and save JSON artifact."""
    report = callback_context.state.get("strategic_report", {})
    logger.info("STAGE 3: COMPLETE - Strategic report generated")

    # Save JSON artifact
    if report:
        try:
            # Handle both dict and Pydantic model
            if hasattr(report, "model_dump"):
                report_dict = report.model_dump()
            else:
                report_dict = report

            json_str = json.dumps(report_dict, indent=2, default=str)
            json_artifact = types.Part.from_bytes(
                data=json_str.encode('utf-8'),
                mime_type="application/json"
            )
            callback_context.save_artifact("intelligence_report.json", json_artifact)
            logger.info("  Saved artifact: intelligence_report.json")
        except Exception as e:
            logger.warning(f"  Failed to save JSON artifact: {e}")

    stages = callback_context.state.get("stages_completed", [])
    stages.append("strategy_synthesis")
    callback_context.state["stages_completed"] = stages

    return None


def after_report_generator(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log completion of report generation.

    Note: The artifact is now saved directly in the generate_html_report tool
    using tool_context.save_artifact(). This callback just logs completion.
    """
    # The report_generation_result from output_key contains the LLM's text response,
    # not the tool's return dict. The artifact is saved directly in the tool.
    logger.info("STAGE 4: COMPLETE - HTML report generation finished")
    logger.info("  (Artifact saved directly by generate_html_report tool)")

    stages = callback_context.state.get("stages_completed", [])
    stages.append("report_generation")
    callback_context.state["stages_completed"] = stages

    return None


def after_infographic_generator(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log completion of infographic generation.

    Note: The artifact is now saved directly in the generate_infographic tool
    using tool_context.save_artifact(). This callback just logs completion.
    """
    # The infographic_result from output_key contains the LLM's text response,
    # not the tool's return dict. The artifact is saved directly in the tool.
    logger.info("STAGE 5: COMPLETE - Infographic generation finished")
    logger.info("  (Artifact saved directly by generate_infographic tool)")

    stages = callback_context.state.get("stages_completed", [])
    stages.append("infographic_generation")
    callback_context.state["stages_completed"] = stages

    # Log final pipeline summary
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"  Stages completed: {stages}")
    logger.info(f"  Total stages: {len(stages)}/7")
    logger.info("=" * 60)

    return None
