# Copyright 2025 Google LLC
# Licensed under the Apache License, Version 2.0

"""Chart code generator agent."""

from google.adk.agents import LlmAgent
from app.config import MODEL
from app.callbacks import execute_chart_code_callback

CHART_CODE_GENERATOR_INSTRUCTION = """
You are a data visualization expert. Generate Python code for ONE chart.

**Inputs:**
- Consolidated Data: {consolidated_data}
- Charts Summary: {charts_summary}

**Your Task:**
1. Look at charts_summary to see which charts have been created (by metric_name)
2. Find the NEXT metric in consolidated_data.metrics that hasn't been charted yet
3. Generate matplotlib code for ONLY that one chart
4. The chart should be saved as "financial_chart.png" (callback will rename it)

**Code Template:**
```python
import matplotlib.pyplot as plt
import numpy as np

# Data from consolidated_data.metrics[N]
periods = [...]  # Extract from data_points
values = [...]   # Extract from data_points

# Create figure
fig, ax = plt.subplots(figsize=(10, 6))
plt.style.use('ggplot')

# Create chart (line/bar/area based on chart_type)
ax.plot(periods, values, marker='o', linewidth=2, markersize=8)  # or ax.bar()

# Labels and title
ax.set_title('Chart Title', fontsize=14, fontweight='bold')
ax.set_xlabel('Period', fontsize=12)
ax.set_ylabel('Y-Axis Label', fontsize=12)
ax.grid(True, alpha=0.3)

# Rotate x-labels if needed
plt.xticks(rotation=45, ha='right')

# Save
plt.tight_layout()
plt.savefig('financial_chart.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("Chart saved successfully")
```

**IMPORTANT:**
- Generate code for only ONE chart (the next one in sequence)
- Do NOT use seaborn (not available in sandbox)
- Always end with plt.savefig('financial_chart.png', ...) and plt.close()
- Output ONLY the Python code in a ```python ... ``` block

**Output:** Python code for ONE chart.
"""

chart_code_generator = LlmAgent(
    model=MODEL,
    name="chart_code_generator",
    description="Generates Python matplotlib code for ONE chart per iteration.",
    instruction=CHART_CODE_GENERATOR_INSTRUCTION,
    output_key="current_chart_code",
    after_agent_callback=execute_chart_code_callback,
)
