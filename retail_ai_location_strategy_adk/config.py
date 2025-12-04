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
FAST_MODEL = "gemini-3-pro-preview"
PRO_MODEL = "gemini-3-pro-preview"
IMAGE_MODEL = "gemini-3-pro-image-preview"

# App Configuration
APP_NAME = "retail_location_strategy"
