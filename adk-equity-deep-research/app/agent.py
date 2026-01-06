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
    The agent uses callback-based routing with boundary validation:
    - Stage 0: Query Validation (rejects crypto, trading advice, etc.)
    - Stage 1: Query Classification (NEW_QUERY vs FOLLOW_UP with market detection)
    - Stages 2-9: Research pipeline (only runs for valid NEW_QUERY)

    Routing is handled by after_agent_callbacks that check state and can
    stop the pipeline by returning a response Content.

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

from .config import APP_NAME, MODEL
from .sub_agents import (
    query_validator,
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
from .callbacks import (
    ensure_classifier_state_callback,
    check_validation_callback,
    check_classification_callback,
    skip_if_rejected_callback,
)


# Create wrapped versions of validator and classifier with routing callbacks
# These callbacks check results and can stop the pipeline if needed

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


# Main equity research pipeline (8 stages)
# Wrapped with skip_if_rejected_callback to skip if validation/classification failed
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
    before_agent_callback=skip_if_rejected_callback,
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


# Root agent with callback-based routing
# Flow: validator -> (check) -> classifier -> (check) -> pipeline
root_agent = SequentialAgent(
    name="equity_research_agent",
    description=f"""
    Professional equity research agent ({APP_NAME}) with intelligent routing.

    Features:
    - Boundary validation (rejects crypto, trading advice, private companies, etc.)
    - Multi-market support (US, India, China, Japan, Korea, Europe)
    - Market auto-detection from query context
    - FOLLOW_UP queries gracefully rejected with guidance

    Flow:
    1. Query Validator → checks boundary rules (crypto, trading advice, etc.)
       - If invalid: responds with rejection message and stops
    2. Query Classifier → classifies as NEW_QUERY/FOLLOW_UP, detects market
       - If FOLLOW_UP: responds with guidance and stops
    3. Equity Research Pipeline → generates comprehensive report
       - Only runs for valid NEW_QUERY

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
        equity_research_pipeline,        # Stages 2-9: Main pipeline (skipped if rejected)
    ],
)


# Export root agent (for adk web app)
__all__ = ["root_agent", "equity_research_pipeline"]
