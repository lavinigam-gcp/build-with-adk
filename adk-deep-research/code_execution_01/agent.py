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

"""
Financial Data Visualization Agent
==================================

A multi-stage agent pipeline that:
1. Fetches real-time financial data via Google Search
2. Extracts structured data points from search results
3. Generates visual charts using matplotlib
4. Returns summary with chart visualization

Architecture: SequentialAgent with 4 sub-agents

Sandbox Configuration:
- If SANDBOX_RESOURCE_NAME env var is set, uses AgentEngineSandboxCodeExecutor
  (pre-created sandbox for faster execution)
- Otherwise, uses VertexAiCodeExecutor (creates sandbox on-demand)
"""

import datetime
import os
from typing import Literal

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.code_executors.vertex_ai_code_executor import VertexAiCodeExecutor
from google.adk.tools import google_search
from pydantic import BaseModel, Field


# --- Configuration ---
MODEL = "gemini-2.5-flash"
CURRENT_DATE = datetime.datetime.now().strftime("%Y-%m-%d")

# Check if a pre-created sandbox is available
SANDBOX_RESOURCE_NAME = os.environ.get("SANDBOX_RESOURCE_NAME")


def get_code_executor():
    """Get the appropriate code executor based on configuration.

    If SANDBOX_RESOURCE_NAME is set, uses AgentEngineSandboxCodeExecutor
    for faster execution with a pre-created sandbox.
    Otherwise, uses VertexAiCodeExecutor which creates sandbox on-demand.
    """
    if SANDBOX_RESOURCE_NAME:
        from google.adk.code_executors.agent_engine_sandbox_code_executor import (
            AgentEngineSandboxCodeExecutor,
        )

        print(f"Using pre-created sandbox: {SANDBOX_RESOURCE_NAME}")
        return AgentEngineSandboxCodeExecutor(
            sandbox_resource_name=SANDBOX_RESOURCE_NAME
        )
    else:
        print("Using VertexAiCodeExecutor (sandbox created on-demand)")
        return VertexAiCodeExecutor()


# --- Structured Output Models ---

class DataPoint(BaseModel):
    """A single financial data point."""

    period: str = Field(
        description="Time period (e.g., '2023', 'Q1 2024', 'Jan 2024')"
    )
    value: float = Field(
        description="Numeric value for this period"
    )
    unit: str = Field(
        default="USD",
        description="Unit of measurement (USD, %, millions, billions, etc.)"
    )


class FinancialDataExtraction(BaseModel):
    """Structured financial data extracted from search results."""

    entity: str = Field(
        description="Company, index, or entity name (e.g., 'Google', 'S&P 500')"
    )
    metric: str = Field(
        description="Financial metric being measured (e.g., 'Revenue', 'Stock Price', 'Net Income')"
    )
    data_points: list[DataPoint] = Field(
        description="List of data points with period and value"
    )
    chart_type: Literal["line", "bar", "area"] = Field(
        default="line",
        description="Recommended chart type: 'line' for trends over time, 'bar' for comparisons, 'area' for cumulative data"
    )
    chart_title: str = Field(
        description="Descriptive title for the chart"
    )
    y_axis_label: str = Field(
        description="Label for the Y-axis (e.g., 'Revenue (Billions USD)')"
    )
    data_source: str = Field(
        default="Google Search",
        description="Primary source of the data"
    )
    notes: str | None = Field(
        default=None,
        description="Any important notes or caveats about the data"
    )


# --- Agent Definitions ---

# Stage 1: Data Fetcher Agent
# Uses Google Search to find financial data based on user query
data_fetcher_agent = LlmAgent(
    model=MODEL,
    name="data_fetcher",
    description="Searches the web for financial data based on user queries using Google Search grounding.",
    instruction=f"""
You are a financial data researcher. Your job is to search for financial data based on the user's query.

**Current Date:** {CURRENT_DATE}

**Your Task:**
1. Analyze the user's query to understand what financial data they need
2. Use the google_search tool to find the most relevant and recent financial data
3. Search for specific numeric data points (revenue, stock prices, earnings, etc.)
4. If the query asks for historical data (e.g., "last 5 years"), ensure you find data for each period

**Search Strategy:**
- For company financials: Search "[Company] [metric] [year range]" (e.g., "Google revenue 2020 2021 2022 2023 2024")
- For stock data: Search "[Company] stock price history [period]"
- For market indices: Search "[Index name] performance [period]"
- Include "annual report" or "quarterly earnings" for official data

**Output:**
Provide a comprehensive summary of the financial data you found, including:
- All numeric values with their time periods
- Sources of the information
- Any relevant context or trends

Be thorough - the next agent will extract structured data from your findings.
""",
    tools=[google_search],
    output_key="raw_financial_data",
)


# Stage 2: Data Extractor Agent
# Extracts structured data points from the raw search results
data_extractor_agent = LlmAgent(
    model=MODEL,
    name="data_extractor",
    description="Extracts structured financial data points from raw search results.",
    instruction="""
You are a data extraction specialist. Your job is to convert unstructured financial data into a clean, structured format.

**Input:** You will receive raw financial data from a previous search in `{raw_financial_data}`

**Your Task:**
1. Identify the main entity (company, index, etc.) and metric being discussed
2. Extract ALL numeric data points with their corresponding time periods
3. Determine the best chart type for visualizing this data:
   - `line`: For trends over time (stock prices, revenue growth)
   - `bar`: For period-by-period comparisons (quarterly earnings)
   - `area`: For cumulative or stacked data
4. Create a descriptive chart title and axis label

**Data Extraction Rules:**
- Convert all values to consistent units (e.g., all in billions or all in millions)
- Ensure periods are in chronological order
- If data is missing for some periods, note this in the 'notes' field
- Round values appropriately (2 decimal places for billions, whole numbers for stock prices)

**Output Format:**
Your response must be a valid JSON object matching the FinancialDataExtraction schema.
""",
    output_schema=FinancialDataExtraction,
    output_key="structured_data",
)


