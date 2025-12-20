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

import datetime
import logging
import re
from collections.abc import AsyncGenerator
from typing import Literal

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from .config import config


# --- Structured Output Models ---
class SearchQuery(BaseModel):
    """Model representing a specific search query for web search."""

    search_query: str = Field(
        description="A highly specific and targeted query for web search."
    )


class Feedback(BaseModel):
    """Model for providing evaluation feedback on research quality."""

    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result. 'pass' if the research is sufficient, 'fail' if it needs revision."
    )
    comment: str = Field(
        description="Detailed explanation of the evaluation, highlighting strengths and/or weaknesses of the research."
    )
    follow_up_queries: list[SearchQuery] | None = Field(
        default=None,
        description="A list of specific, targeted follow-up search queries needed to fix research gaps. This should be null or empty if the grade is 'pass'.",
    )


# --- Callbacks ---
def collect_research_sources_callback(callback_context: CallbackContext) -> None:
    """Collects and organizes web-based research sources and their supported claims from agent events.

    This function processes the agent's `session.events` to extract web source details (URLs,
    titles, domains from `grounding_chunks`) and associated text segments with confidence scores
    (from `grounding_supports`). The aggregated source information and a mapping of URLs to short
    IDs are cumulatively stored in `callback_context.state`.

    Args:
        callback_context (CallbackContext): The context object providing access to the agent's
            session events and persistent state.
    """
    session = callback_context._invocation_context.session
    url_to_short_id = callback_context.state.get("url_to_short_id", {})
    sources = callback_context.state.get("sources", {})
    id_counter = len(url_to_short_id) + 1
    for event in session.events:
        if not (event.grounding_metadata and event.grounding_metadata.grounding_chunks):
            continue
        chunks_info = {}
        for idx, chunk in enumerate(event.grounding_metadata.grounding_chunks):
            if not chunk.web:
                continue
            url = chunk.web.uri
            title = (
                chunk.web.title
                if chunk.web.title != chunk.web.domain
                else chunk.web.domain
            )
            if url not in url_to_short_id:
                short_id = f"src-{id_counter}"
                url_to_short_id[url] = short_id
                sources[short_id] = {
                    "short_id": short_id,
                    "title": title,
                    "url": url,
                    "domain": chunk.web.domain,
                    "supported_claims": [],
                }
                id_counter += 1
            chunks_info[idx] = url_to_short_id[url]
        if event.grounding_metadata.grounding_supports:
            for support in event.grounding_metadata.grounding_supports:
                confidence_scores = support.confidence_scores or []
                chunk_indices = support.grounding_chunk_indices or []
                for i, chunk_idx in enumerate(chunk_indices):
                    if chunk_idx in chunks_info:
                        short_id = chunks_info[chunk_idx]
                        confidence = (
                            confidence_scores[i] if i < len(confidence_scores) else 0.5
                        )
                        text_segment = support.segment.text if support.segment else ""
                        sources[short_id]["supported_claims"].append(
                            {
                                "text_segment": text_segment,
                                "confidence": confidence,
                            }
                        )
    callback_context.state["url_to_short_id"] = url_to_short_id
    callback_context.state["sources"] = sources


def citation_replacement_callback(
    callback_context: CallbackContext,
) -> genai_types.Content:
    """Replaces citation tags in a report with Markdown-formatted links.

    Processes 'final_cited_report' from context state, converting tags like
    `<cite source="src-N"/>` into hyperlinks using source information from
    `callback_context.state["sources"]`. Also fixes spacing around punctuation.

    Args:
        callback_context (CallbackContext): Contains the report and source information.

    Returns:
        genai_types.Content: The processed report with Markdown citation links.
    """
    final_report = callback_context.state.get("final_cited_report", "")
    sources = callback_context.state.get("sources", {})

    def tag_replacer(match: re.Match) -> str:
        short_id = match.group(1)
        if not (source_info := sources.get(short_id)):
            logging.warning(f"Invalid citation tag found and removed: {match.group(0)}")
            return ""
        display_text = source_info.get("title", source_info.get("domain", short_id))
        return f" [{display_text}]({source_info['url']})"

    processed_report = re.sub(
        r'<cite\s+source\s*=\s*["\']?\s*(src-\d+)\s*["\']?\s*/>',
        tag_replacer,
        final_report,
    )
    processed_report = re.sub(r"\s+([.,;:])", r"\1", processed_report)
    callback_context.state["final_report_with_citations"] = processed_report
    return genai_types.Content(parts=[genai_types.Part(text=processed_report)])


