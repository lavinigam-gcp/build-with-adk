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

Architecture:
    17 agents across 9 stages:
    - Stage 0: Query Classification (NEW_QUERY vs FOLLOW_UP)
    - Stage 1: Research Planning
    - Stage 2: Parallel Data Gathering (4 concurrent fetchers)
    - Stage 3: Data Consolidation
    - Stage 4: Chart Generation Loop (LoopAgent)
    - Stage 5: Infographic Planning
    - Stage 6: Infographic Generation (batch parallel)
    - Stage 7: Analysis Writing (Setup→Visual→Interpretation)
    - Stage 8: HTML Report Generation

Final Output:
    - equity_report.html (multi-page report with embedded charts/infographics)
    - chart_1.png, chart_2.png, ... (individual chart artifacts)
    - infographic_1.png, infographic_2.png, ... (individual infographic artifacts)

Usage:
    Run with: adk web app

    The agent expects a natural language query like:
    "Analyze Tesla stock with focus on profitability and valuation"
"""

from google.adk.agents import SequentialAgent

from .sub_agents import (
    query_classifier,
    research_planner,
    parallel_data_gatherers,
    data_consolidator,
    chart_generation_loop,
    infographic_planner,
    infographic_generator,
    analysis_writer,
    html_report_generator,
)
from .callbacks import ensure_classifier_state_callback
from .config import APP_NAME


# Main equity research pipeline (8 stages)
equity_research_pipeline = SequentialAgent(
    name="equity_research_pipeline",
    description="""
    An 8-stage pipeline for comprehensive equity research reports with AI-generated infographics:

    1. Research Planner - Analyzes query, plans metrics to chart
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
    sub_agents=[
        research_planner,               # 1. Plan metrics
        parallel_data_gatherers,        # 2. Fetch data (parallel)
        data_consolidator,              # 3. Merge & structure
        chart_generation_loop,          # 4. Generate all charts
        infographic_planner,            # 5. Plan 2-5 infographics (dynamic)
        infographic_generator,          # 6. Batch generate all infographics (parallel)
        analysis_writer,                # 7. Write analysis with visual context
        html_report_generator,          # 8. Create HTML report
    ],
)


# Root agent with query classification (entry point)
root_agent = SequentialAgent(
    name="equity_research_with_classifier",
    description=f"""
    Professional equity research agent ({APP_NAME}) with intelligent query classification.

    Stage 0: Query Classifier - Classifies user message as NEW_QUERY or FOLLOW_UP
        - NEW_QUERY: Different company → resets visualization state (charts, infographics)
        - FOLLOW_UP: Same company, additional request → preserves state

    Stages 1-8: Standard equity research pipeline

    This enables:
    - Multiple companies analyzed in same session without chart collisions
    - Follow-up queries like "Add Operating Margin chart" preserve existing state
    - Intelligent semantic detection using company name comparison

    Example queries:
    - "Analyze Apple stock focusing on financial performance"
    - "Generate equity research report for Tesla with valuation metrics"
    - "Comprehensive equity analysis of Microsoft including growth trends"
    """,
    before_agent_callback=ensure_classifier_state_callback,
    sub_agents=[
        query_classifier,              # Stage 0: Classify query type
        equity_research_pipeline,      # Stages 1-8: Main pipeline
    ],
)


# Export root agent (for adk web app)
__all__ = ["root_agent"]
