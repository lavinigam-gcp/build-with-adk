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
# Agent models
# NOTE: Using models available in us-central1 for Agent Engine compatibility
MODEL = "gemini-2.5-pro"  # Main agent model

# Media generation models
IMAGE_GENERATION = "gemini-2.5-flash-image"  # For scene image generation (Stage 1)
VEO_MODEL = "veo-3.1-generate-preview"  # For video animation (Stage 2)

# Video configuration
VIDEO_ASPECT_RATIO = "9:16"  # Vertical format for retail displays
VIDEO_DURATION_SECONDS = 8  # Default video duration (4, 6, or 8 for Veo 3.1)
# API Keys (loaded from environment)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
# Support both GOOGLE_MAPS_API_KEY and MAPS_API_KEY (from .env)
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("MAPS_API_KEY")

# Cloud Run detection
IS_CLOUD_RUN = os.environ.get("K_SERVICE") is not None

# Agent Engine detection (set by Vertex AI Agent Engine runtime)
IS_AGENT_ENGINE = os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID") is not None

# Combined: running in any managed cloud environment
IS_CLOUD_ENVIRONMENT = IS_CLOUD_RUN or IS_AGENT_ENGINE

# GCS configuration - Always use GCS for storage (local and cloud)
# This ensures consistent behavior between local development and Cloud Run
DEFAULT_GCS_BUCKET = "kaggle-on-gcp-ad-campaign-assets"
GCS_BUCKET = os.environ.get("GCS_BUCKET", DEFAULT_GCS_BUCKET)

# GCS paths for assets
GCS_PRODUCT_IMAGES_PREFIX = "product-images/"  # Renamed from seed-images per feedback
GCS_SEED_IMAGES_PREFIX = "seed-images/"  # Legacy, deprecated
GCS_GENERATED_PREFIX = "generated/"

# Paths (kept for backwards compatibility, but GCS is primary storage)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

# Local directories (fallback only if GCS_BUCKET is explicitly set to empty string)
SELECTED_DIR = os.path.join(PROJECT_DIR, "selected")
GENERATED_DIR = os.path.join(PROJECT_DIR, "generated")

# Database path
# - Local development: Use project root (persistent across runs)
# - Cloud Run: Use app directory (ephemeral, mock data repopulates on each container start)
# - Agent Engine: Use /tmp (ephemeral, writable in managed container)
if IS_AGENT_ENGINE:
    # Agent Engine: /tmp is guaranteed writable in the managed container
    # Database is ephemeral - mock data repopulates on each instance
    DB_PATH = "/tmp/campaigns.db"
elif IS_CLOUD_RUN:
    # In Cloud Run, the container has the app/ folder as working context
    # Use a path inside the deployed directory
    DB_PATH = os.path.join(BASE_DIR, "campaigns.db")
else:
    # Local development: use project root for persistence
    DB_PATH = os.path.join(PROJECT_DIR, "campaigns.db")

# App metadata
APP_NAME = "ad_campaign_agent"
APP_DESCRIPTION = "Fashion retail ad campaign management agent with video generation"

# Campaign categories
CAMPAIGN_CATEGORIES = ["summer", "formal", "professional", "essentials"]

# Campaign statuses
CAMPAIGN_STATUSES = ["draft", "active", "paused", "completed"]