# --- Custom Agent for Loop Control ---
class EscalationChecker(BaseAgent):
    """Checks research evaluation and escalates to stop the loop if grade is 'pass'."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        evaluation_result = ctx.session.state.get("research_evaluation")
        if evaluation_result and evaluation_result.get("grade") == "pass":
            logging.info(
                f"[{self.name}] Research evaluation passed. Escalating to stop loop."
            )
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            logging.info(
                f"[{self.name}] Research evaluation failed or not found. Loop will continue."
            )
            # Yielding an event without content or actions just lets the flow continue.
            yield Event(author=self.name)


# --- AGENT DEFINITIONS ---


# plan_generator = LlmAgent(
#     model=config.worker_model,
#     name="plan_generator",
#     description="Strategically deconstructs a user query into a comprehensive, multi-phase research plan. It also refines the plan based on user feedback and uses search only for initial topic clarification.",
#     instruction=f"""
#     **PLAN CONFIGURATION**
#     - INITIAL_RESEARCH_GOALS: 6

#     You are a senior research strategist. Your purpose is to deconstruct complex user requests into comprehensive, actionable research plans. You do not provide answers directly; you create the roadmap for finding them. If there is already a RESEARCH PLAN in the session state, improve upon it based on the user feedback.

#     RESEARCH PLAN(SO FAR):
#     {{ research_plan? }}

#     **Core Principle: The Strategy Funnel**
#     For any complex query, especially those involving strategy or business planning, your plan **MUST** be structured around the following four phases in this specific order. Each phase builds upon the previous one.

#     1.  **Phase I: Situational & Market Analysis:** Establish the context. Research the target environment, audience demographics, competitive landscape, and relevant trends or regulations. The goal is to answer "What is the current state of play?"
#     2.  **Phase II: Core Concept & Strategy Development:** Formulate the central strategy. Based *only* on the analysis from Phase I, define the unique selling proposition (USP), primary theme, and core concept. The goal is to answer "Given the context, what is our unique approach?"
#     3.  **Phase III: Operational & Tactical Implementation:** Detail the execution plan. Based on the concept from Phase II, outline the practical steps for key pillars like menu design, sourcing, staffing, and marketing. The goal is to answer "How will we make this happen?"
#     4.  **Phase IV: Synthesis & Deliverable Generation:** Create the final outputs. Synthesize all preceding research into the final artifacts requested by the user (e.g., reports, FAQs).

#     **CRITICAL RULE: Your generated plan MUST reflect this logical dependency.** Tasks from Phase I must appear before Phase II, and so on. For every component mentioned in a `[DELIVERABLE]` task (e.g., 'marketing approach'), there must be a corresponding `[RESEARCH]` task to gather that information.

#     **Example of a Well-Structured Plan:**
#     *   `[RESEARCH]` Analyze market... (Phase I)
#     *   `[RESEARCH]` Investigate competitors... (Phase I)
#     *   `[RESEARCH]` Define core concept based on market analysis... (Phase II)
#     *   `[RESEARCH]` Detail staffing plan for the defined concept... (Phase III)
#     *   `[RESEARCH]` Develop marketing strategy for the defined concept... (Phase III)
#     *   `[DELIVERABLE]` Synthesize all findings into a strategy document... (Phase IV)

#     **GENERAL INSTRUCTION: CLASSIFY TASK TYPES**
#     - **`[RESEARCH]`**: For goals in Phases I, II, and III that involve information gathering and analysis.
#     - **`[DELIVERABLE]`**: For goals in Phase IV that involve synthesizing information into final outputs.

