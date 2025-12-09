# Part 7: Multimodal Artifact Generation

By the end of this part, you'll have the **complete agent** generating HTML reports, infographics, and podcast-style audio!

**Input**: Strategic report from StrategyAdvisorAgent
**Output**: Three artifacts generated in parallel:
- `executive_report.html` - 7-slide presentation
- `infographic.png` - Visual summary
- `audio_overview.wav` - Podcast audio (~2-3 minutes)

---

## Beyond Text: Actionable Outputs

Business users don't want to read JSON. They need:
- **HTML Reports**: Shareable, printable executive presentations
- **Infographics**: Quick visual summaries for stakeholders
- **Audio Summaries**: Podcast-style briefings for busy executives

The **ArtifactGenerationPipeline** produces all three simultaneously.

---

## ParallelAgent for Performance

Instead of generating artifacts one-by-one, we use `ParallelAgent`:

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

**Why ParallelAgent?**

| Benefit | Impact |
|---------|--------|
| ~40% faster | All three run simultaneously |
| Independent failures | One failing doesn't block others |
| Shared state | All read from `strategic_report` |

---

## HTML Report Generation

The `ReportGeneratorAgent` creates McKinsey/BCG style presentations:

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

**Key points:**
- Uses `async` for non-blocking execution in parallel
- `tool_context.save_artifact()` persists the HTML
- `mime_type="text/html"` tells the UI how to render it

---

## Infographic Generation

Uses Gemini's native image generation:

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
        model=IMAGE_MODEL,  # gemini-3-pro-image-preview
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

**Key configuration:**
- `model=IMAGE_MODEL` uses Gemini's image generation model
- `response_modalities=["TEXT", "IMAGE"]` enables image output
- Image data is binary, saved directly as artifact

---

## Audio Overview Generation

Creates podcast-style audio using Gemini TTS:

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

**TTS Configuration:**

| Mode | Voices | Script Format |
|------|--------|---------------|
| AI Studio | Kore + Puck (two hosts) | Dialogue with speaker labels |
| Vertex AI | Kore only | Single narrator |

---

## The Complete Pipeline

With artifact generation, you have the complete agent:

