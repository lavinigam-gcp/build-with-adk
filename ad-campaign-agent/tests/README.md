# Ad Campaign Agent - Test Suite

Comprehensive testing framework for validating all agents, tools, and workflows.

## Quick Start

```bash
# Run all fast tests (recommended for development)
make test

# Run only unit tests (~4 seconds)
make test-unit

# Run E2E workflow tests (~1 second)
make test-e2e

# Run everything including slow Veo tests (~10+ minutes)
make test-all
```

---

## Test Architecture

```
tests/
├── conftest.py              # Shared fixtures (DB copy, mocks)
├── README.md                # This file
│
├── unit/                    # Tool-level unit tests (no LLM)
│   ├── test_campaign_tools.py    # Campaign CRUD (7 tools)
│   ├── test_video_tools.py       # Media/video tools (8 tools)
│   ├── test_review_tools.py      # HITL workflow (10 tools)
│   ├── test_metrics_tools.py     # Analytics (8 tools)
│   └── test_maps_tools.py        # Geographic tools (5 tools)
│
├── integration/             # Agent-level tests (uses LLM)
│   ├── test_agents.py            # AgentEvaluator runner
│   └── eval_sets/                # EvalSet JSON files
│       ├── coordinator.test.json     # Routing tests
│       ├── campaign_agent.test.json
│       ├── media_agent.test.json
│       ├── review_agent.test.json
│       └── analytics_agent.test.json
│
└── e2e/                     # End-to-end workflow tests
    └── test_demo_workflows.py    # Demo scenario coverage
```

---

## Test Levels

| Level | Purpose | Speed | LLM Calls | Command |
|-------|---------|-------|-----------|---------|
| **Unit** | Test individual tools | ~4 sec | No | `make test-unit` |
| **E2E** | Test demo workflows | ~1 sec | No | `make test-e2e` |
| **Integration** | Test agent routing with real LLM | ~2-5 min | Yes | `make test-integration` |

---

## Database Isolation

Tests use a **copy** of the main `campaigns.db` to:

1. **Preserve demo data** - Tests run against real campaigns, products, videos
2. **Protect production** - Changes don't affect the main database
3. **Ensure consistency** - Each test starts with known state

### Fixtures

| Fixture | Scope | Use Case |
|---------|-------|----------|
| `test_db` | Function | Each test gets fresh DB copy |
| `shared_test_db` | Module | Shared copy for read-only tests |
| `fresh_test_db` | Function | Empty DB (no demo data) |

---

## Test Markers

Skip slow tests during development:

```bash
# Skip Veo and chart generation tests
pytest tests/ -m "not slow"

# Run only integration tests
pytest tests/ -m "integration"

# Run only Veo tests
pytest tests/ -m "veo"
```

### Available Markers

| Marker | Description |
|--------|-------------|
| `slow` | Tests taking >30 seconds (Veo, charts) |
| `integration` | Tests requiring LLM API calls |
| `veo` | Tests requiring Veo 3.1 API |
| `e2e` | End-to-end workflow tests |

---

## Running Specific Tests

```bash
# Run a single test file
pytest tests/unit/test_campaign_tools.py -v

# Run a specific test class
pytest tests/unit/test_review_tools.py::TestActivateVideo -v

# Run a specific test function
pytest tests/e2e/test_demo_workflows.py::TestAnalyticsWorkflow::test_campaign_metrics -v

# Run with verbose output and short tracebacks
pytest tests/unit -v --tb=short

# Run with coverage report
make test-coverage
```

---

## Unit Tests Coverage

### Campaign Tools (7 tests)
- `list_campaigns` - List all campaigns with filtering
- `get_campaign` - Get campaign by ID
- `create_campaign` - Create new campaign
- `update_campaign` - Update campaign status
- `get_campaign_locations` - Get store locations
- `search_nearby_stores` - Search for nearby retail stores
- `get_location_demographics` - Get city demographics

### Video Tools (10 tests)
- `list_products` - List 22 products with category filtering
- `get_variation_presets` - Get diversity/settings/moods presets
- `list_campaign_videos` - List videos by campaign
- `list_campaign_ads` - List ads for campaign
- `CreativeVariation` - Pydantic model validation
- Video generation parameter handling

### Review Tools (12 tests)
- `get_video_review_table` - Formatted review table
- `get_video_details` - Video metadata
- `list_pending_videos` - Videos awaiting activation
- `activate_video` - Single video activation
- `activate_batch` - Batch activation
- `pause_video` - Pause activated video
- `archive_video` - Archive with reason
- `get_video_status` - Check video status
- `get_activation_summary` - Status counts

