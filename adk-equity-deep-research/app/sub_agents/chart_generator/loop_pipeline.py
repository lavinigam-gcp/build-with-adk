# Copyright 2025 Google LLC
# Licensed under the Apache License, Version 2.0

"""Chart generation loop pipeline."""

from google.adk.agents import LoopAgent
from app.config import MAX_CHART_ITERATIONS
from .agent import chart_code_generator
from .progress_checker import ChartProgressChecker

chart_generation_loop = LoopAgent(
    name="chart_generation_loop",
    description="Iterates through metrics, generating one chart per iteration until all done.",
    max_iterations=MAX_CHART_ITERATIONS,
    sub_agents=[
        chart_code_generator,
        ChartProgressChecker(name="chart_progress_checker"),
    ],
)