#     **INITIAL RULE: Your initial output MUST start with a bulleted list of the configured number of action-oriented goals (`INITIAL_RESEARCH_GOALS`) that reflect the initial phases of the Strategy Funnel, followed by any *inherently implied* deliverables.**
#     - Your initial `INITIAL_RESEARCH_GOALS` must be logically ordered to represent the progression through Phases I, II, and III of the Strategy Funnel.
#     - **Proactive Implied Deliverables (Initial):** If the user's query explicitly asks for a final document (like a strategy plan or an FAQ), you MUST add these as distinct goals at the end of the plan. Phrase these as *synthesis actions* and prefix them with `[DELIVERABLE][IMPLIED]`.

#     **REFINEMENT RULE**:
#     - **Integrate Feedback & Mark Changes:** When incorporating user feedback, make targeted modifications to existing bullet points by adding `[MODIFIED]` (e.g., `[RESEARCH][MODIFIED]`). New goals should be prefixed with `[RESEARCH][NEW]` or `[DELIVERABLE][NEW]`.
#     - **Proactive Implied Deliverables (Refinement):** If feedback or existing goals imply a new synthesis step, add it as a `[DELIVERABLE][IMPLIED]` task.
#     - **Maintain Order:** Strictly maintain the logical, phased order of the plan. New bullets should be inserted into the appropriate phase or appended to the list.
#     - **Flexible Length:** The refined plan is no longer constrained by the initial limit of `INITIAL_RESEARCH_GOALS`.

#     **TOOL USE IS STRICTLY LIMITED:**
#     Your goal is to create a high-quality plan *without searching*. Only use `google_search` if a topic is ambiguous. You are forbidden from researching the *content* of the topic; that is the next agent's job.
#     Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
#     """,
#     tools=[google_search],
# )

# plan_generator = LlmAgent(
#     model=config.worker_model,
#     name="plan_generator",
#     description="Strategically deconstructs a user query into a comprehensive, multi-phase research plan. It also refines the plan based on user feedback and uses search only for initial topic clarification.",
#     instruction=f"""
#     **PLAN CONFIGURATION**
#     - INITIAL_RESEARCH_GOALS: 6

#     You are a senior research strategist. Your purpose is to deconstruct complex user requests into comprehensive, actionable research plans. You do not provide answers directly; you create the roadmap for finding them. If there is already a RESEARCH PLAN in the session state, improve upon it based on the user feedback.

#     RESEARCH PLAN(SO FAR):
#     {{ research_plan? }}

#     **Core Principle: The Strategy Funnel**
#     For any complex query, especially those involving strategy or business planning, your plan **MUST** be structured around the following five phases in this specific order. Each phase builds upon the previous one.

#     1.  **Phase I: Situational & Market Analysis:** Establish the context. Research the target environment, audience, competition, and trends.
#     2.  **Phase II: Core Concept & Strategy Development:** Formulate the central strategy. Based on Phase I, define the unique selling proposition (USP), theme, and core concept.
#     3.  **Phase III: Operational & Tactical Implementation:** Detail the execution plan. Based on the concept from Phase II, outline the practical steps for key pillars like staffing, marketing, logistics, etc.
#     4.  **Phase IV: Synthesis & Deliverable Generation:** Create the textual outputs. Synthesize all research into the final text-based artifacts requested by the user (e.g., reports, FAQs).
#     5.  **Phase V: Creative Asset Generation:** Proactively suggest AI-generatable media assets. Based on the fully formed strategy from the previous phases, identify and list potential visual or audio assets that would support the project's goals.

#     **CRITICAL RULE: Your generated plan MUST reflect this logical dependency.** Tasks from Phase I must appear before Phase II, and so on. Media tasks must always come last.

#     **Example of a Well-Structured Plan:**
#     *   `[RESEARCH]` Analyze market... (Phase I)
#     *   `[RESEARCH]` Define core concept... (Phase II)
#     *   `[RESEARCH]` Develop marketing strategy... (Phase III)
#     *   `[DELIVERABLE]` Synthesize all findings into a strategy document... (Phase IV)
#     *   `[MEDIA]` Generate a brand logo and color palette based on the core concept. (Phase V)
#     *   `[MEDIA]` Create a concept image for social media marketing banners. (Phase V)

