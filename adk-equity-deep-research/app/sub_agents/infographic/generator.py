# Copyright 2025 Google LLC
# Licensed under the Apache License, Version 2.0

"""Infographic generator agent."""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.config import MODEL
from app.tools import generate_all_infographics
from app.callbacks import create_infographics_summary_callback

INFOGRAPHIC_GENERATOR_INSTRUCTION = """
You are an infographic batch generator for professional equity research reports.

**Input:**
- Infographic Plan: {infographic_plan} (contains 2-5 infographic specifications)

**Your Task:**
Call the generate_all_infographics tool ONCE with the entire infographic plan.

The tool will:
1. Extract all infographics from the plan (2, 3, 4, or 5 infographics)
2. Generate ALL of them in parallel using asyncio.gather()
3. Save each as an artifact (infographic_1.png, infographic_2.png, etc.)
4. Store results in state["infographics_generated"]

**CRITICAL INSTRUCTIONS:**
- Call the tool EXACTLY ONCE
- Do NOT retry or make multiple calls
- The tool handles all infographics automatically
- Pass the ENTIRE infographic_plan as parameter

**Output:** Confirmation message with count of successfully generated infographics.
"""

infographic_generator = LlmAgent(
    model=MODEL,
    name="infographic_generator",
    description="Generates all planned infographics (2-5) in parallel using batch generation tool.",
    instruction=INFOGRAPHIC_GENERATOR_INSTRUCTION,
    tools=[FunctionTool(generate_all_infographics)],
    after_agent_callback=create_infographics_summary_callback,
)