### Metrics Tools (11 tests)
- `get_campaign_metrics` - Daily metrics with date range
- `get_top_performing_ads` - Top ads by RPI
- `get_campaign_insights` - Actionable insights
- `compare_campaigns` - Side-by-side comparison
- `generate_metrics_visualization` - AI charts

### Maps Tools (8 tests)
- `get_campaign_map_data` - Location data with coordinates
- `generate_static_map` - Google Static Maps
- `generate_map_visualization` - AI-generated maps

---

## E2E Workflow Tests

Tests based on [DEMO_GUIDE.md](../DEMO_GUIDE.md) scenarios:

| Act | Test Class | Coverage |
|-----|-----------|----------|
| Act 1 | `TestAgentDiscoveryWorkflow` | List campaigns, products, categories |
| Act 2 | `TestCreativeGenerationWorkflow` | Variation presets, video listing |
| Act 3 | `TestHITLReviewWorkflow` | Review table, activation, summary |
| Act 4 | `TestAnalyticsWorkflow` | Metrics, top performers, comparison |
| Act 5 | `TestGeographicIntelligenceWorkflow` | Map data, locations |
| Act 6 | `TestOptimizationWorkflow` | Insights, campaign details |

Additional coverage:
- `TestMultiAgentWorkflow` - Cross-agent coordination
- `TestEdgeCases` - Invalid IDs, empty data handling
- `TestDataConsistency` - Campaign-product-video consistency

---

## Integration Tests (EvalSet Format)

Integration tests use ADK's `AgentEvaluator` with EvalSet JSON files:

```json
{
  "eval_set_id": "campaign-agent-tests",
  "eval_cases": [
    {
      "eval_id": "list-all-campaigns",
      "conversation": [
        {
          "user_content": {"parts": [{"text": "What campaigns do we have?"}]},
          "intermediate_data": {
            "tool_uses": [{"name": "list_campaigns", "args": {}}]
          }
        }
      ]
    }
  ]
}
```

Run integration tests:

```bash
# Note: Requires GOOGLE_CLOUD_PROJECT and Gemini API access
make test-integration
```

---

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make test` | Run unit + E2E tests (default) |
| `make test-unit` | Run unit tests only |
| `make test-e2e` | Run E2E workflow tests |
| `make test-integration` | Run LLM integration tests |
| `make test-all` | Run all tests including slow |
| `make test-coverage` | Generate HTML coverage report |

---

## Environment Variables

Tests mock most external services, but some tests may need:

| Variable | Required For |
|----------|-------------|
| `GOOGLE_CLOUD_PROJECT` | Integration tests with real LLM |
| `GOOGLE_MAPS_API_KEY` | Location/maps tests (skipped if missing) |
| `GCS_BUCKET` | Storage tests (mocked by default) |

---

## Writing New Tests

### Unit Test Example

```python
# tests/unit/test_my_tools.py
import pytest

class TestMyTool:
    def test_my_tool_basic(self, test_db):
        """Test description."""
        from app.tools.my_tools import my_tool

        result = my_tool(param=1)

        assert "expected_key" in result
        assert result["status"] == "success"

    @pytest.mark.slow
    def test_my_tool_slow(self, test_db):
        """Test that takes a long time."""
        # Mark with @pytest.mark.slow for selective execution
        pass
```

### E2E Test Example

```python
# tests/e2e/test_my_workflow.py
class TestMyWorkflow:
    def test_workflow_step(self, shared_test_db):
        """Test a demo workflow step."""
        from app.tools.tool_a import tool_a
        from app.tools.tool_b import tool_b

        # Step 1
        result_a = tool_a()
        assert "data" in result_a

        # Step 2 (uses Step 1 output)
        result_b = tool_b(id=result_a["data"][0]["id"])
        assert result_b["status"] == "success"
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: app` | Run from `ad-campaign-agent/` directory |
| `GOOGLE_MAPS_API_KEY not set` | Test skipped (expected behavior) |
| `Database locked` | Close other connections to campaigns.db |
| `Veo tests timeout` | Mark with `@pytest.mark.slow`, run with `make test-all` |

---

## CI/CD Integration

For GitHub Actions or Cloud Build:

```yaml
# .github/workflows/test.yml
- name: Run Tests
  run: |
    pip install -r app/requirements.txt
    make test
```

The default `make test` runs fast tests suitable for CI (~5 seconds).