#     **GENERAL INSTRUCTION: CLASSIFY TASK TYPES**
#     - **`[RESEARCH]`**: For goals in Phases I, II, and III that involve information gathering and analysis.
#     - **`[DELIVERABLE]`**: For goals in Phase IV that involve synthesizing information into text-based final outputs.
#     - **`[MEDIA]`**: For goals in Phase V that involve the generation of creative assets (images, video concepts, audio scripts). These are suggestions for downstream generation tools and are NOT part of the research pipeline.

#     **INITIAL RULE: Your initial plan must include research goals from Phases I-III, any implied deliverables for Phase IV, and proactive suggestions for Phase V.**
#     - Your initial `INITIAL_RESEARCH_GOALS` must be logically ordered to represent the progression through Phases I, II, and III.
#     - **Proactive Deliverables (Phase IV):** If the user explicitly asks for a final document (like a strategy plan), add this as a `[DELIVERABLE][IMPLIED]` task.
#     - **Proactive Media Suggestions (Phase V):** After all other tasks, analyze the overall project goal and proactively add 2-3 relevant `[MEDIA][IMPLIED]` tasks. Infer the need for these based on the context:
#         - If the project involves creating a **new brand or company** -> suggest a logo and brand identity assets.
#         - If the project involves a **product or service** -> suggest concept art or mockups.
#         - If the project includes **marketing** -> suggest promotional video concepts or social media visuals.

#     **REFINEMENT RULE**:
#     - **Integrate Feedback & Mark Changes:** When incorporating feedback, modify existing bullet points with `[MODIFIED]`. New goals should be prefixed with `[RESEARCH][NEW]`, `[DELIVERABLE][NEW]`, or `[MEDIA][NEW]`.
#     - **Maintain Order:** Strictly maintain the five-phase logical order of the plan.

#     **TOOL USE IS STRICTLY LIMITED:**
#     Your goal is to create a high-quality plan *without searching*. Only use `google_search` if a topic is ambiguous. You are forbidden from researching the *content* of the topic.
#     Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
#     """,
#     # tools=[google_search],
# )

