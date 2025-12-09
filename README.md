# Build with ADK

**Learn to build production-ready AI agents with Google's Agent Development Kit**

A curated collection of design patterns and real-world examples for building AI agents using [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/). From simple single-agent setups to complex multi-agent pipelines, this repository demonstrates how to combine ADK features and components to create powerful, deployable agents.

---

## Why This Repository?

Building AI agents that work in production requires more than just prompt engineering. You need:

- **Robust architectures** that handle complex, multi-step workflows
- **State management** that flows seamlessly between components
- **Tool integration** with external APIs and services
- **Error handling** with retries and graceful degradation
- **Structured outputs** that downstream systems can consume
- **Observability** through callbacks and logging
- **Frontend integration** for user-facing applications

This repository provides **battle-tested patterns** that solve these challenges, with complete working examples you can run, study, and adapt.

---

## What You'll Learn

| Pattern | Description | Complexity |
|---------|-------------|------------|
| **Sequential Pipelines** | Chain agents in order, passing state between stages | Intermediate |
| **Multi-Agent Orchestration** | Coordinate specialized agents for complex tasks | Advanced |
| **Custom Tool Development** | Build tools that integrate external APIs | Intermediate |
| **State Management** | Share data between agents via session state | Foundational |
| **Structured Output** | Use Pydantic schemas for type-safe responses | Intermediate |
| **Lifecycle Callbacks** | Hook into agent execution for logging and artifacts | Intermediate |
| **Code Execution** | Let agents write and run Python code | Advanced |
| **Image Generation** | Generate images with Gemini's native capabilities | Intermediate |
| **AG-UI Integration** | Build interactive frontends with real-time state sync | Advanced |

---

## Examples

### [Retail AI Location Strategy](./retail-ai-location-strategy/)

**Complexity:** Advanced | **Type:** Multi-Agent Sequential Pipeline

A comprehensive example that demonstrates how to build a production-ready multi-agent system. Given a location and business type, this pipeline automatically researches markets, maps competitors, calculates viability scores, and generates executive reports.

**Key ADK Features Demonstrated:**
- `SequentialAgent` for pipeline orchestration
- 7 specialized sub-agents with distinct responsibilities
- `google_search` built-in tool for web research
- Custom tools for Google Maps Places API integration
- `BuiltInCodeExecutor` for Python/pandas analysis
- `BuiltInPlanner` with extended thinking for strategy synthesis
- Pydantic `output_schema` for structured JSON output
- Lifecycle callbacks for logging and artifact management
- Native image generation with Gemini
- AG-UI Protocol frontend with CopilotKit

```bash
cd retail-ai-location-strategy
make install && make dev
# Open http://localhost:8501
```

---

## Getting Started

### Prerequisites

- **Python 3.10-3.12**
- **[uv](https://github.com/astral-sh/uv)** (recommended) or pip
- **[Google AI Studio API Key](https://aistudio.google.com/app/apikey)** or Google Cloud project with Vertex AI

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/lavinigam-gcp/build-with-adk.git
   cd build-with-adk
   ```

2. **Choose an example and follow its README**
   ```bash
   cd retail-ai-location-strategy
   cat README.md
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example app/.env
   # Edit app/.env with your API keys
   ```

4. **Install and run**
   ```bash
   make install && make dev
   ```

---

## Repository Structure

```
build-with-adk/
├── README.md                      # This file
├── retail-ai-location-strategy/   # Multi-agent pipeline example
│   ├── app/                       # Agent code
│   │   ├── agent.py               # Root SequentialAgent
│   │   ├── sub_agents/            # 7 specialized agents
│   │   ├── tools/                 # Custom tools
│   │   ├── callbacks/             # Lifecycle hooks
│   │   ├── schemas/               # Pydantic models
│   │   └── frontend/              # AG-UI dashboard
│   ├── notebook/                  # Reference Jupyter notebook
│   ├── README.md                  # Example-specific docs
│   └── DEVELOPER_GUIDE.md         # Deep-dive documentation
└── [future examples...]
```

---

## Resources

- **[ADK Documentation](https://google.github.io/adk-docs/)** - Official ADK docs
- **[ADK Samples](https://github.com/google/adk-samples)** - Google's official sample agents
- **[Agent Starter Pack](https://goo.gle/agent-starter-pack)** - Production deployment templates
- **[AG-UI Protocol](https://docs.ag-ui.com/)** - Agent-UI integration standard
- **[CopilotKit](https://docs.copilotkit.ai/)** - React components for AI agents

---

## Contributing

Contributions are welcome! If you have a design pattern or example that would help others learn ADK, please open an issue or pull request.

---

## Author

[Lavi Nigam](https://github.com/lavinigam-gcp)

### Collaborators

- [Deepak Moonat](https://github.com/dmoonat)

---

## License

Apache 2.0 - See individual example folders for specific licenses.
