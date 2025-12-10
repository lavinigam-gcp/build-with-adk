# Part 8: Testing Your Agent

You've built a complete multi-agent pipeline that transforms natural language into strategic reports, infographics, and audio briefings. It works on your laptop. But how do you know it will keep working after you change a prompt, upgrade a model, or refactor a tool?

Testing LLM-based agents is fundamentally different from testing traditional software. The same input can produce different valid outputs. External APIs return different data over time. "Correct" is often subjective. This part establishes a testing strategy that handles this uncertainty—unit tests for fast feedback, integration tests for real agent behavior, and evaluations for measuring quality over time.

<p align="center">
  <img src="assets/part8_testing_pyramid.jpeg" alt="Part 8: Testing Pyramid for AI Agents" width="600">
</p>

---

## The Challenge: Non-Deterministic Outputs

Testing traditional software is straightforward: given input X, expect output Y. But LLM-based agents break this model fundamentally.

Consider this scenario: You ask the IntakeAgent to parse "I want to open a coffee shop in Bangalore." Today it extracts `{"target_location": "Bangalore, India", "business_type": "coffee shop"}`. Tomorrow, with the exact same input, it might return `{"target_location": "Bangalore, Karnataka, India", "business_type": "specialty coffee shop"}`. Both are correct. Neither matches exactly.

This non-determinism cascades through the pipeline. The MarketResearchAgent searches the web—but web results change daily. The CompetitorMappingAgent calls Google Maps—but businesses open and close. The GapAnalysisAgent writes Python code—but the specific code varies run to run.

The unique challenges of testing AI agents:

| Challenge | Why It Matters |
|-----------|----------------|
| **Non-deterministic outputs** | Same input produces different valid outputs |
| **External dependencies** | APIs (search, maps, LLMs) return different data over time |
| **Emergent behavior** | Multi-agent pipelines create complex interactions |
| **Quality vs. correctness** | "Good enough" is often the right bar, not "exactly right" |

Testing AI agents isn't about asserting exact matches—it's about validating that behavior stays within acceptable bounds across runs.

---

## The Testing Pyramid for AI Agents

The traditional testing pyramid applies to AI agents, but with different characteristics at each level:

| Level | Speed | API Calls | Purpose |
|-------|-------|-----------|---------|
| **Unit Tests** | ~2 seconds | None | Validate schemas, utilities, configurations |
| **Integration Tests** | ~2-5 minutes | Yes | Test individual agents with real API calls |
| **Evaluations** | ~30-60 minutes | Yes | Measure response quality over time |

Each level answers a different question. Unit tests ask "Is the code structurally correct?" Integration tests ask "Does the agent work?" Evaluations ask "How well does it work?"

