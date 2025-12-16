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

"""Configuration for the Ad Campaign Agent."""

import os

# Model configuration
MODEL = "gemini-3-pro-preview" #gemini-2.5-flash #gemini-3-pro-preview #gemini-2.5-pro 

# API Keys (loaded from environment)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
# Support both GOOGLE_MAPS_API_KEY and MAPS_API_KEY (from .env)
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("MAPS_API_KEY")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
SELECTED_DIR = os.path.join(PROJECT_DIR, "selected")
GENERATED_DIR = os.path.join(PROJECT_DIR, "generated")
DB_PATH = os.path.join(PROJECT_DIR, "campaigns.db")

# App metadata
APP_NAME = "ad_campaign_agent"
APP_DESCRIPTION = "Fashion retail ad campaign management agent with video generation"

# Campaign categories
CAMPAIGN_CATEGORIES = ["summer", "formal", "professional", "essentials"]

# Campaign statuses
CAMPAIGN_STATUSES = ["draft", "active", "paused", "completed"]
