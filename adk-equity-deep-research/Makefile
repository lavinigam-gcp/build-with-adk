# Makefile for Equity Research Agent
# Simplifies setup and running of the agent

.PHONY: install dev auth setup sandbox clean help

# ============================================================================
# QUICK START (run these in order for first-time setup)
# ============================================================================

## Full automated setup (auth + install + env + sandbox)
setup: auth install env-setup sandbox
	@echo ""
	@echo "============================================"
	@echo "Setup complete! Run 'make dev' to start."
	@echo "============================================"

# ============================================================================
# LOCAL DEVELOPMENT
# ============================================================================

## Install dependencies (creates .venv)
install:
	@echo "Creating virtual environment..."
	python -m venv .venv
	@echo "Installing dependencies..."
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo ""
	@echo "Installation complete!"

## Install with uv (faster alternative)
install-uv:
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv venv .venv
	uv pip install -r requirements.txt

## Run agent locally with ADK web UI
dev:
	@if [ ! -f ".env" ]; then \
		echo "Error: .env file not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@if [ -d ".venv" ]; then \
		cd app && ../.venv/bin/adk web; \
	else \
		cd app && adk web; \
	fi

## Alias for dev
playground: dev

# ============================================================================
# GCP AUTHENTICATION
# ============================================================================

## Authenticate with Google Cloud
auth:
	@echo "Authenticating with Google Cloud..."
	@echo ""
	gcloud auth login
	gcloud auth application-default login
	@echo ""
	@echo "Authentication complete!"

## Set GCP project
set-project:
	@read -p "Enter your GCP Project ID: " project_id; \
	gcloud config set project $$project_id; \
	echo "Project set to: $$project_id"

# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

## Interactive .env file setup
env-setup:
	@if [ -f ".env" ]; then \
		echo ".env file already exists. Skipping..."; \
	else \
		echo "Creating .env file..."; \
		read -p "Enter your GCP Project ID: " project_id; \
		echo "GOOGLE_CLOUD_PROJECT=$$project_id" > .env; \
		echo "GOOGLE_CLOUD_LOCATION=us-central1" >> .env; \
		echo "GOOGLE_GENAI_USE_VERTEXAI=1" >> .env; \
		echo "SANDBOX_RESOURCE_NAME=" >> .env; \
		echo ""; \
		echo ".env file created. Sandbox will be configured next."; \
	fi

## Create Agent Engine Sandbox for chart generation
sandbox:
	@echo "Creating Agent Engine Sandbox..."
	@echo "This may take 1-2 minutes..."
	@echo ""
	@if [ -f ".env" ]; then set -a && . ./.env && set +a; fi; \
	if [ -d ".venv" ]; then \
		SANDBOX_NAME=$$(.venv/bin/python manage_sandbox.py create 2>&1 | grep -o 'projects/[^"]*' | head -1); \
	else \
		SANDBOX_NAME=$$(python manage_sandbox.py create 2>&1 | grep -o 'projects/[^"]*' | head -1); \
	fi; \
	if [ -n "$$SANDBOX_NAME" ]; then \
		echo ""; \
		echo "Sandbox created: $$SANDBOX_NAME"; \
		if [ -f ".env" ]; then \
			sed -i '' "s|^SANDBOX_RESOURCE_NAME=.*|SANDBOX_RESOURCE_NAME=$$SANDBOX_NAME|" .env 2>/dev/null || \
			sed -i "s|^SANDBOX_RESOURCE_NAME=.*|SANDBOX_RESOURCE_NAME=$$SANDBOX_NAME|" .env; \
			echo "Updated .env with sandbox resource name."; \
		fi; \
	else \
		echo "Run sandbox creation manually:"; \
		echo "  python manage_sandbox.py create"; \
		echo "Then add SANDBOX_RESOURCE_NAME to your .env file"; \
	fi

## List existing sandboxes
sandbox-list:
	@if [ -f ".env" ]; then set -a && . ./.env && set +a; fi; \
	if [ -d ".venv" ]; then \
		.venv/bin/python manage_sandbox.py list; \
	else \
		python manage_sandbox.py list; \
	fi

# ============================================================================
# UTILITIES
# ============================================================================

## Clean build artifacts
clean:
	rm -rf .venv __pycache__ .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned build artifacts"

## Clean ADK session artifacts
clean-sessions:
	rm -rf .adk/artifacts
	@echo "Cleaned ADK session artifacts"

## Run tests
test:
	@if [ -d ".venv" ]; then \
		.venv/bin/pytest tests/ -v; \
	else \
		pytest tests/ -v; \
	fi

# ============================================================================
# HELP
# ============================================================================

## Show help
help:
	@echo "Equity Research Agent - Makefile Commands"
	@echo ""
	@echo "QUICK START (first-time setup):"
	@echo "  make setup       - Full automated setup (auth + install + sandbox)"
	@echo ""
	@echo "DAILY USE:"
	@echo "  make dev         - Run agent with ADK web UI (http://localhost:8000)"
	@echo ""
	@echo "INDIVIDUAL COMMANDS:"
	@echo "  make install     - Install Python dependencies"
	@echo "  make install-uv  - Install with uv (faster)"
	@echo "  make auth        - Authenticate with Google Cloud"
	@echo "  make env-setup   - Create .env file interactively"
	@echo "  make sandbox     - Create Agent Engine Sandbox"
	@echo "  make sandbox-list - List existing sandboxes"
	@echo ""
	@echo "UTILITIES:"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make clean-sessions - Clean ADK session artifacts"
	@echo "  make test        - Run tests"
	@echo ""
	@echo "FIRST-TIME SETUP:"
	@echo "  1. make setup    (or run individual commands below)"
	@echo "  2. make dev"
	@echo "  3. Open http://localhost:8000"
	@echo ""
	@echo "PREREQUISITES:"
	@echo "  - Python 3.10+"
	@echo "  - Google Cloud SDK (gcloud)"
	@echo "  - Active GCP project with Vertex AI enabled"
