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

"""Configuration for Retail AI Location Strategy ADK Agent.

This agent uses Google AI Studio (API key authentication) instead of Vertex AI.
Set the following environment variables in your .env file:

    GOOGLE_API_KEY=your_google_api_key
    GOOGLE_GENAI_USE_VERTEXAI=FALSE
    MAPS_API_KEY=your_maps_api_key
"""

import os

# API Keys
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
MAPS_API_KEY = os.environ.get("MAPS_API_KEY", "")

# Model Configuration
# ============================================================================
# Uncomment the model set you want to use. Only one set should be active.
# ============================================================================

# Option 1: Gemini 3 Pro Preview (latest, may have availability issues)
# FAST_MODEL = "gemini-3-pro-preview"
# PRO_MODEL = "gemini-3-pro-preview"
# CODE_EXEC_MODEL = "gemini-2.5-pro"  # Code execution requires 2.5-pro or higher
IMAGE_MODEL = "gemini-3-pro-image-preview"

# Option 2: Gemini 2.5 Pro (stable, good for production)
FAST_MODEL = "gemini-2.5-pro"
PRO_MODEL = "gemini-2.5-pro"
CODE_EXEC_MODEL = "gemini-2.5-pro"
# IMAGE_MODEL = "gemini-2.0-flash-exp"  # 2.5 doesn't have native image gen

# Option 3: Gemini 2.5 Flash (fastest, lowest cost)
# FAST_MODEL = "gemini-2.5-flash"
# PRO_MODEL = "gemini-2.5-flash"
# CODE_EXEC_MODEL = "gemini-2.5-flash"
# IMAGE_MODEL = "gemini-2.0-flash-exp"  # Flash image generation

# Retry Configuration (for handling model overload errors)
# Note: HttpRetryOptions may only retry on certain HTTP codes (429, etc.)
# For persistent 503 errors, consider using a different model or waiting for API availability
RETRY_INITIAL_DELAY = 5  # seconds - longer wait for overloaded models
RETRY_ATTEMPTS = 5  # More attempts for transient errors
RETRY_MAX_DELAY = 60  # seconds

# App Configuration
APP_NAME = "retail_location_strategy"
