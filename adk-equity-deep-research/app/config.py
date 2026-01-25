# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration for the Equity Research Agent."""

import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root
# Try project root first, then app/ directory as fallback
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
if not env_path.exists():
    env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# ==============================================================================
# Model Configuration
# ==============================================================================

# Primary models
MODEL = os.environ.get("MODEL", "gemini-3-flash-preview")  # Main model for all agents
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gemini-3-pro-image-preview")  # Image generation model
CODE_EXEC_MODEL = MODEL  # Code execution model (same as main)

# Model options (commented alternatives)
# Option 1: Gemini 3 Flash (current, faster)
# Option 2: Gemini 3 Pro (more capable for complex tasks)
# STABLE_MODEL = "gemini-3-pro-preview"
# Option 3: Gemini 2.5 Flash (fallback if Gemini 3 unavailable)
# FAST_MODEL = "gemini-2.5-flash"

# ==============================================================================
# Application Configuration
# ==============================================================================

APP_NAME = "equity_research_agent"
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")

# ==============================================================================
# Sandbox Configuration (for code execution)
# ==============================================================================

# Sandbox resource name (REQUIRED for chart generation)
# Create sandbox: python manage_sandbox.py create
# This will output: export SANDBOX_RESOURCE_NAME="projects/.../sandboxes/..."
SANDBOX_RESOURCE_NAME = os.environ.get("SANDBOX_RESOURCE_NAME", "")

# Agent Engine resource name (optional - will auto-create if not set)
AGENT_ENGINE_RESOURCE_NAME = os.environ.get("AGENT_ENGINE_RESOURCE_NAME", "")

# ==============================================================================
# Chart Generation Configuration
# ==============================================================================

# Maximum charts to generate per report
MAX_CHARTS = 10

# Chart resolution
CHART_DPI = 150
CHART_WIDTH = 12  # inches
CHART_HEIGHT = 6  # inches
CHART_STYLE = "ggplot"  # Matplotlib built-in style

# ==============================================================================
# Infographic Configuration
# ==============================================================================

# Infographic count range
MIN_INFOGRAPHICS = 2
MAX_INFOGRAPHICS = 5

# Infographic resolution
INFOGRAPHIC_WIDTH = 1200  # pixels
INFOGRAPHIC_HEIGHT = 800  # pixels

# ==============================================================================
# Report Generation Configuration
# ==============================================================================

# Output file names
HTML_REPORT_FILENAME = "equity_report.html"
CHART_FILENAME_TEMPLATE = "chart_{index}.png"
INFOGRAPHIC_FILENAME_TEMPLATE = "infographic_{index}.png"

# ==============================================================================
# Agent Pipeline Configuration
# ==============================================================================

# Loop agent settings
MAX_CHART_ITERATIONS = 15  # Maximum iterations for chart generation loop

# Parallel agent settings
PARALLEL_DATA_FETCHERS = 4  # Number of concurrent data fetchers

# ==============================================================================
# Retry Configuration
# ==============================================================================

RETRY_ATTEMPTS = 3
RETRY_INITIAL_DELAY = 2  # seconds
RETRY_MAX_DELAY = 10  # seconds

# ==============================================================================
# PDF Export Configuration
# ==============================================================================

# Enable PDF generation alongside HTML report
ENABLE_PDF_EXPORT = os.environ.get("ENABLE_PDF_EXPORT", "true").lower() == "true"

# PDF filename
PDF_REPORT_FILENAME = "equity_report.pdf"

# ==============================================================================
# Batch Chart Generation Configuration (Experimental)
# ==============================================================================

# Enable batch chart generation for ~5-10x speedup
# When enabled: 1 LLM call + 1 sandbox execution (generates ALL charts at once)
# When disabled: N LLM calls + N sandbox executions (one per chart)
ENABLE_BATCH_CHARTS = os.environ.get("ENABLE_BATCH_CHARTS", "false").lower() == "true"

# ==============================================================================
# yfinance Configuration
# ==============================================================================

# Rate limiting for Yahoo Finance API (conservative to avoid throttling)
YFINANCE_MAX_REQUESTS_PER_MINUTE = 30
YFINANCE_MAX_CONCURRENT_REQUESTS = 2

# Cache TTL for yfinance data (in hours)
# Financial data doesn't change frequently, so we cache aggressively
YFINANCE_CACHE_TTL_HOURS = 1

# Maximum retry attempts for yfinance calls
YFINANCE_MAX_RETRIES = 3
YFINANCE_RETRY_BASE_DELAY = 1.0  # seconds

# ==============================================================================
# Logging Configuration
# ==============================================================================

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