# Stage 3: Visualization Agent
# Generates matplotlib code to create the chart and saves it as an artifact
visualization_agent = LlmAgent(
    model=MODEL,
    name="visualizer",
    description="Generates Python code to create financial data visualizations using matplotlib.",
    instruction="""
You are a data visualization expert. Your job is to create professional-quality financial charts.

**Input:** You will receive structured financial data in `{structured_data}`

**Your Task:**
Generate Python code using matplotlib to create a visualization based on the data.

**CRITICAL - Code Requirements:**
1. You MUST explicitly import ALL libraries at the top of your code:
   ```python
   import matplotlib.pyplot as plt
   import numpy as np
   import pandas as pd
   ```

   NOTE: The sandbox does NOT have seaborn pre-installed. Use matplotlib only for styling.
   Do NOT use seaborn (sns) - it will cause errors.

2. Parse the structured data and create the appropriate chart type

3. Chart Styling Guidelines (using matplotlib only):
   - Use plt.style.use('ggplot') or plt.style.use('seaborn-v0_8-whitegrid') for clean styling
   - Set figure size to (12, 6) for good readability
   - Include a descriptive title with appropriate font size
   - Label both axes clearly
   - Add data labels on the chart where appropriate
   - Use a consistent color scheme (use matplotlib colors like '#1f77b4', '#2ca02c', etc.)
   - Add a subtle grid for readability: ax.grid(True, alpha=0.3)
   - Include a legend if multiple series

4. For different chart types:
   - LINE: ax.plot() with markers for data points, smooth lines
   - BAR: ax.bar() with appropriate width, consider horizontal for long labels
   - AREA: ax.fill_between() with transparency (alpha=0.7), show line on top

5. Save the figure:
   ```python
   plt.tight_layout()
   plt.savefig('financial_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
   plt.close()
   ```

6. Print confirmation: `print("Chart saved as financial_chart.png")`

**Example Code Structure:**
```python
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Parse the data (structured_data is already a dict)
data = {structured_data}
periods = [dp['period'] for dp in data['data_points']]
values = [dp['value'] for dp in data['data_points']]

# Create the chart with styling
plt.style.use('ggplot')
fig, ax = plt.subplots(figsize=(12, 6))

# Plot based on chart type (line example)
ax.plot(periods, values, marker='o', linewidth=2, markersize=8, color='#1f77b4')

# Styling
ax.set_title(data['chart_title'], fontsize=16, fontweight='bold')
ax.set_xlabel('Period', fontsize=12)
ax.set_ylabel(data['y_axis_label'], fontsize=12)
ax.grid(True, alpha=0.3)

# Add value labels
for i, (x, y) in enumerate(zip(periods, values)):
    ax.annotate(f'{y:.1f}', (x, y), textcoords="offset points",
                xytext=(0,10), ha='center', fontsize=9)

plt.tight_layout()
plt.savefig('financial_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("Chart saved as financial_chart.png")
```

IMPORTANT: Always import matplotlib.pyplot, numpy, and pandas at the top. Never use seaborn.
Generate the complete code to create and save the visualization.
""",
    code_executor=get_code_executor(),
    output_key="visualization_result",
)


# Stage 4: Summary Agent
# Creates a final summary combining insights with the visualization
summary_agent = LlmAgent(
    model=MODEL,
    name="summarizer",
    description="Creates a comprehensive summary of the financial data analysis with key insights.",
    instruction="""
You are a financial analyst. Your job is to create a clear, insightful summary of the financial data analysis.

**Inputs Available:**
- Raw financial data: `{raw_financial_data}`
- Structured data: `{structured_data}`
- Visualization result: `{visualization_result}`

**Your Task:**
Create a professional summary that includes:

1. **Overview** (2-3 sentences)
   - What data was analyzed
   - Time period covered
   - Key entity/metric

2. **Key Findings** (3-5 bullet points)
   - Notable trends (growth, decline, stability)
   - Significant changes between periods
   - Comparisons to industry or expectations if relevant

3. **Data Summary**
   - Highest and lowest values
   - Average or total if meaningful
   - Growth rate (if applicable)

4. **Chart Description**
   - Mention that a chart has been generated
   - Briefly describe what the chart shows

5. **Sources & Caveats**
   - Note the data source
   - Any limitations or caveats mentioned

**Format:**
Use clear markdown formatting with headers, bullet points, and emphasis where appropriate.
Keep the summary concise but informative - aim for 200-300 words.
""",
    output_key="final_summary",
)


# --- Main Pipeline ---

# Combine all agents into a sequential pipeline
financial_data_pipeline = SequentialAgent(
    name="financial_data_visualization_pipeline",
    description="""
    A multi-stage pipeline for financial data visualization:
    1. Fetches data via Google Search
    2. Extracts structured data points
    3. Generates chart visualization
    4. Creates summary with insights
    """,
    sub_agents=[
        data_fetcher_agent,
        data_extractor_agent,
        visualization_agent,
        summary_agent,
    ],
)


# Root agent - entry point
root_agent = financial_data_pipeline