plan_generator = LlmAgent(
    model=config.worker_model,
    name="plan_generator",
    description="Strategically deconstructs a user query into a comprehensive, multi-phase research plan. It also refines the plan based on user feedback and uses search only for initial topic clarification.",
    instruction=f"""
    **PLAN CONFIGURATION**
    - INITIAL_RESEARCH_GOALS: 6

    You are a senior research strategist. Your purpose is to deconstruct complex user requests into a comprehensive, actionable research plan formatted as a strict JSON object. If there is already a RESEARCH PLAN in the session state, improve upon it and output the complete, updated JSON.

    RESEARCH PLAN(SO FAR):
    {{ research_plan? }}

    **Core Principle: The Strategy Funnel**
    You must structure your plan around the following five phases in this specific order. These phases will serve as the main keys in your final JSON output.

    1.  **Phase I: Situational & Market Analysis:** Establish the context.
    2.  **Phase II: Core Concept & Strategy Development:** Formulate the central strategy.
    3.  **Phase III: Operational & Tactical Implementation:** Detail the execution plan.
    4.  **Phase IV: Synthesis & Deliverable Generation:** Define the textual outputs.
    5.  **Phase V: Creative Asset Prompt Generation:** Proactively define tasks to generate detailed prompts for AI media creation. This phase is populated by first classifying the user's intent and then deploying a relevant playbook of creative tasks.

    ---
    **Phase V - Creative Asset Prompt Generation Logic**
    To populate Phase V, you MUST follow this two-step classification process:

    **Step 1: Primary Intent Classification**
    First, classify the user's query into ONE of the following archetypes and select its playbook:
    -   **Venture Creation:** The query is about creating a new business, product, service, or event.
        -   **Action:** Deploy the "Base Venture Starter Pack" and then proceed to Step 2.
    -   **Informational Synthesis:** The query is about researching and explaining a topic.
        -   **Action:** Deploy the "Explanatory Visuals Playbook."
    -   **Creative Exploration:** The query is about generating artistic or fictional concepts.
        -   **Action:** Deploy the "Concept Art Playbook."

    **Step 2: Sub-Type Specialization (for "Venture Creation" ONLY)**
    If the primary intent is Venture Creation, you MUST also check for a specific sub-type and deploy its "Specialist Add-on Pack" in addition to the base pack.
    -   **Sub-Type: Food & Hospitality** (restaurant, cafe, food truck): Deploy the "Food & Hospitality Pack."
    -   **Sub-Type: Digital Product/Service** (app, website, SaaS): Deploy the "Digital Product Pack."
    -   **Sub-Type: Physical Product** (retail item, e-commerce): Deploy the "Physical Product Pack."

    **The Playbooks:**
    *   **Base Venture Starter Pack:**
        -   `<prompt_section>Brand Logo Concepts</prompt_section>`
        -   `<prompt_section>Visual Style and Color Palette</prompt_section>`
        -   `<prompt_section>Short Brand Introduction Video (Script & Storyboard)</prompt_section>`
    *   **Specialist Add-on: Food & Hospitality Pack:**
        -   `<prompt_section>Visual Menu Mockup</prompt_section>`
        -   `<prompt_section>Signature Dish Photography Style in a Brochure</prompt_section>`
        -   `<prompt_section>Promotional Brochure or Flyer</prompt_section>`
        -   `<prompt_section>Brand Logo</prompt_section>`
        -   `<prompt_section>Launch Announcement Social Media Post</prompt_section>`
        -   `<prompt_section>Social Media Content Templates with brand logo and colors</prompt_section>`
        -   `<prompt_section>Short Promotional Video Ad (Reels/TikTok)</prompt_section>`
        -   `<prompt_section>Brand color themes and palettes</prompt_section>`
    *   **Specialist Add-on: Digital Product Pack:**
        -   `<prompt_section>UI/UX Mockup Concepts</prompt_section>`
        -   `<prompt_section>App Icon Designs</prompt_section>`
    *   **Specialist Add-on: Physical Product Pack:**
        -   `<prompt_section>Product Packaging Concepts</prompt_section>`
        -   `<prompt_section>Promotional Lifestyle Images</prompt_section>`
    *   **Explanatory Visuals Playbook:**
        -   `<prompt_section>Infographic to Summarize Key Findings</prompt_section>`
        -   `<prompt_section>Data Visualization for Key Statistics</prompt_section>`
    *   **Concept Art Playbook:**
        -   `<prompt_section>Character Design Concepts</prompt_section>`
        -   `<prompt_section>Environment and Mood Board Concepts</prompt_section>`

    ---
    **Output Format: STRICT JSON STRUCTURE**
    Your entire output MUST be a single, raw JSON object. The description for each Phase V task MUST start with the `<prompt_section>` title from the playbook, followed by a description of the goal.

    ```json
    {{
      "phase_1_analysis": {{ "title": "Phase I: Situational & Market Analysis", "tasks": [] }},
      "phase_2_strategy": {{ "title": "Phase II: Core Concept & Strategy Development", "tasks": [] }},
      "phase_3_implementation": {{ "title": "Phase III: Operational & Tactical Implementation", "tasks": [] }},
      "phase_4_deliverables": {{ "title": "Phase IV: Synthesis & Deliverable Generation", "tasks": [] }},
      "phase_5_media_assets": {{
        "title": "Phase V: Creative Asset Prompt Generation",
        "tasks": [
          {{
            "type": "MEDIA",
            "status": "IMPLIED",
            "description": "<prompt_section>Brand Logo Concepts</prompt_section> Generate a series of detailed prompts for creating a brand logo, based on the research from Phase I and the core concepts from Phase II."
          }}
        ]
      }}
    }}
    ```

    **Key Definitions for the JSON Schema:**
    -   `"type"`: Must be one of `"RESEARCH"`, `"DELIVERABLE"`, or `"MEDIA"`.
    -   `"status"`: Must be one of `"BASE"`, `"IMPLIED"`, `"NEW"`, or `"MODIFIED"`.
    -   `"description"`: The detailed text of the task. For `MEDIA` tasks, this MUST begin with the `<prompt_section>` tag.

    ---
    **Execution Rules:**
    1.  **Populate the Structure:** Your primary goal is to populate the `tasks` array for each of the five phases.
    2.  **Initial Plan:** Populate Phases I-III with `INITIAL_RESEARCH_GOALS`. Populate Phase IV with any implied deliverables. For Phase V, execute the classification logic above and deploy the appropriate playbook(s).
    3.  **Refinement:** When refining a plan, regenerate the entire JSON object, updating fields as needed based on user feedback.

    **TOOL USE IS STRICTLY LIMITED:**
    Your goal is to create this plan without searching. Use `google_search` only if a topic is ambiguous.
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    """,
    # tools=[google_search],
)


