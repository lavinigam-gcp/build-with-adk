# Part 8: Testing Your Agent

By the end of this part, you'll have a testing strategy for validating your agent.

**Goal**: Ensure your agent works correctly with unit tests, integration tests, and evaluations.

---

## Why Test AI Agents?

Testing traditional software is straightforward: given input X, expect output Y. But LLM-based agents break this model fundamentally.

Consider this scenario: You ask the IntakeAgent to parse "I want to open a coffee shop in Bangalore." Today it extracts `{"target_location": "Bangalore, India", "business_type": "coffee shop"}`. Tomorrow, with the exact same input, it might return `{"target_location": "Bangalore, Karnataka, India", "business_type": "specialty coffee shop"}`. Both are correct. Neither matches exactly.

This non-determinism cascades through the pipeline. The MarketResearchAgent searches the web—but web results change daily. The CompetitorMappingAgent calls Google Maps—but businesses open and close. The GapAnalysisAgent writes Python code—but the specific code varies run to run.

**The unique challenges of testing AI agents:**

| Challenge | Why It Matters |
|-----------|----------------|
| **Non-deterministic outputs** | Same input produces different valid outputs |
| **External dependencies** | APIs (search, maps, LLMs) return different data over time |
| **Emergent behavior** | Multi-agent pipelines create complex interactions |
| **Quality vs. correctness** | "Good enough" is often the right bar, not "exactly right" |

Testing AI agents isn't about asserting exact matches—it's about validating that behavior stays within acceptable bounds across runs.

---

## The Testing Pyramid

```
                    ┌─────────────┐
                    │   Evals     │  ← Slow, comprehensive
                    │  (quality)  │     Run before releases
                    ├─────────────┤
                    │ Integration │  ← Medium speed
                    │   Tests     │     Run on PRs
                    ├─────────────┤
                    │    Unit     │  ← Fast, focused
                    │   Tests     │     Run on every commit
                    └─────────────┘
```

| Level | Speed | API Calls | Purpose |
|-------|-------|-----------|---------|
| Unit | ~2 seconds | 0 | Validate schemas, utilities |
| Integration | ~2-5 minutes | Yes | Test individual agents |
| Evaluations | ~30-60 minutes | Yes | Measure response quality |

---

## Unit Tests

Fast tests that don't require API keys. Great for schemas and data transformations.

### Example: Schema Validation

```python
# tests/unit/test_schemas.py
import pytest
from app.schemas.report_schema import (
    LocationIntelligenceReport,
    LocationRecommendation,
    StrengthAnalysis,
)

class TestLocationIntelligenceReport:
    """Test Pydantic schema validation."""

    def test_valid_report(self):
        """Test creating a valid report."""
        report = LocationIntelligenceReport(
            target_location="Bangalore, India",
            business_type="coffee shop",
            analysis_date="2025-01-15",
            market_validation="Strong market",
            total_competitors_found=15,
            zones_analyzed=4,
            top_recommendation=LocationRecommendation(...),
            alternative_locations=[],
            key_insights=["Insight 1"],
            methodology_summary="Summary",
        )
        assert report.target_location == "Bangalore, India"

    def test_invalid_score(self):
        """Test that score must be 0-100."""
        with pytest.raises(ValueError):
            LocationRecommendation(
                overall_score=150,  # Invalid!
                # ...
            )
```

**Run unit tests:**
```bash
make test-unit
```

---

## Integration Tests

Test real agent behavior with actual API calls.

### The `run_agent_test` Helper

The project includes a helper for running agents in isolation:

```python
# tests/conftest.py
async def run_agent_test(
    agent: Any,
    query: str,
    session_state: dict | None = None,
) -> dict[str, Any]:
    """
    Run a single agent with a query and return results.

    Returns:
        dict with:
        - 'response': The agent's text response
        - 'state': The updated session state
    """
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="test_app",
        session_service=session_service,
    )

    # Create session with initial state
    session = session_service.create_session(
        app_name="test_app",
        user_id="test_user",
        state=session_state or {},
    )

    # Run the agent
    response_text = ""
    async for event in runner.run_async(
        session_id=session.id,
        user_id="test_user",
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=query)],
        ),
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

    # Get final state
    final_session = session_service.get_session(
        app_name="test_app",
        user_id="test_user",
        session_id=session.id,
    )

    return {
        "response": response_text,
        "state": dict(final_session.state),
    }
```

### Testing IntakeAgent

