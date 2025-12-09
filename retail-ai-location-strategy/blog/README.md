# Building a Production Multi-Agent System with Google ADK

A progressive tutorial series where you build the **Retail AI Location Strategy Agent** step-by-step. Each part adds a new capability, and by the end of each part, you have a working agent you can run.

## The Agent You'll Build

An 8-agent pipeline that helps retailers find optimal locations for new stores:

```
User: "I want to open a coffee shop in Indiranagar, Bangalore"
                    ↓
        [8-Agent Pipeline]
                    ↓
Output: Strategic report, infographic, and podcast-style audio
```

The complete agent:
- Parses natural language requests
- Searches the web for market research
- Finds real competitors via Google Maps
- Calculates viability scores with Python
- Synthesizes strategic recommendations
- Generates HTML reports, infographics, and audio summaries

## The Progressive Journey

| Part | What You Add | What Works After |
|------|--------------|------------------|
| [1. Setup and First Agent](./01-setup-first-agent.md) | Root Agent | Basic chat at :8501 |
| [2. IntakeAgent](./02-intake-agent.md) | Request Parsing | Extracts location & business type |
| [3. Market Research](./03-market-research.md) | Google Search | Live web research |
| [4. Competitor Mapping](./04-competitor-mapping.md) | Maps API | Real competitor data |
| [5. Code Execution](./05-code-execution.md) | Python/pandas | Viability scores |
| [6. Strategy Synthesis](./06-strategy-synthesis.md) | Extended Reasoning | Strategic recommendations |
| [7. Artifact Generation](./07-artifact-generation.md) | ParallelAgent | **Complete agent!** |
| [8. Testing](./08-testing.md) | Tests & Evals | Quality validation |
| [9. Production](./09-production-deployment.md) | Cloud Deployment | Live production URL |
| [Bonus: AG-UI](./bonus-ag-ui-frontend.md) | Rich Frontend | Interactive dashboard |

## Prerequisites

Before starting, you should:
- Know Python basics
- Have familiarity with [Google ADK](https://google.github.io/adk-docs/) concepts (agents, tools, state)
- Have API keys ready (Google AI Studio or Vertex AI, Google Maps)

This tutorial assumes you know ADK fundamentals. For deeper ADK concepts, we'll link to the [official documentation](https://google.github.io/adk-docs/).

## Quick Start

If you want to see the complete agent first:

```bash
git clone https://github.com/lavinigam-gcp/build-with-adk.git
cd build-with-adk/retail-ai-location-strategy
echo "GOOGLE_GENAI_USE_VERTEXAI=FALSE" >> app/.env
echo "GOOGLE_API_KEY=your_key" >> app/.env
echo "MAPS_API_KEY=your_maps_key" >> app/.env
make install && make dev
```

Open `http://localhost:8501` and try: *"I want to open a coffee shop in Indiranagar, Bangalore"*

## What You'll Learn

By the end of this series, you'll understand how to:

1. **Structure multi-agent pipelines** with SequentialAgent and ParallelAgent
2. **Parse unstructured input** into structured data with Pydantic schemas
3. **Integrate external APIs** with custom tools (Google Maps, web search)
4. **Execute code dynamically** for quantitative analysis
5. **Use extended reasoning** for complex synthesis tasks
6. **Generate multimodal outputs** (HTML, images, audio)
7. **Test AI agents** with unit tests, integration tests, and evaluations
8. **Deploy to production** with Agent Starter Pack

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LocationStrategyPipeline (SequentialAgent)            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────┐│
│  │ Intake   │ → │ Market   │ → │Competitor│ → │   Gap    │ → │Strategy││
│  │ Agent    │   │ Research │   │ Mapping  │   │ Analysis │   │Advisor ││
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └────────┘│
│       │              │              │              │              │     │
│       ▼              ▼              ▼              ▼              ▼     │
│   [Parse]      [google_search] [search_places] [CodeExec]  [Thinking]  │
│                                                                          │
│                              ┌──────────────────────────────────────────┤
│                              │  ArtifactGenerationPipeline (Parallel)   │
│                              ├──────────────────────────────────────────┤
│                              │  ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│                              │  │ Report  │ │Infograph│ │  Audio  │    │
│                              │  │Generator│ │Generator│ │Overview │    │
│                              │  └─────────┘ └─────────┘ └─────────┘    │
│                              │       │           │           │          │
│                              │       ▼           ▼           ▼          │
│                              │   [HTML]     [Image]      [TTS]         │
└──────────────────────────────┴──────────────────────────────────────────┘
```

## Start Building

Ready to build? Start with [Part 1: Setup and Your First Agent](./01-setup-first-agent.md).

---

**Authors**: [Lavi Nigam](https://github.com/lavinigam-gcp) and [Deepak Moonat](https://github.com/dmoonat)

**Source Code**: [retail-ai-location-strategy](../)

**ADK Documentation**: [google.github.io/adk-docs](https://google.github.io/adk-docs/)
