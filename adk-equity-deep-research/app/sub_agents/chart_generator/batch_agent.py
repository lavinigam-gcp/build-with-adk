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

"""Batch chart code generator agent.

This agent generates a single Python script that creates ALL charts at once,
providing ~5-10x speedup compared to the sequential LoopAgent approach.

Key differences from sequential agent.py:
- Generates code for ALL charts in one script
- Uses a loop with try/except per chart for fault tolerance
- Saves as chart_1.png, chart_2.png, etc.
- Single LLM call + single sandbox execution
"""

from google.adk.agents import LlmAgent
from app.config import MODEL
from app.callbacks import execute_batch_charts_callback


BATCH_CHART_CODE_GENERATOR_INSTRUCTION = """
You are a data visualization expert. Generate Python code that creates ALL charts in a single script.

**Inputs:**
- Consolidated Data: {consolidated_data}

**Your Task:**
Generate a complete Python script that creates ALL charts for the metrics in consolidated_data.

**CRITICAL REQUIREMENTS:**
1. Generate ONE script that creates ALL charts (chart_1.png through chart_N.png)
2. Loop through all metrics and create a chart for each one
3. Use try/except around each chart so one failure doesn't stop others
4. Call plt.close() after saving each chart to prevent memory issues
5. Print success/error messages for each chart
6. Do NOT use seaborn (not available in sandbox)

**Code Structure:**
```python
import matplotlib.pyplot as plt
import numpy as np

plt.style.use('ggplot')

def create_chart(metric_data, chart_index):
    '''Create and save a single chart.'''
    try:
        # Extract metric_name, chart_type, data_points from metric_data
        # Parse periods and values from data_points list

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))

        # Create chart based on chart_type (line, bar, or area)
        # Add appropriate styling, labels, title

        # Save as chart_N.png where N is chart_index
        plt.savefig('chart_N.png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        print("Saved chart_N.png")
        return True
    except Exception as e:
        print("Error creating chart N")
        plt.close('all')
        return False

# Parse consolidated_data to get metrics list
# Loop through metrics with enumerate starting at 1
# Call create_chart for each metric
# Print summary of success/failure counts
```

**Chart Type Handling:**
- line: ax.plot() with markers
- bar: ax.bar() with value labels
- area: ax.fill_between() with line overlay

**File Naming:**
- First chart: chart_1.png
- Second chart: chart_2.png
- And so on...

**IMPORTANT:**
- Extract the metrics list from consolidated_data (it's a dict with 'metrics' key)
- Each metric has: metric_name, chart_type, data_points, section
- Each data_point has: period, value, unit
- Always close figures with plt.close() after saving
- Print clear messages showing which chart was saved

**Output:** A complete Python script in a ```python ... ``` block that generates ALL charts.
"""


batch_chart_generator = LlmAgent(
    model=MODEL,
    name="batch_chart_generator",
    description="Generates Python code that creates ALL charts in a single script execution.",
    instruction=BATCH_CHART_CODE_GENERATOR_INSTRUCTION,
    output_key="all_charts_code",
    after_agent_callback=execute_batch_charts_callback,
)