```python
# tests/integration/test_agents.py
import pytest
from tests.conftest import run_agent_test

@pytest.mark.integration
class TestIntakeAgent:
    """Test IntakeAgent in isolation."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_parse_coffee_shop_bangalore(self):
        """Test parsing a coffee shop request."""
        from app.sub_agents.intake_agent import intake_agent

        result = await run_agent_test(
            agent=intake_agent,
            query="I want to open a coffee shop in Indiranagar, Bangalore",
        )

        # Verify state contains parsed values
        state = result["state"]
        assert "parsed_request" in state or "target_location" in state

        # Check location extracted
        target = state.get("target_location", "")
        assert "bangalore" in target.lower() or "indiranagar" in target.lower()

        # Check business type extracted
        business = state.get("business_type", "")
        assert "coffee" in business.lower()

    @pytest.mark.asyncio
    @pytest.mark.timeout(60)
    async def test_parse_gym_seattle(self):
        """Test parsing a gym request."""
        from app.sub_agents.intake_agent import intake_agent

        result = await run_agent_test(
            agent=intake_agent,
            query="Analyze downtown Seattle for a gym",
        )

        state = result["state"]
        assert "seattle" in state.get("target_location", "").lower()
        assert "gym" in state.get("business_type", "").lower()
```

**Run integration tests:**
```bash
# Quick test - just IntakeAgent
make test-intake

# All agents
make test-agents
```

---

## Testing Agents That Depend on State

Some agents need prior state. Pre-populate it in tests:

```python
@pytest.mark.asyncio
@pytest.mark.timeout(120)
async def test_market_research(self):
    """Test MarketResearchAgent with pre-populated state."""
    from app.sub_agents.market_research import market_research_agent

    result = await run_agent_test(
        agent=market_research_agent,
        query="Research the market for this business",
        session_state={
            "target_location": "Indiranagar, Bangalore",
            "business_type": "coffee shop",
        },
    )

    state = result["state"]
    assert "market_research_findings" in state
    assert len(state["market_research_findings"]) > 100
```

---

## ADK Evaluations

Evaluations measure response quality, not just correctness.

### EvalSet Format

```json
{
  "eval_set_id": "intake_eval",
  "name": "IntakeAgent Evaluation",
  "description": "Tests request parsing accuracy",
  "eval_cases": [
    {
      "eval_id": "coffee_bangalore",
      "conversation": [
        {
          "invocation_id": "inv-001",
          "user_content": {
            "parts": [{"text": "I want to open a coffee shop in Bangalore"}],
            "role": "user"
          },
          "final_response": {
            "parts": [{"text": "target_location: Bangalore, business_type: coffee shop"}],
            "role": "model"
          }
        }
      ],
      "session_input": {
        "app_name": "retail_location_strategy",
        "user_id": "test_user",
        "state": {}
      }
    }
  ]
}
```

### Running Evaluations

```bash
# Run all evalsets
make eval

# Run specific evalset
uv run adk eval app tests/evalsets/intake.evalset.json
```

### Evaluation Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| `response_match_score` | Semantic similarity (0-1) | > 0.6 |
| `tool_trajectory_avg_score` | Tool usage accuracy | > 0.8 |

---

## Tests vs Evaluations

| Aspect | Tests | Evaluations |
|--------|-------|-------------|
| **Question** | "Does it work?" | "How well does it work?" |
| **Output** | Pass/Fail | Score (0.0-1.0) |
| **Speed** | Fast | Slow |
| **When to run** | Every commit | Pre-release |

### When to Use What

| Scenario | Use |
|----------|-----|
| Changed Pydantic schema | `make test-unit` |
| Modified agent prompt | `make test-agents` + `make eval` |
| Upgrading model version | `make eval` (compare before/after) |
| Fixed a bug in a tool | `make test-agents` |
| Preparing a release | Full suite + evals |

---

## CI/CD Pipeline

A production-grade pipeline:

```yaml
# On every commit
- make test-unit        # ~2 seconds

# On pull requests
- make test-agents      # ~2-5 minutes

# Before release
- make eval             # ~30-60 minutes
- Compare scores to baseline
- Block release if scores drop
```

---

## Best Practices

### 1. Test Agents in Isolation

Test each sub-agent before the full pipeline:
```
IntakeAgent → MarketResearchAgent → CompetitorMappingAgent → ...
```

### 2. Use Appropriate Timeouts

| Agent | Timeout |
|-------|---------|
| IntakeAgent | 60s |
| MarketResearchAgent | 120s |
| GapAnalysisAgent | 180s |
| Full pipeline | 600s |

### 3. Validate State, Not Just Response

```python
# Check state structure
state = result["state"]
assert "target_location" in state
assert len(state.get("market_research_findings", "")) > 50

# Also check response exists
assert result["response"] is not None
```

### 4. Use Fixtures

```python
# conftest.py
@pytest.fixture
def sample_intake_state() -> dict:
    return {
        "target_location": "Indiranagar, Bangalore",
        "business_type": "coffee shop",
    }

# test_agents.py
async def test_market_research(self, sample_intake_state):
    result = await run_agent_test(
        agent=market_research_agent,
        query="Research the market",
        session_state=sample_intake_state,
    )
```

---

## Commands Reference

