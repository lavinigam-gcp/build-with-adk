# Makefile for Ad Campaign Agent
# Compatible with agent-starter-pack deployment

.PHONY: install dev playground deploy deploy-ae clean help test test-unit test-integration test-e2e test-all test-coverage

# ============================================================================
# LOCAL DEVELOPMENT
# ============================================================================

## Install dependencies
install:
	@echo "Setting up virtual environment..."
	python -m venv .venv
	@echo "Installing dependencies..."
	.venv/bin/pip install -r app/requirements.txt
	@echo ""
	@echo "Installation complete!"
	@echo "Activate the virtual environment: source .venv/bin/activate"

## Install dependencies with uv (faster alternative)
install-uv:
	@command -v uv >/dev/null 2>&1 || { echo "uv is not installed. Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv venv .venv
	uv pip install -r app/requirements.txt

## Run agent locally with ADK web UI
dev:
	@if [ -d ".venv" ]; then \
		.venv/bin/adk web app --port 8501; \
	else \
		adk web app --port 8501; \
	fi

## Alias for dev
playground: dev

## Run with pip-installed adk (no venv)
dev-global:
	adk web app --port 8501

# ============================================================================
# DEPLOYMENT
# ============================================================================

## Deploy to Cloud Run (with ADK Web UI)
deploy:
	@echo "Deploying to Cloud Run..."
	./scripts/deploy.sh

## Deploy to Cloud Run with tracing
deploy-trace:
	./scripts/deploy.sh --trace

## Deploy to Agent Engine (managed service)
deploy-ae:
	@echo "Deploying to Agent Engine..."
	./scripts/deploy_ae.sh

## Deploy to Agent Engine with tracing
deploy-ae-trace:
	./scripts/deploy_ae.sh --trace

## Preview deployment commands without executing
deploy-dry-run:
	./scripts/deploy.sh --dry-run

deploy-ae-dry-run:
	./scripts/deploy_ae.sh --dry-run

# ============================================================================
# AGENT STARTER PACK INTEGRATION
# ============================================================================

## Create production-ready project with Agent Starter Pack
starter-pack:
	@echo "Creating production-ready project with Agent Starter Pack..."
	@echo ""
	@echo "Prerequisites: pip install agent-starter-pack"
	@echo ""
	pip install --upgrade agent-starter-pack
	agent-starter-pack create my-ad-campaign-agent -a adk@ad-campaign-agent

# ============================================================================
# GCP SETUP
# ============================================================================

## Setup GCP resources (bucket, APIs)
setup-gcp:
	./scripts/setup_gcp.sh

## Authenticate with Google Cloud
auth:
	gcloud auth login
	gcloud auth application-default login

# ============================================================================
# TESTING
# ============================================================================

## Run all tests (unit + integration, skip slow)
test: test-unit test-integration
	@echo ""
	@echo "All tests passed!"

## Run unit tests only (fast, no LLM calls)
test-unit:
	@echo "Running unit tests..."
	@if [ -d ".venv" ]; then \
		.venv/bin/pytest tests/unit -v --tb=short; \
	else \
		pytest tests/unit -v --tb=short; \
	fi

## Run integration tests (with LLM, skip slow)
test-integration:
	@echo "Running integration tests..."
	@if [ -d ".venv" ]; then \
		.venv/bin/pytest tests/integration -v --tb=short -m "not slow"; \
	else \
		pytest tests/integration -v --tb=short -m "not slow"; \
	fi

## Run end-to-end workflow tests
test-e2e:
	@echo "Running end-to-end tests..."
	@if [ -d ".venv" ]; then \
		.venv/bin/pytest tests/e2e -v --tb=short; \
	else \
		pytest tests/e2e -v --tb=short; \
	fi

## Run all tests including slow (Veo) tests
test-all:
	@echo "Running ALL tests including slow Veo tests..."
	@if [ -d ".venv" ]; then \
		.venv/bin/pytest tests/ -v --tb=short; \
	else \
		pytest tests/ -v --tb=short; \
	fi

## Run tests with coverage report
test-coverage:
	@echo "Running tests with coverage..."
	@if [ -d ".venv" ]; then \
		.venv/bin/pytest tests/ --cov=app --cov-report=html --cov-report=term-missing; \
	else \
		pytest tests/ --cov=app --cov-report=html --cov-report=term-missing; \
	fi
	@echo ""
	@echo "Coverage report generated: htmlcov/index.html"

# ============================================================================
# UTILITIES
# ============================================================================

## Clean build artifacts and caches
clean:
	rm -rf .venv __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned build artifacts"

## Reset database to fresh state
reset-db:
	@echo "Resetting database..."
	rm -f app/campaigns.db
	@echo "Database will be recreated on next run with demo data"

## Show help
help:
	@echo "Ad Campaign Agent - Makefile Commands"
	@echo ""
	@echo "LOCAL DEVELOPMENT:"
	@echo "  make install     - Install dependencies (creates .venv)"
	@echo "  make install-uv  - Install dependencies with uv (faster)"
	@echo "  make dev         - Run agent locally with ADK web UI (port 8501)"
	@echo "  make playground  - Alias for 'make dev'"
	@echo ""
	@echo "DEPLOYMENT:"
	@echo "  make deploy         - Deploy to Cloud Run (with Web UI)"
	@echo "  make deploy-trace   - Deploy to Cloud Run with Cloud Trace"
	@echo "  make deploy-ae      - Deploy to Agent Engine (managed)"
	@echo "  make deploy-ae-trace - Deploy to Agent Engine with tracing"
	@echo "  make deploy-dry-run - Preview Cloud Run deployment"
	@echo ""
	@echo "AGENT STARTER PACK:"
	@echo "  make starter-pack   - Create production project with CI/CD"
	@echo ""
	@echo "GCP SETUP:"
	@echo "  make setup-gcp   - Setup GCP resources (bucket, APIs)"
	@echo "  make auth        - Authenticate with Google Cloud"
	@echo ""
	@echo "TESTING:"
	@echo "  make test           - Run unit + integration tests (default)"
	@echo "  make test-unit      - Run unit tests only (fast, no LLM)"
	@echo "  make test-integration - Run integration tests (with LLM)"
	@echo "  make test-e2e       - Run end-to-end workflow tests"
	@echo "  make test-all       - Run ALL tests including slow Veo tests"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo ""
	@echo "UTILITIES:"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make reset-db    - Reset database to fresh state"
	@echo ""
	@echo "QUICK START:"
	@echo "  1. Create .env file in app/ folder (see .env.example)"
	@echo "  2. make install && make dev"
	@echo "  3. Open http://localhost:8501"
	@echo ""
	@echo "AUTHENTICATION SETUP:"
	@echo "  For Vertex AI (recommended):"
	@echo "    echo 'GOOGLE_GENAI_USE_VERTEXAI=TRUE' >> app/.env"
	@echo "    echo 'GOOGLE_CLOUD_PROJECT=your_project' >> app/.env"
	@echo "    echo 'GCS_BUCKET=your_bucket' >> app/.env"
	@echo ""
	@echo "  For AI Studio:"
	@echo "    echo 'GOOGLE_GENAI_USE_VERTEXAI=FALSE' >> app/.env"
	@echo "    echo 'GOOGLE_API_KEY=your_key' >> app/.env"
	@echo "    echo 'GCS_BUCKET=your_bucket' >> app/.env"