section_planner = LlmAgent(
    model=config.worker_model,
    name="section_planner",
    description="Converts the high-level research_plan into a detailed, parallel markdown report structure, ensuring every research goal and deliverable has a dedicated section.",
    instruction="""
    You are a meticulous report architect. Your single, critical task is to convert the approved `research_plan` into a detailed and parallel report outline. The structure of your outline MUST PERFECTLY MIRROR the structure of the research plan.

    **Core Directives:**

    1.  **One-to-One Mapping:** For **every single bullet point** in the `research_plan`, you MUST create a corresponding and distinct markdown section in your output. The number of sections in your outline must exactly match the number of bullet points in the `research_plan`.
    2.  **No Merging or Omitting:** You are explicitly forbidden from merging, combining, or omitting any points from the research plan.
    3.  **Create Meaningful Titles:** For each plan item, create a clear and descriptive section title that captures the essence of that item's goal. Do not simply copy the text verbatim.
        -   *Generic Example:* If the plan item is `[RESEARCH] Investigate the key market drivers for renewable energy adoption.`, a good section title would be `# 1. Analysis of Key Market Drivers for Renewable Energy`.
    4.  **Frame Deliverables Appropriately:** If a plan item is marked `[DELIVERABLE]`, frame its section as a concluding, summary, or appendix chapter, depending on its nature.
        -   *Example for a Main Deliverable:* A plan item like `[DELIVERABLE] Synthesize all research into a comprehensive strategic analysis...` should become a major concluding section, such as `# 7. Comprehensive Strategic Analysis and Final Recommendations`.
        -   *Example for an Auxiliary Deliverable:* A plan item like `[DELIVERABLE] Generate an FAQ document for end-users...` should become a final appendix section, like `# 8. Appendix: End-User FAQ`.
    5.  **Provide Section Descriptions:** Underneath each section title, write a brief, 1-2 sentence overview of what content that section will cover, based directly on the details in the corresponding plan item.

    **Formatting Rules:**
    -   Ignore the status tags (`[MODIFIED]`, `[NEW]`, `[IMPLIED]`) when creating your output.
    -   Do not include a "References" or "Sources" section; citations will be handled later.
    -   Use numbered markdown headers (`# 1. Title`, `# 2. Title`, etc.) for clarity.
    """,
    output_key="report_sections",
)

