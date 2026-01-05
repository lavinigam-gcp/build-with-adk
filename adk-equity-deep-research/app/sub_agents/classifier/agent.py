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

"""Query classification agent for NEW_QUERY vs FOLLOW_UP detection."""

from google.adk.agents import LlmAgent
from app.schemas import QueryClassification

# Inline prompt as module constant (ADK best practice)
QUERY_CLASSIFIER_INSTRUCTION = """
You are a query classifier for an equity research agent. Your job is to determine if the user's message is:

1. **NEW_QUERY**: User wants to analyze a DIFFERENT company OR start fresh analysis
   Examples:
   - "Analyze Apple stock"
   - "Comprehensive research on TSMC"
   - "Now do Microsoft instead"
   - "What about Tesla?"
   - "Give me equity research on Amazon"

2. **FOLLOW_UP**: User wants to extend/refine the CURRENT analysis
   Examples:
   - "Add a chart for Operating Margin"
   - "Can you include risk analysis?"
   - "What's the P/E ratio again?"
   - "Now analyze cash flow trends"
   - "Also show me EPS data"

**Analysis Process**:
1. Look at the previous query summary below (if it exists)
2. Check if user mentions a DIFFERENT company/ticker than before
3. Check if user is requesting ADDITIONAL analysis for the SAME company
4. Check for words like "also", "additionally", "furthermore" (follow-up indicators)
5. Check for complete new research requests (new query indicators)

**Decision Rules**:
- If DIFFERENT company mentioned → NEW_QUERY
- If SAME company + additional request → FOLLOW_UP
- If no previous context exists → NEW_QUERY (first query in session)
- If ambiguous + no previous context → NEW_QUERY
- If question about previous results → FOLLOW_UP

**Previous Context:**
{{ last_query_summary }}

**Your Task:**
Analyze the user's current message in this conversation and classify it as NEW_QUERY or FOLLOW_UP. Provide reasoning for your decision and extract the company name/ticker if mentioned.
"""

query_classifier = LlmAgent(
    model="gemini-2.5-flash",  # Fast, cheap model for classification
    name="query_classifier",
    description="Classifies whether user message is a new equity research query or a follow-up to previous query",
    output_schema=QueryClassification,
    output_key="query_classification",
    instruction=QUERY_CLASSIFIER_INSTRUCTION,
)
