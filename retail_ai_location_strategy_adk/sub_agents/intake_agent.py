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

"""Intake Agent - Extracts target location and business type from user request.

This agent parses the user's natural language request and extracts the
required parameters (target_location, business_type) into session state
for use by subsequent agents in the pipeline.
"""

from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from pydantic import BaseModel, Field

from ..config import FAST_MODEL, RETRY_INITIAL_DELAY, RETRY_ATTEMPTS


class UserRequest(BaseModel):
    """Structured output for parsing user's location strategy request."""

    target_location: str = Field(
        description="The geographic location/area to analyze (e.g., 'Indiranagar, Bangalore', 'Manhattan, New York')"
    )
    business_type: str = Field(
        description="The type of business the user wants to open (e.g., 'coffee shop', 'bakery', 'gym', 'restaurant')"
    )
    additional_context: Optional[str] = Field(
        default=None,
        description="Any additional context or requirements mentioned by the user"
    )


def after_intake(callback_context: CallbackContext) -> Optional[types.Content]:
    """After intake, copy the parsed values to state for other agents."""
    parsed = callback_context.state.get("parsed_request", {})

    if isinstance(parsed, dict):
        # Extract values from parsed request
        callback_context.state["target_location"] = parsed.get("target_location", "")
        callback_context.state["business_type"] = parsed.get("business_type", "")
        callback_context.state["additional_context"] = parsed.get("additional_context", "")
    elif hasattr(parsed, "target_location"):
        # Handle Pydantic model
        callback_context.state["target_location"] = parsed.target_location
        callback_context.state["business_type"] = parsed.business_type
        callback_context.state["additional_context"] = parsed.additional_context or ""

    # Track intake stage completion
    stages = callback_context.state.get("stages_completed", [])
    stages.append("intake")
    callback_context.state["stages_completed"] = stages

    # Note: current_date is set in each agent's before_callback to ensure it's always available
    return None


INTAKE_INSTRUCTION = """You are a request parser for a retail location intelligence system.

Your task is to extract the target location and business type from the user's request.

## Examples

User: "I want to open a coffee shop in Indiranagar, Bangalore"
→ target_location: "Indiranagar, Bangalore"
→ business_type: "coffee shop"

User: "Analyze the market for a new gym in downtown Seattle"
→ target_location: "downtown Seattle"
→ business_type: "gym"

User: "Help me find the best location for a bakery in Mumbai"
→ target_location: "Mumbai"
→ business_type: "bakery"

User: "Where should I open my restaurant in San Francisco's Mission District?"
→ target_location: "Mission District, San Francisco"
→ business_type: "restaurant"

## Instructions
1. Extract the geographic location mentioned by the user
2. Identify the type of business they want to open
3. Note any additional context or requirements

If the user doesn't specify a clear location or business type, make a reasonable inference or ask for clarification.
"""

intake_agent = LlmAgent(
    name="IntakeAgent",
    model=FAST_MODEL,
    description="Parses user request to extract target location and business type",
    instruction=INTAKE_INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                initial_delay=RETRY_INITIAL_DELAY,
                attempts=RETRY_ATTEMPTS,
            ),
        ),
    ),
    output_schema=UserRequest,
    output_key="parsed_request",
    after_agent_callback=after_intake,
)
