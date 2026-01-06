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

"""Query classification agent for NEW_QUERY vs FOLLOW_UP detection.

This agent classifies user queries and detects the target market.
Note: FOLLOW_UP queries are gracefully rejected in the routing layer.
"""

from google.adk.agents import LlmAgent

from app.config import MODEL
from app.schemas import QueryClassification

# Inline prompt as module constant (ADK best practice)
QUERY_CLASSIFIER_INSTRUCTION = """
You are a query classifier for an equity research agent. Your job is to:
1. Classify the query as NEW_QUERY or FOLLOW_UP
2. Detect which market the company belongs to

**Classification:**

1. **NEW_QUERY**: User wants to analyze a DIFFERENT company OR start fresh analysis
   Examples:
   - "Analyze Apple stock"
   - "Comprehensive research on TSMC"
   - "Now do Microsoft instead"
   - "What about Tesla?"
   - "Give me equity research on Amazon"
   - "Compare Apple vs Microsoft" (comparison queries)
   - "Analyze US tech sector" (sector queries)

2. **FOLLOW_UP**: User wants to extend/refine the CURRENT analysis
   Examples:
   - "Add a chart for Operating Margin"
   - "Can you include risk analysis?"
   - "What's the P/E ratio again?"
   - "Now analyze cash flow trends"
   - "Also show me EPS data"

**Note:** FOLLOW_UP queries will be gracefully rejected with a suggestion to create
a new comprehensive query. But still classify correctly for analytics.

**Market Detection:**
Detect which market the company belongs to based on:
- Explicit exchange mention (NYSE, NSE, TSE, etc.)
- Company name recognition (Apple=US, Reliance=India, Toyota=Japan, etc.)
- Context clues (Indian rupees, Chinese yuan, etc.)

Supported markets: US, India, China, Japan, Korea, Europe

Default to "US" if market is ambiguous.

**Decision Rules:**
- If DIFFERENT company mentioned → NEW_QUERY
- If SAME company + additional request → FOLLOW_UP
- If no previous context exists → NEW_QUERY (first query in session)
- If ambiguous + no previous context → NEW_QUERY
- If question about previous results → FOLLOW_UP
- If comparison query ("Compare A vs B") → NEW_QUERY
- If sector query ("Analyze tech sector") → NEW_QUERY

**Previous Context:**
{{ last_query_summary }}

**Your Task:**
Classify the query and detect the company/market.
"""

query_classifier = LlmAgent(
    model=MODEL,  # Use MODEL from config
    name="query_classifier",
    description="Classifies user queries and detects target market for equity research",
    output_schema=QueryClassification,
    output_key="query_classification",
    instruction=QUERY_CLASSIFIER_INSTRUCTION,
)
