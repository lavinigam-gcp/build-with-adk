# Makefile for Retail AI Location Strategy Agent
# Follows the deep-search/gemini-fullstack pattern from adk-samples

# Agent directory name (current directory)
AGENT_DIR = retail_ai_location_strategy_adk

.PHONY: install dev playground backend deploy-cloud-run test clean help

# ============================================================================
# LOCAL DEVELOPMENT
# ============================================================================

## Install dependencies
install:
	uv sync

## Run agent locally with ADK web UI (default: AI Studio auth)
## Run from parent directory to allow adk web to find the agent
dev:
	cd .. && uv run adk web $(AGENT_DIR)

## Alias for dev
playground: dev

# ============================================================================
# DEPLOYMENT
# ============================================================================

## Deploy to Vertex AI Agent Engine
backend:
	uv sync --group deployment
	cd .. && uv build --wheel --out-dir $(AGENT_DIR)/deployment
	cd deployment && uv run python deploy.py --create

## Deploy to Cloud Run
deploy-cloud-run:
	cd .. && uv run adk deploy cloud_run \
		--project=$(GOOGLE_CLOUD_PROJECT) \
		--region=$(GOOGLE_CLOUD_LOCATION) \
		$(AGENT_DIR)

# ============================================================================
# TESTING & UTILITIES
# ============================================================================

## Run tests
test:
	uv sync --dev
	uv run pytest tests/

## Clean build artifacts
clean:
	rm -rf .venv __pycache__ .pytest_cache
	rm -rf deployment/*.whl
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

## Show help
help:
	@echo "Retail AI Location Strategy Agent - Makefile Commands"
	@echo ""
	@echo "LOCAL DEVELOPMENT:"
	@echo "  make install     - Install dependencies with uv"
	@echo "  make dev         - Run agent locally with ADK web UI"
	@echo "  make playground  - Alias for 'make dev'"
	@echo ""
	@echo "DEPLOYMENT:"
	@echo "  make backend     - Deploy to Vertex AI Agent Engine"
	@echo "  make deploy-cloud-run - Deploy to Cloud Run"
	@echo ""
	@echo "TESTING & UTILITIES:"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Clean build artifacts"
	@echo ""
	@echo "AUTHENTICATION SETUP:"
	@echo "  For AI Studio (default):"
	@echo "    echo 'GOOGLE_GENAI_USE_VERTEXAI=FALSE' >> $(AGENT_DIR)/.env"
	@echo "    echo 'GOOGLE_API_KEY=your_key' >> $(AGENT_DIR)/.env"
	@echo ""
	@echo "  For Vertex AI:"
	@echo "    echo 'GOOGLE_GENAI_USE_VERTEXAI=TRUE' >> $(AGENT_DIR)/.env"
	@echo "    echo 'GOOGLE_CLOUD_PROJECT=your_project' >> $(AGENT_DIR)/.env"
	@echo "    echo 'GOOGLE_CLOUD_LOCATION=us-central1' >> $(AGENT_DIR)/.env"
