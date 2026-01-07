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

"""Plan response classifier agent for HITL planning flow.

This agent classifies the user's response to a presented research plan:
- APPROVAL: User wants to proceed with the plan
- REFINEMENT: User wants to modify the plan
- NEW_QUERY: User wants to analyze a different company

Phase 2 HITL Flow:
    After plan is presented (plan_state="pending"):
    1. User responds
    2. plan_response_classifier classifies response
    3. Based on classification:
       - APPROVAL -> set approved, continue to pipeline
       - REFINEMENT -> plan_refiner modifies plan, re-present
       - NEW_QUERY -> reset state, start fresh
"""

from google.adk.agents import LlmAgent
from app.config import MODEL
from app.schemas import PlanResponseClassification


PLAN_RESPONSE_CLASSIFIER_INSTRUCTION = """
You are classifying the user's response to a research plan that was just presented.

**APPROVAL - User wants to proceed (response_type: "approval"):**
Natural language phrases indicating approval:
- "looks good", "that's good", "good to go"
- "approved", "approve", "approve it"
- "proceed", "go ahead", "let's go", "start"
- "yes", "ok", "okay", "sure", "yep", "yeah"
- "execute", "run it", "do it", "start the analysis"
- "perfect", "great", "excellent", "fine"
- "that works", "that's fine", "all good"
- "👍", "✓", "confirmed"
- Single word affirmations

**REFINEMENT - User wants to modify the plan (response_type: "refinement"):**
Phrases indicating modification request:
- "add X", "include X", "also add X"
- "remove X", "don't need X", "skip X", "drop X"
- "change X to Y", "use Y instead of X"
- "change chart type", "use bar chart", "use line chart"
- "make it 3 years", "5 year analysis", "extend to 10 years"
- "add more metrics", "fewer metrics"
- "focus on valuation", "emphasize growth"
- Questions like "can you add...?", "could you include...?"

For REFINEMENT, extract the specific change request into refinement_request field.

**NEW_QUERY - User wants to analyze something else (response_type: "new_query"):**
Indicators of a completely new request:
- Different company mentioned
- "analyze X instead", "forget that, do Y"
- "actually, I want to look at Z"
- "let's do something else"
- Complete topic change
- New stock symbol or company name

**CURRENT PLAN CONTEXT:**
{{ enhanced_research_plan }}

The plan above was presented to the user. Now classify their response.

**CLASSIFICATION GUIDELINES:**
1. When in doubt between APPROVAL and REFINEMENT, lean toward APPROVAL if the message is brief and positive
2. If the user asks a question about the plan without requesting changes, treat as APPROVAL
3. Any mention of a different company/stock = NEW_QUERY
4. For REFINEMENT, be specific about what change is requested in refinement_request

**OUTPUT:**
Return PlanResponseClassification with:
- response_type: approval, refinement, or new_query
- reasoning: Brief explanation of classification
- refinement_request: (only for REFINEMENT) What specific change the user wants
"""


plan_response_classifier = LlmAgent(
    model=MODEL,
    name="plan_response_classifier",
    description="Classifies user response to plan: APPROVAL, REFINEMENT, or NEW_QUERY",
    instruction=PLAN_RESPONSE_CLASSIFIER_INSTRUCTION,
    output_schema=PlanResponseClassification,
    output_key="plan_response",
)
