# Part 7: Multimodal Artifact Generation

In the previous part, you built the StrategyAdvisorAgent that synthesizes all research into a comprehensive strategic report. But there's a problem: the report is JSON. Business stakeholders don't read JSON. They need polished deliverables they can share with investors, present to boards, or consume on the go.

This is where your agent transforms from a research tool into a complete solution. By the end of this part, you'll have an agent that produces three professional artifacts simultaneously: an HTML executive presentation, a visual infographic, and a podcast-style audio briefing. And thanks to ADK's `ParallelAgent`, all three generate concurrently—making the pipeline roughly 40% faster than sequential execution.

<p align="center">
  <img src="assets/part7_parallel_pipeline_diagram.jpeg" alt="Part 7: ArtifactGenerationPipeline - Parallel Artifact Generation" width="600">
</p>

---

## Beyond Text: Actionable Outputs

The strategic report contains everything a business owner needs to make a location decision: top recommendation with evidence-backed strengths and concerns, alternative locations, key insights, and next steps. But format matters as much as content.

Different stakeholders consume information differently:

- **Executives** want a polished HTML presentation they can review in minutes and share with their board
- **Marketing teams** need visual infographics they can use in pitch decks and social media
- **Busy founders** want audio summaries they can listen to during their commute

The `ArtifactGenerationPipeline` produces all three, transforming a single strategic report into multiple consumption formats.

---

## ParallelAgent: Concurrent Execution

When you have multiple independent tasks—like generating three different artifacts from the same input—running them sequentially wastes time. Each generation might take 10-30 seconds. Sequential execution: 30-90 seconds. Parallel execution: the time of the slowest one.

ADK's `ParallelAgent` runs sub-agents concurrently:

```python
# app/sub_agents/artifact_generation/agent.py
from google.adk.agents import ParallelAgent

from ..report_generator import report_generator_agent
from ..infographic_generator import infographic_generator_agent
from ..audio_overview import audio_overview_agent

artifact_generation_pipeline = ParallelAgent(
    name="ArtifactGenerationPipeline",
    description="""Generates all output artifacts in parallel:
    - 4A: HTML executive report (McKinsey/BCG style)
    - 4B: Visual infographic (Gemini image generation)
    - 4C: Audio podcast overview (Gemini multi-speaker TTS)

    All three agents run concurrently and share the same session state.
    """,
    sub_agents=[
        report_generator_agent,
        infographic_generator_agent,
        audio_overview_agent,
    ],
)
```

The benefits are significant:

| Benefit | Impact |
|---------|--------|
| ~40% faster | All three agents run simultaneously |
| Independent failures | One agent failing doesn't block others |
| Shared state | All agents read from the same `strategic_report` |

Each sub-agent reads from session state (specifically `strategic_report` from the previous stage) and writes its artifact independently. If image generation fails due to a quota limit, HTML and audio generation continue unaffected.