```
User Query
    │
    ▼
┌─────────────┐
│IntakeAgent  │ → target_location, business_type
└─────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│              LocationStrategyPipeline                        │
├─────────────────────────────────────────────────────────────┤
│  MarketResearchAgent → market_research_findings              │
│              │                                               │
│              ▼                                               │
│  CompetitorMappingAgent → competitor_analysis                │
│              │                                               │
│              ▼                                               │
│  GapAnalysisAgent → gap_analysis                             │
│              │                                               │
│              ▼                                               │
│  StrategyAdvisorAgent → strategic_report                     │
│              │                                               │
│              ▼                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │       ArtifactGenerationPipeline (ParallelAgent)        ││
│  ├─────────────────────────────────────────────────────────┤│
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ││
│  │  │   Report     │  │  Infographic │  │    Audio     │  ││
│  │  │  Generator   │  │   Generator  │  │   Overview   │  ││
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  ││
│  │         │                 │                 │           ││
│  │         ▼                 ▼                 ▼           ││
│  │  executive_     infographic.   audio_overview.          ││
│  │  report.html       png            wav                   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Try the Complete Agent!

Run the agent:

```bash
make dev
```

Try: "I want to open a coffee shop in Indiranagar, Bangalore"

Watch the full pipeline execute:
1. IntakeAgent parses your request
2. MarketResearchAgent searches the web
3. CompetitorMappingAgent finds real competitors
4. GapAnalysisAgent calculates viability scores
5. StrategyAdvisorAgent synthesizes recommendations
6. ArtifactGenerationPipeline creates all outputs in parallel

Check the **Artifacts tab** for:
- `intelligence_report.json` - Structured data
- `executive_report.html` - 7-slide presentation
- `infographic.png` - Visual summary
- `audio_overview.wav` - Podcast audio

---

## Callbacks for Artifact Pipeline

Each artifact generator has callbacks:

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

---

## What You've Built

Congratulations! You've built a complete multi-agent pipeline that:

1. **Parses** natural language requests
2. **Researches** markets with live web search
3. **Maps** competitors with Google Maps API
4. **Analyzes** viability with Python code execution
5. **Synthesizes** recommendations with extended reasoning
6. **Generates** multimodal artifacts in parallel

---

## Next Steps

Your agent is *feature-complete*. It takes natural language input and produces strategic reports, visual infographics, and audio briefings. But before you share it with stakeholders or deploy it to production, you need confidence that it actually works reliably.

LLM-based agents are notoriously hard to test—outputs vary between runs, external APIs return different data, and "correct" is often subjective. How do you validate something that doesn't give deterministic outputs?

In [Part 8: Testing](./08-testing.md), we'll establish a testing strategy that handles this uncertainty. You'll learn to write unit tests for schemas, integration tests for individual agents, and evaluations that measure quality over time.

After that:
- [Part 9: Production](./09-production-deployment.md) - Deploy to Cloud Run or Agent Engine
- [Bonus: AG-UI](./bonus-ag-ui-frontend.md) - Add a rich interactive dashboard

---

## Quick Reference

| Feature | How to Use |
|---------|------------|
| Parallel execution | `ParallelAgent(sub_agents=[...])` |
| Image generation | `response_modalities=["TEXT", "IMAGE"]` |
| TTS audio | `response_modalities=["AUDIO"]`, `speech_config` |
| Save artifact | `await tool_context.save_artifact(filename, part)` |
| Async tools | `async def my_tool(...) -> dict` |

---

**Code files referenced in this part:**
- [`app/sub_agents/artifact_generation/agent.py`](../app/sub_agents/artifact_generation/agent.py) - ParallelAgent
- [`app/sub_agents/report_generator/agent.py`](../app/sub_agents/report_generator/agent.py) - HTML report
- [`app/tools/html_report_generator.py`](../app/tools/html_report_generator.py) - HTML tool
- [`app/tools/image_generator.py`](../app/tools/image_generator.py) - Image tool
- [`app/tools/audio_generator.py`](../app/tools/audio_generator.py) - Audio tool

**ADK Documentation:**
- [ParallelAgent](https://google.github.io/adk-docs/agents/workflow-agents/#parallelagent)
- [Artifacts](https://google.github.io/adk-docs/agents/artifacts/)

---

<details>
<summary>Image Prompt for This Part</summary>

```json
{
  "image_type": "parallel_pipeline_diagram",
  "style": {
    "design": "clean, modern technical diagram",
    "color_scheme": "Google Cloud colors (blue #4285F4, red #EA4335, yellow #FBBC05, green #34A853) with white background",
    "layout": "horizontal with parallel fork",
    "aesthetic": "minimalist, vector-style"
  },
  "dimensions": {"aspect_ratio": "16:9", "recommended_width": 1200},
  "title": {"text": "Part 7: ArtifactGenerationPipeline - Complete Agent!", "position": "top center"},
  "sections": [
    {
      "id": "input",
      "position": "left",
      "color": "#E8F5E9",
      "components": [
        {"name": "strategic_report", "icon": "document", "status": "from Part 6"}
      ]
    },
    {
      "id": "parallel",
      "position": "center",
      "label": "ParallelAgent (concurrent)",
      "layout": "vertical stack of 3",
      "components": [
        {"name": "ReportGeneratorAgent", "icon": "HTML document", "tool": "generate_html_report", "color": "#E0F7FA"},
        {"name": "InfographicGeneratorAgent", "icon": "image", "tool": "generate_infographic", "color": "#FFF8E1"},
        {"name": "AudioOverviewAgent", "icon": "microphone", "tool": "generate_audio_overview", "color": "#F1F8E9"}
      ]
    },
    {
      "id": "outputs",
      "position": "right",
      "color": "#FBBC05",
      "components": [
        {"name": "executive_report.html", "icon": "HTML file", "description": "7-slide presentation"},
        {"name": "infographic.png", "icon": "image file", "description": "Visual summary"},
        {"name": "audio_overview.wav", "icon": "audio file", "description": "~2-3 min podcast"}
      ]
    }
  ],
  "connections": [
    {"from": "input", "to": "parallel", "label": "Fork (3 parallel)"},
    {"from": "parallel", "to": "outputs", "style": "triple arrows"}
  ],
  "annotation": {"text": "~40% faster than sequential", "position": "below parallel"}
}
```

</details>