section_researcher = LlmAgent(
    model=config.worker_model,
    name="section_researcher",
    description="Executes only the [RESEARCH] tasks from the plan to gather a comprehensive body of information, ignoring all [DELIVERABLE] tasks.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialist research agent. Your sole purpose is to execute the information-gathering phase of the provided `research_plan` with depth and precision. You are a knowledge gatherer, not a final report writer.

    **Your Workflow is Strict and Linear:**

    1.  **Focus Exclusively on `[RESEARCH]` Tasks:** You MUST process every goal prefixed with `[RESEARCH]`. You are to completely IGNORE any and all goals prefixed with `[DELIVERABLE]`. Those tasks are for a different agent.
    2.  **Execute a Comprehensive Search:** For each `[RESEARCH]` goal, formulate and execute a set of 5-8 targeted search queries using the `google_search` tool. Your queries should be designed to cover the topic from multiple angles to ensure thoroughness.
    3.  **Synthesize and Structure Findings:** After researching a goal, synthesize the collected information into a detailed, self-contained summary. Your final output MUST be a single, cohesive body of text, structured with clear markdown headers that correspond DIRECTLY to the `[RESEARCH]` goals from the plan. This creates a structured knowledge base for the next agent.

    **Example of Your Task:**

    If the `research_plan` is:
    *   `[RESEARCH]` Analyze the history of solar panel efficiency.
    *   `[RESEARCH]` Investigate the economic impact of geothermal energy.
    *   `[DELIVERABLE]` Create a comparison table of the two technologies.

    Your output (`section_research_findings`) MUST be structured like this:

    # History of Solar Panel Efficiency
    (Detailed, comprehensive text with your synthesized findings from multiple searches goes here...)

    # Economic Impact of Geothermal Energy
    (Detailed, comprehensive text with your synthesized findings from multiple searches goes here...)

    **CRITICAL:** Do NOT produce the comparison table or any other artifact mentioned in the `[DELIVERABLE]` task. Your job is only to provide the foundational research. The final output, `section_research_findings`, will be this structured compilation of your research, serving as the complete raw knowledge base for the composition agent that follows you.
    """,
    tools=[google_search],
    output_key="section_research_findings",
    after_agent_callback=collect_research_sources_callback,
)

research_evaluator = LlmAgent(
    model=config.critic_model,
    name="research_evaluator",
    description="Critically evaluates research and generates follow-up queries.",
    instruction=f"""
    You are a meticulous quality assurance analyst evaluating the research findings in 'section_research_findings'.

    **CRITICAL RULES:**
    1. Assume the given research topic is correct. Do not question or try to verify the subject itself.
    2. Your ONLY job is to assess the quality, depth, and completeness of the research provided *for that topic*.
    3. Focus on evaluating: Comprehensiveness of coverage, logical flow and organization, use of credible sources, depth of analysis, and clarity of explanations.
    4. Do NOT fact-check or question the fundamental premise or timeline of the topic.
    5. If suggesting follow-up queries, they should dive deeper into the existing topic, not question its validity.

    Be very critical about the QUALITY of research. If you find significant gaps in depth or coverage, assign a grade of "fail",
    write a detailed comment about what's missing, and generate 5-7 specific follow-up queries to fill those gaps.
    If the research thoroughly covers the topic, grade "pass".

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Your response must be a single, raw JSON object validating against the 'Feedback' schema.
    """,
    output_schema=Feedback,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    output_key="research_evaluation",
)

enhanced_search_executor = LlmAgent(
    model=config.worker_model,
    name="enhanced_search_executor",
    description="Executes follow-up searches and integrates new findings.",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
    You are a specialist researcher executing a refinement pass.
    You have been activated because the previous research was graded as 'fail'.

    1.  Review the 'research_evaluation' state key to understand the feedback and required fixes.
    2.  Execute EVERY query listed in 'follow_up_queries' using the 'google_search' tool.
    3.  Synthesize the new findings and COMBINE them with the existing information in 'section_research_findings'.
    4.  Your output MUST be the new, complete, and improved set of research findings.
    """,
    tools=[google_search],
    output_key="section_research_findings",
    after_agent_callback=collect_research_sources_callback,
)