> **Learn more:** The [ParallelAgent documentation](https://google.github.io/adk-docs/agents/workflow-agents/#parallelagent) covers configuration and error handling.

---

## HTML Report Generation

The `ReportGeneratorAgent` creates McKinsey/BCG-style executive presentations—the kind of polished deliverable you'd expect from a strategy consulting firm.

### The Agent

```python
# app/sub_agents/report_generator/agent.py
from google.adk.agents import LlmAgent
from ...tools import generate_html_report

report_generator_agent = LlmAgent(
    name="ReportGeneratorAgent",
    model=FAST_MODEL,
    description="Generates professional McKinsey/BCG-style HTML executive reports",
    instruction=REPORT_GENERATOR_INSTRUCTION,
    tools=[generate_html_report],
    output_key="report_generation_result",
    before_agent_callback=before_report_generator,
    after_agent_callback=after_report_generator,
)
```

The agent's instruction tells it to call the `generate_html_report` tool with the strategic report data. The tool handles the actual generation and artifact saving.

### The Tool

```python
# app/tools/html_report_generator.py
async def generate_html_report(report_data: str, tool_context: ToolContext) -> dict:
    """Generate a McKinsey/BCG style HTML executive report and save as artifact."""
    from google import genai

    client = genai.Client()

    prompt = f"""Generate a comprehensive, professional HTML report...

    This report should be in the style of McKinsey/BCG consulting presentations:
    - Multi-slide format using full-screen scrollable sections
    - Modern, clean, executive-ready design

    STRUCTURE - Create 7 distinct slides:
    1. EXECUTIVE SUMMARY & TOP RECOMMENDATION
    2. TOP RECOMMENDATION DETAILS
    3. COMPETITION ANALYSIS
    4. MARKET CHARACTERISTICS
    5. ALTERNATIVE LOCATIONS
    6. KEY INSIGHTS & NEXT STEPS
    7. METHODOLOGY

    DATA TO INCLUDE:
    {report_data}
    """

    response = client.models.generate_content(
        model=PRO_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=1.0),
    )

    html_code = response.text
    # Strip markdown fences if present
    if html_code.startswith("```"):
        html_code = html_code[7:-3].strip()

    # Save as artifact
    html_artifact = types.Part.from_bytes(
        data=html_code.encode('utf-8'),
        mime_type="text/html"
    )
    version = await tool_context.save_artifact(
        filename="executive_report.html",
        artifact=html_artifact
    )

    return {
        "status": "success",
        "artifact_filename": "executive_report.html",
        "html_length": len(html_code),
    }
```

Several implementation details are worth noting. The function is `async` because `save_artifact()` is asynchronous—essential for non-blocking parallel execution. The `mime_type="text/html"` tells the ADK Web UI to render it as HTML rather than plain text. And we strip markdown code fences that Gemini sometimes wraps around generated code.

> **Learn more:** The [Artifacts documentation](https://google.github.io/adk-docs/agents/artifacts/) covers saving and retrieving different file types.

---

## Infographic Generation

Visual communication is powerful—a well-designed infographic conveys complex information at a glance. Gemini's native image generation creates professional business infographics directly from the strategic report.

```python
# app/tools/image_generator.py
async def generate_infographic(data_summary: str, tool_context: ToolContext) -> dict:
    """Generate infographic using Gemini's native image generation."""
    from google import genai

    client = genai.Client()

    prompt = f"""Create a professional business infographic...

    Design should be:
    - Clean, modern, corporate style
    - Data visualization focused
    - Professional color palette

    Data to visualize:
    {data_summary}
    """

    response = client.models.generate_content(
        model=IMAGE_MODEL,  # gemini-2.0-flash-exp or imagen model
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],  # Enable image output
        ),
    )

    # Extract image from response
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            image_data = part.inline_data.data
            mime_type = part.inline_data.mime_type

            # Save as artifact
            image_artifact = types.Part.from_bytes(
                data=image_data,
                mime_type=mime_type
            )
            await tool_context.save_artifact("infographic.png", image_artifact)

            return {"status": "success", "artifact_filename": "infographic.png"}

    return {"status": "error", "message": "No image generated"}
