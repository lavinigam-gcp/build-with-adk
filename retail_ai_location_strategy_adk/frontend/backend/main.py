# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""FastAPI server wrapping ADK agent with AG-UI middleware.

This server provides an AG-UI compatible endpoint that wraps the existing
LocationStrategyPipeline agent without modifying any core agent files.

Usage:
    cd frontend/backend
    pip install -r requirements.txt
    python main.py

    # Or with uv:
    uv pip install -r requirements.txt
    uv run python main.py
"""

import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent directories to path for imports
# This allows importing from retail_ai_location_strategy_adk
# Structure: build-with-adk/retail_ai_location_strategy_adk/frontend/backend/main.py
# We need to add build-with-adk/ to the path
agent_package_dir = Path(__file__).parent.parent.parent  # retail_ai_location_strategy_adk/
workspace_dir = agent_package_dir.parent  # build-with-adk/
sys.path.insert(0, str(workspace_dir))

# Load environment variables from the main project .env
env_path = agent_package_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Import AG-UI middleware (CopilotKit official package)
from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint

# Import the EXISTING root_agent - no modifications needed
from retail_ai_location_strategy_adk.agent import root_agent

# Create AG-UI wrapper around the existing ADK agent
# Increase timeout for Strategy Synthesis which uses extended thinking
adk_agent = ADKAgent(
    adk_agent=root_agent,
    app_name="retail_location_strategy",
    user_id="demo_user",
    execution_timeout_seconds=1800,  # 30 minutes for full pipeline
    tool_timeout_seconds=600,  # 10 minutes for individual tools
)

# Create FastAPI app
app = FastAPI(
    title="Retail Location Strategy API",
    description="AG-UI compatible API for the Retail AI Location Strategy agent",
    version="1.0.0",
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "LocationStrategyPipeline"}


# Add AG-UI endpoint at root path
# This handles all AG-UI protocol communication
add_adk_fastapi_endpoint(app, adk_agent, path="/")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting AG-UI server at http://0.0.0.0:{port}")
    print("Frontend should connect to this URL")
    uvicorn.run(app, host="0.0.0.0", port=port)