```bash
# Unit tests (fast, no API calls)
make test-unit

# IntakeAgent only (~30 seconds)
make test-intake

# All individual agents (~2-5 minutes)
make test-agents

# Full pipeline (~15-30 minutes)
make test-integration

# Evaluations
make eval
make eval-intake
```

---

## What You've Learned

In this part, you:

1. Understood the testing pyramid for AI agents
2. Created unit tests for Pydantic schemas
3. Built integration tests using `run_agent_test`
4. Learned about ADK evaluations and metrics
5. Established CI/CD best practices

---

## Next Up

Your agent is tested and validated. It works on your laptop at `localhost:8501`. But your stakeholders aren't going to SSH into your machine to use it. They need a URL.

In [Part 9: Production Deployment](./09-production-deployment.md), we'll take this agent from local development to production. You'll deploy to Cloud Run with IAP authentication, or to Vertex AI Agent Engine for a fully managed experience. Either way, you'll end with a secure, scalable URL that your team can actually use.

---

**Code files referenced in this part:**
- [`tests/README.md`](../tests/README.md) - Comprehensive testing guide
- [`tests/conftest.py`](../tests/conftest.py) - Shared fixtures
- [`tests/unit/test_schemas.py`](../tests/unit/test_schemas.py) - Unit tests
- [`tests/integration/test_agents.py`](../tests/integration/test_agents.py) - Integration tests
- [`tests/evalsets/`](../tests/evalsets/) - Evaluation datasets

**ADK Documentation:**
- [Testing](https://google.github.io/adk-docs/evaluate/)
- [Evaluations](https://google.github.io/adk-docs/evaluate/)

---

<details>
<summary>Image Prompts for This Part</summary>

### Image 1: Testing Pyramid

```json
{
  "image_type": "testing_pyramid",
  "style": {
    "design": "clean, technical documentation style",
    "color_scheme": "Google Cloud colors (blue #4285F4, red #EA4335, yellow #FBBC05, green #34A853) with white background",
    "layout": "pyramid with annotations",
    "aesthetic": "minimalist"
  },
  "dimensions": {"aspect_ratio": "4:3", "recommended_width": 800},
  "title": {"text": "Part 8: Testing Your Agent", "position": "top center"},
  "sections": [
    {
      "id": "pyramid",
      "layout": "triangle/pyramid",
      "layers": [
        {"level": 1, "name": "Unit Tests", "color": "#E8F5E9", "time": "~2 seconds", "command": "make test-unit"},
        {"level": 2, "name": "Integration Tests", "color": "#FFF3E0", "time": "~2-5 minutes", "command": "make test-agents"},
        {"level": 3, "name": "Evaluations", "color": "#FCE4EC", "time": "Quality metrics", "command": "make eval"}
      ]
    },
    {
      "id": "axis",
      "position": "right",
      "annotations": [
        {"arrow": "up", "label": "Cost & Time"},
        {"arrow": "down", "label": "Speed & Coverage"}
      ]
    }
  ]
}
```

### Image 2: Tests vs Evaluations Concept

```json
{
  "image_type": "concept_comparison",
  "style": {
    "design": "side-by-side comparison diagram",
    "color_scheme": "Google Cloud colors (green #34A853 for tests, blue #4285F4 for evals)",
    "layout": "two-column comparison",
    "aesthetic": "clean, educational"
  },
  "dimensions": {"aspect_ratio": "16:9", "recommended_width": 1000},
  "title": {"text": "Tests vs Evaluations: Different Questions", "position": "top center"},
  "concept": "Illustrate the fundamental difference between pass/fail testing and quality scoring",
  "sections": [
    {
      "id": "tests",
      "position": "left half",
      "label": "Integration Tests",
      "color": "#E8F5E9",
      "icon": "checkmark in circle",
      "question": "Does it work?",
      "output_type": "Pass / Fail",
      "characteristics": [
        {"name": "Speed", "value": "Fast (2-5 min)"},
        {"name": "Frequency", "value": "Every commit"},
        {"name": "Validation", "value": "State contains expected keys"},
        {"name": "Example", "value": "'target_location' in state"}
      ],
      "use_when": "After modifying agent code"
    },
    {
      "id": "evals",
      "position": "right half",
      "label": "Evaluations",
      "color": "#E3F2FD",
      "icon": "gauge/meter",
      "question": "How well does it work?",
      "output_type": "Score (0.0 - 1.0)",
      "characteristics": [
        {"name": "Speed", "value": "Slow (30-60 min)"},
        {"name": "Frequency", "value": "Pre-release"},
        {"name": "Validation", "value": "Semantic similarity to ideal"},
        {"name": "Example", "value": "response_match_score > 0.6"}
      ],
      "use_when": "Before deploying to production"
    }
  ],
  "bottom_annotation": {
    "text": "Tests catch regressions fast; Evals ensure quality over time",
    "position": "bottom center"
  }
}
```

</details>