```

The key configuration is `response_modalities=["TEXT", "IMAGE"]`, which tells Gemini to generate an image as part of its response. The image comes back as binary data in `part.inline_data`, which we save directly as an artifact.

Image generation models are still evolving, and results can vary. The prompt design matters—asking for "professional business infographic" with "data visualization focused" and "corporate style" guides the model toward appropriate output.

---

## Audio Overview Generation

For busy executives who prefer to consume information while commuting or exercising, audio summaries are invaluable. Gemini's text-to-speech capabilities can create podcast-style audio briefings with multiple speakers.

```python
# app/tools/audio_generator.py
async def generate_audio_overview(podcast_script: str, tool_context: ToolContext) -> dict:
    """Generate audio using Gemini TTS.

    - AI Studio: Multi-speaker (Host A + Host B) dialogue
    - Vertex AI: Single-speaker narrative (fallback)
    """
    from google import genai

    client = genai.Client()

    # Multi-speaker config for AI Studio
    speech_config = types.SpeechConfig(
        multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
            speaker_voice_configs=[
                types.SpeakerVoiceConfig(
                    speaker="Host A",
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
                    )
                ),
                types.SpeakerVoiceConfig(
                    speaker="Host B",
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
                    )
                ),
            ]
        )
    )

    response = client.models.generate_content(
        model=TTS_MODEL,  # gemini-2.5-flash-preview-tts
        contents=podcast_script,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=speech_config,
        ),
    )

    # Extract audio data
    for part in response.candidates[0].content.parts:
        if part.inline_data and "audio" in part.inline_data.mime_type:
            audio_data = part.inline_data.data

            # Wrap in WAV headers for compatibility
            wav_data = wrap_in_wav_headers(audio_data)

            # Save as artifact
            audio_artifact = types.Part.from_bytes(
                data=wav_data,
                mime_type="audio/wav"
            )
            await tool_context.save_artifact("audio_overview.wav", audio_artifact)

            return {"status": "success", "artifact_filename": "audio_overview.wav"}
```

The multi-speaker configuration creates a natural dialogue between two hosts, making the audio more engaging than a monotone narration. The script format uses speaker labels like `Host A: "Welcome to our location intelligence briefing..."` that the TTS model interprets correctly.

One important caveat: multi-speaker TTS currently only works with AI Studio. If you're using Vertex AI, the tool falls back to single-speaker narration. Check the tool implementation for the fallback logic.

| Mode | Voices | Script Format |
|------|--------|---------------|
| AI Studio | Kore + Puck (two hosts) | Dialogue with speaker labels |
| Vertex AI | Kore only | Single narrator |

---

## Testing the Complete Agent

With artifact generation in place, you have the complete pipeline. Start the development server:

```bash
make dev
```

Open `http://localhost:8501` and enter:

> "I want to open a coffee shop in Indiranagar, Bangalore"

Watch the full pipeline execute:

1. **IntakeAgent** parses your request into structured data
2. **MarketResearchAgent** searches the web for demographics and trends
3. **CompetitorMappingAgent** finds real competitors via Google Maps
4. **GapAnalysisAgent** calculates viability scores with Python code
5. **StrategyAdvisorAgent** synthesizes everything into strategic recommendations
6. **ArtifactGenerationPipeline** creates all outputs in parallel

When complete, check the **Artifacts tab** for:

- `intelligence_report.json` — Structured strategic data
- `executive_report.html` — 7-slide presentation (open in browser for full effect)
- `infographic.png` — Visual summary
- `audio_overview.wav` — Podcast audio (~2-3 minutes)

---

## Callback Coordination

Since the artifact generators run in parallel, we need a way to know when all three are complete. Each generator has its own after callback, and a helper function checks if all three have finished:

```python
# app/callbacks/pipeline_callbacks.py
def after_report_generator(callback_context: CallbackContext):
    """Log completion of report generation."""
    logger.info("STAGE 4A: COMPLETE - HTML report generated")
    stages = callback_context.state.get("stages_completed", [])
    stages.append("report_generation")
    callback_context.state["stages_completed"] = stages
    _check_artifact_generation_complete(callback_context)
    return None


def _check_artifact_generation_complete(callback_context: CallbackContext):
    """Log summary when all artifact stages complete."""
    stages = callback_context.state.get("stages_completed", [])
    artifact_stages = {"report_generation", "infographic_generation", "audio_overview"}
    completed = artifact_stages.intersection(set(stages))

    if len(completed) == 3:
        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETE")
        logger.info(f"  Stages completed: {stages}")
        logger.info("  Artifacts: HTML report, infographic, audio overview")
        logger.info("=" * 60)
```

