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

"""Follow-up query rejection handler with helpful message.

This agent provides a helpful rejection message when users try to extend
a previous analysis. It guides them to create a new comprehensive query
instead.
"""

from google.adk.agents import LlmAgent

from app.config import MODEL

FOLLOW_UP_REJECTION_INSTRUCTION = """
You are responding to a follow-up query that cannot be processed.

The user tried to extend a previous analysis, but this system currently only
supports fresh, comprehensive queries.

**Your Response:**
1. Acknowledge what they were trying to do
2. Explain that follow-up queries are not currently supported
3. Suggest creating a new comprehensive query that includes what they want

**Context from Classification:**
- Previous query summary: {{ last_query_summary }}
- Current query classification: {{ query_classification }}

**Example Response:**
"I understand you'd like to add more analysis to the previous report. Currently,
I can only process complete, fresh queries.

To include the additional metrics you want, please create a new query like:
'Comprehensive analysis of [Company] including [previous metrics] AND [new metrics you wanted]'

This will generate a complete report with all the metrics you need."

Be helpful and guide them to success. Mention specific examples based on
what you can infer from the context.
"""

follow_up_handler = LlmAgent(
    model=MODEL,  # Use MODEL from config
    name="follow_up_handler",
    description="Handles follow-up queries with helpful rejection message",
    instruction=FOLLOW_UP_REJECTION_INSTRUCTION,
)
