# Retail AI Location Strategy - ADK Implementation Tracker

## Project Overview
Port the Gemini API-based Retail AI Location Strategy pipeline to Google ADK.

## Quick Reference

### Architecture
```
SequentialAgent: LocationStrategyPipeline
├── MarketResearchAgent      (google_search tool)
├── CompetitorMappingAgent   (search_places FunctionTool)
├── GapAnalysisAgent         (BuiltInCodeExecutor)
├── StrategyAdvisorAgent     (BuiltInPlanner + output_schema)
├── ReportGeneratorAgent     (HTML generation)
└── InfographicGeneratorAgent (Gemini image API)
```

### State Flow
```
target_location, business_type, current_date, maps_api_key
    → market_research_findings
    → competitor_analysis
    → gap_analysis
    → strategic_report (Pydantic)
    → html_report
    → infographic_result
```

### Artifacts Generated
- `intelligence_report.json`
- `executive_report.html`
- `infographic.png`

---

## Implementation Status

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| Project Structure | directories | ✅ Done | |
| __init__.py files | all | ✅ Done | |
| config.py | config.py | ✅ Done | FAST_MODEL, PRO_MODEL |
| requirements.txt | requirements.txt | ✅ Done | |
| Pydantic Schemas | schemas/report_schema.py | ✅ Done | LocationIntelligenceReport |
| Places Tool | tools/places_search.py | ✅ Done | Uses ToolContext for API key |
| Image Tool | tools/image_generator.py | ✅ Done | Gemini 2.0 Flash Exp |
| Callbacks | callbacks/pipeline_callbacks.py | ✅ Done | Full logging + artifacts |
| MarketResearchAgent | sub_agents/market_research.py | ✅ Done | google_search tool |
| CompetitorMappingAgent | sub_agents/competitor_mapping.py | ✅ Done | search_places tool |
| GapAnalysisAgent | sub_agents/gap_analysis.py | ✅ Done | BuiltInCodeExecutor |
| StrategyAdvisorAgent | sub_agents/strategy_advisor.py | ✅ Done | BuiltInPlanner + output_schema |
| ReportGeneratorAgent | sub_agents/report_generator.py | ✅ Done | HTML generation |
| InfographicGeneratorAgent | sub_agents/infographic_generator.py | ✅ Done | generate_infographic tool |
| Root Agent | agent.py | ✅ Done | SequentialAgent with 6 sub-agents |
| Testing | adk web | ⏳ Ready | Ready to test |

---

## Key ADK Patterns Used

### 1. State via output_key
```python
LlmAgent(
    output_key="market_research_findings"  # Auto-saves to state
)
```

### 2. State Injection in Instructions
```python
instruction="Research {target_location} for {business_type}..."
# Variables are auto-injected from session state
```

### 3. Custom FunctionTool with ToolContext
```python
def search_places(query: str, tool_context: ToolContext) -> dict:
    api_key = tool_context.state.get("maps_api_key")
    # ...
```

### 4. BuiltInCodeExecutor
```python
from google.adk.code_executors import BuiltInCodeExecutor
LlmAgent(code_executor=BuiltInCodeExecutor())
```

### 5. BuiltInPlanner with ThinkingConfig
```python
from google.adk.planners import BuiltInPlanner
from google.genai.types import ThinkingConfig

LlmAgent(
    planner=BuiltInPlanner(
        thinking_config=ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048
        )
    )
)
```

### 6. Structured Output with Pydantic
```python
from pydantic import BaseModel
class MyOutput(BaseModel):
    field: str

LlmAgent(output_schema=MyOutput)
```

### 7. Callbacks
```python
def before_cb(callback_context: CallbackContext):
    callback_context.state["key"] = "value"
    return None  # Continue

async def after_cb(callback_context: CallbackContext):
    await callback_context.save_artifact("file.txt", part)

LlmAgent(
    before_agent_callback=before_cb,
    after_agent_callback=after_cb
)
```

### 8. SequentialAgent
```python
from google.adk.agents import SequentialAgent
root_agent = SequentialAgent(
    name="Pipeline",
    sub_agents=[agent1, agent2, agent3]
)
```

---

## Environment Variables Required

Using **Google AI Studio** (API key authentication):

```bash
# Required - Get from https://aistudio.google.com/app/apikey
export GOOGLE_API_KEY="your-google-api-key"

# Required - Must be FALSE for AI Studio
export GOOGLE_GENAI_USE_VERTEXAI=FALSE

# Required for competitor mapping - Enable Places API in Google Cloud Console
export MAPS_API_KEY="your-maps-api-key"
```

Or create a `.env` file (copy from `.env.example`):
```env
GOOGLE_API_KEY=your_google_api_key
GOOGLE_GENAI_USE_VERTEXAI=FALSE
MAPS_API_KEY=your_maps_api_key
```

---

## Run Commands
```bash
# From build-with-adk directory
adk web retail_ai_location_strategy_adk
adk run retail_ai_location_strategy_adk
```

---

## Troubleshooting

### Common Issues
1. **Import errors**: Check all __init__.py exports
2. **State not found**: Verify output_key is set on previous agent
3. **Tool not called**: Check tool function signature and docstring
4. **adk web fails**: Ensure root_agent is exported from agent.py

---

## Files Created (for context recovery)

1. `retail_ai_location_strategy_adk/__init__.py`
2. `retail_ai_location_strategy_adk/agent.py`
3. `retail_ai_location_strategy_adk/config.py`
4. `retail_ai_location_strategy_adk/requirements.txt`
5. `retail_ai_location_strategy_adk/.env.example`
6. `retail_ai_location_strategy_adk/schemas/__init__.py`
7. `retail_ai_location_strategy_adk/schemas/report_schema.py`
8. `retail_ai_location_strategy_adk/tools/__init__.py`
9. `retail_ai_location_strategy_adk/tools/places_search.py`
10. `retail_ai_location_strategy_adk/tools/image_generator.py`
11. `retail_ai_location_strategy_adk/callbacks/__init__.py`
12. `retail_ai_location_strategy_adk/callbacks/pipeline_callbacks.py`
13. `retail_ai_location_strategy_adk/sub_agents/__init__.py`
14. `retail_ai_location_strategy_adk/sub_agents/market_research.py`
15. `retail_ai_location_strategy_adk/sub_agents/competitor_mapping.py`
16. `retail_ai_location_strategy_adk/sub_agents/gap_analysis.py`
17. `retail_ai_location_strategy_adk/sub_agents/strategy_advisor.py`
18. `retail_ai_location_strategy_adk/sub_agents/report_generator.py`
19. `retail_ai_location_strategy_adk/sub_agents/infographic_generator.py`