> **Learn more:** The [ADK Evaluation documentation](https://google.github.io/adk-docs/evaluate/) covers the full testing and evaluation framework.

---

## Unit Tests: Fast, No API Calls

Unit tests validate the deterministic parts of your agent: Pydantic schemas, utility functions, configuration parsing. They run in seconds and don't require API keys.

### Example: Schema Validation

The `LocationIntelligenceReport` schema has validation constraints like `ge=0, le=100` for scores. Unit tests verify these constraints work:

```python
# tests/unit/test_schemas.py
import pytest
from app.schemas.report_schema import (
    LocationIntelligenceReport,
    LocationRecommendation,
    StrengthAnalysis,
    ConcernAnalysis,
    CompetitionProfile,
    MarketCharacteristics,
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
            top_recommendation=self._create_sample_recommendation(),
            alternative_locations=[],
            key_insights=["Insight 1"],
            methodology_summary="Summary",
        )
        assert report.target_location == "Bangalore, India"
        assert report.zones_analyzed == 4

    def test_invalid_score_too_high(self):
        """Test that score must be <= 100."""
        with pytest.raises(ValueError):
            self._create_sample_recommendation(overall_score=150)

    def test_invalid_score_negative(self):
        """Test that score must be >= 0."""
        with pytest.raises(ValueError):
            self._create_sample_recommendation(overall_score=-10)

    def _create_sample_recommendation(self, overall_score=78):
        return LocationRecommendation(
            location_name="Defence Colony",
            area="Indiranagar",
            overall_score=overall_score,
            opportunity_type="Residential Premium",
            strengths=[],
            concerns=[],
            competition=CompetitionProfile(...),
            market=MarketCharacteristics(...),
            best_customer_segment="Young professionals",
            estimated_foot_traffic="Moderate",
            next_steps=["Scout properties"],
        )
```

Run unit tests with:

```bash
make test-unit  # ~2 seconds, no API calls
```

Unit tests catch schema changes that would break downstream processing. If you add a required field to `LocationIntelligenceReport`, unit tests fail immediately—before you waste time on slow integration tests.

---

## Integration Tests: Real Agent Behavior

Integration tests run actual agents with real API calls. They're slower but validate that agents behave correctly end-to-end.

### The `run_agent_test` Helper

The project includes a helper function that runs agents in isolation and returns both the response and final state:

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

This helper uses `InMemorySessionService` for test isolation—each test gets a fresh session without persisting to any database.

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

        # Check location extracted (flexible matching)
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

Notice the flexible assertions. We don't assert `target_location == "Indiranagar, Bangalore"` exactly. Instead, we check that it contains "bangalore" or "indiranagar". This accommodates the natural variation in LLM outputs while still validating correctness.

Run integration tests with:

```bash
make test-intake    # Just IntakeAgent (~30 seconds)
make test-agents    # All agents (~2-5 minutes)
```

---

## Testing Agents That Depend on State

Some agents need prior state to function. The MarketResearchAgent expects `target_location` and `business_type` to already exist in state. Pre-populate this in tests:

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

The `session_state` parameter lets you inject the state that would normally come from upstream agents. This enables testing agents in isolation without running the full pipeline.

---

## ADK Evaluations: Measuring Quality

Integration tests answer "Does it work?" Evaluations answer "How well does it work?" They measure semantic similarity between actual outputs and expected outputs, giving you a quality score rather than a binary pass/fail.

<p align="center">
  <img src="assets/part8_concept_comparison.jpeg" alt="Tests vs Evaluations: Different Questions" width="600">
</p>

### EvalSet Format

Evaluations use JSON files that define test cases with expected outputs:

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

The `final_response` is the expected output. ADK's evaluation framework compares actual agent responses to this expected output using semantic similarity.

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
| `response_match_score` | Semantic similarity to expected output (0-1) | > 0.6 |
| `tool_trajectory_avg_score` | How well tool usage matches expected pattern | > 0.8 |

A `response_match_score` of 0.6 means the response is semantically similar to the expected output, even if the exact words differ. This is perfect for LLM outputs where "coffee shop in Bangalore, Karnataka" and "Bangalore coffee shop" mean the same thing.

---

## Tests vs Evaluations: When to Use What

| Aspect | Tests | Evaluations |
|--------|-------|-------------|
| **Question** | "Does it work?" | "How well does it work?" |
| **Output** | Pass/Fail | Score (0.0-1.0) |
| **Speed** | Fast (2-5 min) | Slow (30-60 min) |
| **When to run** | Every commit | Pre-release |

Use this decision matrix:

| Scenario | What to Run |
|----------|-------------|
| Changed a Pydantic schema | `make test-unit` |
| Modified an agent prompt | `make test-agents` + `make eval` |
| Upgrading model version | `make eval` (compare before/after) |
| Fixed a bug in a tool | `make test-agents` |
| Preparing a release | Full suite + evals |

---

## CI/CD Pipeline

A production-grade pipeline runs different test levels at different stages:

```yaml
# On every commit
- make test-unit        # ~2 seconds

# On pull requests
- make test-agents      # ~2-5 minutes

# Before release
- make eval             # ~30-60 minutes
- Compare scores to baseline
- Block release if scores drop significantly
```

This balances fast feedback (unit tests on every commit) with thorough validation (evals before release).

---

## Best Practices

### 1. Test Agents in Isolation

Test each sub-agent before running the full pipeline. This makes failures easier to diagnose:

```
IntakeAgent → MarketResearchAgent → CompetitorMappingAgent → ...
```

If the full pipeline fails, you don't know which agent broke. If you test each agent in isolation, you know exactly where the problem is.

### 2. Use Appropriate Timeouts

Different agents take different amounts of time:

| Agent | Recommended Timeout |
|-------|---------------------|
| IntakeAgent | 60s |
| MarketResearchAgent | 120s |
| GapAnalysisAgent | 180s |
| Full pipeline | 600s |

Set timeouts with `@pytest.mark.timeout(60)` to prevent hung tests.

### 3. Validate State, Not Just Response

The response text is often less important than the state changes:

```python
# Check state structure
state = result["state"]
assert "target_location" in state
assert len(state.get("market_research_findings", "")) > 50

# Also check response exists
assert result["response"] is not None
```

### 4. Use Fixtures for Common State

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

Fixtures reduce duplication and make tests easier to maintain.

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

In this part, you've established a testing strategy for AI agents:

- **Unit tests** validate schemas and utilities without API calls
- **Integration tests** run real agents with the `run_agent_test` helper
- **Flexible assertions** accommodate non-deterministic LLM outputs
- **State pre-population** enables testing agents in isolation
- **ADK evaluations** measure response quality with semantic similarity
- **CI/CD pipelines** balance fast feedback with thorough validation

Testing AI agents requires accepting that "correct" isn't a binary—it's a spectrum. The goal is to catch regressions while allowing for the natural variation inherent in LLM outputs.

---

## Quick Reference

| Test Type | Command | When to Run | API Calls |
|-----------|---------|-------------|-----------|
| Unit | `make test-unit` | Every commit | No |
| Integration | `make test-agents` | Pull requests | Yes |
| Evaluation | `make eval` | Pre-release | Yes |

**Files referenced in this part:**

- [`tests/README.md`](../tests/README.md) — Comprehensive testing guide
- [`tests/conftest.py`](../tests/conftest.py) — Shared fixtures and helpers
- [`tests/unit/test_schemas.py`](../tests/unit/test_schemas.py) — Unit tests
- [`tests/integration/test_agents.py`](../tests/integration/test_agents.py) — Integration tests
- [`tests/evalsets/`](../tests/evalsets/) — Evaluation datasets

**ADK Documentation:**

- [Testing & Evaluation](https://google.github.io/adk-docs/evaluate/) — ADK's evaluation framework
- [Runners](https://google.github.io/adk-docs/runtime/runners/) — Running agents programmatically
- [Sessions](https://google.github.io/adk-docs/sessions/) — Session management for testing

---

## Next: Production Deployment

Your agent is tested and validated. It works on your laptop at `localhost:8501`. But your stakeholders aren't going to SSH into your machine to use it. They need a URL they can bookmark and share.

In **[Part 9: Production Deployment](./09-production-deployment.md)**, you'll take this agent from local development to production. You'll learn two deployment options: Cloud Run for containerized deployment with IAP authentication, and Vertex AI Agent Engine for a fully managed experience. Either way, you'll end with a secure, scalable URL that your team can actually use.

You'll learn:
- **Cloud Run** deployment with Docker and IAP authentication
- **Vertex AI Agent Engine** for fully managed hosting
- Environment configuration for production
- Monitoring and observability setup

---

**[← Back to Part 7: Artifact Generation](./07-artifact-generation.md)** | **[Continue to Part 9: Production Deployment →](./09-production-deployment.md)**