Each after callback appends its stage to `stages_completed`, then calls `_check_artifact_generation_complete()`. When all three artifact stages are in the list, we log the final pipeline completion summary. This pattern works because all three agents share the same session state.

---

## What You've Built

Congratulations! You've built a complete multi-agent pipeline that transforms a natural language request into professional business deliverables:

1. **Parses** natural language requests into structured data
2. **Researches** markets with live web search
3. **Maps** competitors with Google Maps Places API
4. **Analyzes** viability with sandboxed Python code execution
5. **Synthesizes** recommendations with extended reasoning
6. **Generates** multimodal artifacts in parallel

From "I want to open a coffee shop in Bangalore" to a strategic report, executive presentation, visual infographic, and audio briefing—all generated automatically.

---

## What You've Learned

In this part, you've seen how ADK enables multimodal artifact generation:

- **ParallelAgent** runs independent sub-agents concurrently for faster execution
- **Async tools** with `await tool_context.save_artifact()` enable non-blocking artifact saving
- **Image generation** uses `response_modalities=["TEXT", "IMAGE"]` for visual outputs
- **Multi-speaker TTS** creates engaging podcast-style audio with dialogue
- **Callback coordination** tracks parallel completion across shared state

This pattern—parallel artifact generation from structured data—applies to many use cases: report generation pipelines, content creation workflows, or any system that needs to produce multiple output formats.

---

## Quick Reference

| Feature | How to Use |
|---------|------------|
| Parallel execution | `ParallelAgent(sub_agents=[...])` |
| Image generation | `response_modalities=["TEXT", "IMAGE"]` |
| TTS audio | `response_modalities=["AUDIO"]`, `speech_config` |
| Save artifact | `await tool_context.save_artifact(filename, part)` |
| Async tools | `async def my_tool(...) -> dict` |

**Files referenced in this part:**

- [`app/sub_agents/artifact_generation/agent.py`](../app/sub_agents/artifact_generation/agent.py) — ParallelAgent definition
- [`app/sub_agents/report_generator/agent.py`](../app/sub_agents/report_generator/agent.py) — HTML report agent
- [`app/tools/html_report_generator.py`](../app/tools/html_report_generator.py) — HTML generation tool
- [`app/tools/image_generator.py`](../app/tools/image_generator.py) — Infographic generation tool
- [`app/tools/audio_generator.py`](../app/tools/audio_generator.py) — Audio generation tool
- [`app/callbacks/pipeline_callbacks.py`](../app/callbacks/pipeline_callbacks.py) — Coordination callbacks

**ADK Documentation:**

- [ParallelAgent](https://google.github.io/adk-docs/agents/workflow-agents/#parallelagent) — Concurrent agent execution
- [Artifacts](https://google.github.io/adk-docs/agents/artifacts/) — Saving and retrieving files
- [Custom Function Tools](https://google.github.io/adk-docs/tools/function-tools/) — Building async tools

---

## Next: Testing Your Agent

Your agent is feature-complete. It takes natural language input and produces strategic reports, visual infographics, and audio briefings. But before you share it with stakeholders or deploy it to production, you need confidence that it actually works reliably.

LLM-based agents are notoriously hard to test. Outputs vary between runs, external APIs return different data, and "correct" is often subjective. How do you validate something that doesn't give deterministic outputs?

In **[Part 8: Testing](./08-testing.md)**, you'll establish a testing strategy that handles this uncertainty. You'll learn to write unit tests for schemas and configurations, integration tests for individual agents, and evaluations that measure quality over time.

You'll learn:
- **Unit tests** for schemas, tools, and configurations (fast, no API calls)
- **Integration tests** for individual agents with real API calls
- **ADK evalsets** for measuring agent quality over time
- Testing strategies for non-deterministic LLM outputs

---

**[← Back to Part 6: Strategy Synthesis](./06-strategy-synthesis.md)** | **[Continue to Part 8: Testing →](./08-testing.md)**
