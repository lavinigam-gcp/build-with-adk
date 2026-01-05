# Copyright 2025 Google LLC
# Licensed under the Apache License, Version 2.0

"""Custom progress checker agent for chart generation loop."""

from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.genai import types


class ChartProgressChecker(BaseAgent):
    """Custom agent that checks if all charts have been generated.

    This agent runs after each chart generation iteration and:
    - Compares charts_generated count vs metrics count in consolidated data
    - Escalates (exits loop) when all charts are done
    - Otherwise, allows loop to continue
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Check progress and escalate if all charts generated."""

        state = ctx.session.state

        # Get planned metrics count
        consolidated = state.get("consolidated_data")
        planned_count = 0
        if consolidated:
            if isinstance(consolidated, dict):
                planned_count = len(consolidated.get("metrics", []))
            elif hasattr(consolidated, "metrics"):
                planned_count = len(consolidated.metrics)

        # Get generated charts count
        charts_generated = state.get("charts_generated", [])
        generated_count = len(charts_generated)

        print(f"Chart progress: {generated_count}/{planned_count}")

        # Check if all done
        all_done = generated_count >= planned_count and planned_count > 0

        if all_done:
            print("All charts generated - escalating to exit loop")

        yield Event(
            author=self.name,
            content=types.Content(
                parts=[types.Part(text=f"Progress: {generated_count}/{planned_count} charts. {'Complete!' if all_done else 'Continuing...'}")],
                role="model"
            ),
            actions=EventActions(escalate=all_done)
        )