report_composer = LlmAgent(
    model=config.critic_model,
    name="report_composer_with_citations",
    include_contents="none",
    description="Synthesizes raw research findings into a comprehensive, polished report, executing all [DELIVERABLE] tasks from the original plan.",
    instruction="""
    You are an expert research analyst and report writer. Your role is to transform a structured knowledge base and a set of instructions into a final, comprehensive, and polished report. You will not just report on findings; you will also execute synthesis tasks to create final artifacts like summaries, tables, or FAQs.

    ---
    ### INPUT DATA
    *   **The Original Instructions (`research_plan`):** `{research_plan}` - This contains the high-level goals, including the specific commands for `[DELIVERABLE]` tasks.
    *   **The Report Blueprint (`report_sections`):** `{report_sections}` - This provides the exact, non-negotiable structure of the final report.
    *   **The Knowledge Base (`section_research_findings`):** `{section_research_findings}` - This contains the complete, raw, and detailed information gathered during the research phase.
    *   **The Citation Data (`sources`):** `{sources}` - This contains the mapping of source IDs to URLs for citation.

    ---
    ### Your Core Workflow
    You MUST follow this two-part process, iterating through the blueprint provided in `report_sections` section by section.

    **Part 1: Writing the Research Sections**
    For each section in your blueprint that corresponds to a `[RESEARCH]` task in the original plan:
    1.  Locate the relevant body of text in the `section_research_findings` knowledge base.
    2.  Transform this raw information into a well-written, narrative chapter. Do not just copy and paste. Elaborate, ensure smooth transitions, and maintain a professional tone.
    3.  Integrate citations seamlessly as you write.

    **Part 2: Executing the Deliverable Sections**
    When you encounter a section in your blueprint that corresponds to a `[DELIVERABLE]` task from the original plan, you must treat that plan item as a direct command.
    1.  Read the instruction from the original `research_plan` item (e.g., "Synthesize all research into a comprehensive strategy document," "Generate a customer-facing FAQ," "Create a comparison table").
    2.  Synthesize the necessary information from the **previously written research chapters** of your report to fulfill this command.
    3.  Generate the required artifact precisely as requested. If the command is to create a comparison table, you MUST generate a markdown table. If it is to generate an FAQ, you MUST format the output as a series of questions and answers.

    ---
    ### CRITICAL: Citation System
    To cite a source, you MUST insert a special citation tag directly after the claim it supports.
    **The only correct format is:** `<cite source="src-ID_NUMBER" />`

    ---
    ### Final Mandate
    Your final output must be a single, complete report that is comprehensive, meticulously cited, and strictly follows the structure defined in `report_sections`. Every single objective from the original `research_plan`, both research and deliverable, must be visibly and thoroughly fulfilled in your output.
    """,
    output_key="final_cited_report",
    after_agent_callback=citation_replacement_callback,
)

research_pipeline = SequentialAgent(
    name="research_pipeline",
    description="Executes a pre-approved research plan. It performs iterative research, evaluation, and composes a final, cited report.",
    sub_agents=[
        section_planner,
        section_researcher,
        LoopAgent(
            name="iterative_refinement_loop",
            max_iterations=config.max_search_iterations,
            sub_agents=[
                research_evaluator,
                EscalationChecker(name="escalation_checker"),
                enhanced_search_executor,
            ],
        ),
        report_composer,
    ],
)

interactive_planner_agent = LlmAgent(
    name="interactive_planner_agent",
    model=config.worker_model,
    description="The primary research assistant. It collaborates with the user to create a research plan, and then executes it upon approval.",
    instruction=f"""
    You are a research planning assistant. Your primary function is to convert ANY user request into a research plan.

    **CRITICAL RULE: Never answer a question directly or refuse a request.** Your one and only first step is to use the `plan_generator` tool to propose a research plan for the user's topic.
    If the user asks a question, you MUST immediately call `plan_generator` to create a plan to answer the question.

    Your workflow is:
    1.  **Plan:** Use `plan_generator` to create a draft plan and present it to the user.
    2.  **Refine:** Incorporate user feedback until the plan is approved.
    3.  **Execute:** Once the user gives EXPLICIT approval (e.g., "looks good, run it"), you MUST delegate the task to the `research_pipeline` agent, passing the approved plan.

    Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
    Do not perform any research yourself. Your job is to Plan, Refine, and Delegate.
    """,
    sub_agents=[research_pipeline],
    tools=[AgentTool(plan_generator)],
    output_key="research_plan",
)

root_agent = interactive_planner_agent
