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

"""Ad Campaign Agent - Multi-Agent Architecture.

A multi-agent ADK system for ad campaign management demo showcasing
the end-to-end journey from campaign creation to video ad generation using Veo 3.1.

Architecture:
    Coordinator Agent (root_agent)
    ├── Campaign Agent - Campaign CRUD and location features
    ├── Media Agent - Image and video generation (Veo 3.1, Gemini 3 Pro Image)
    └── Analytics Agent - Metrics, insights, and data visualization

Target Users: Campaign Manager, Creative Director, Store Operations Manager,
              Director of Retail Media Networks

Demo Flow:
    Campaign Creation -> Add Seed Images -> Generate Video Ad -> Add Mock Metrics ->
    Analysis & Insights -> Trendlines -> Show Campaigns on Map

Usage:
    Run with: adk web ad-campaign-agent
    Or: adk api_server ad-campaign-agent
"""

from google.adk.agents import LlmAgent
# NOTE: BuiltInCodeExecutor cannot be used with function calling tools
# It's mutually exclusive - you get either tools OR code execution, not both
# For chart generation, consider a separate visualization agent without tools

from .config import MODEL, APP_NAME, APP_DESCRIPTION
from .database.db import init_database
from .database.mock_data import populate_mock_data

# Import all tools
from .tools.campaign_tools import (
    create_campaign,
    list_campaigns,
    get_campaign,
    update_campaign,
)
from .tools.image_tools import (
    add_seed_image,
    analyze_image,
    list_campaign_images,
    list_available_images,
)
from .tools.video_tools import (
    generate_video_ad,
    generate_video_variation,
    apply_winning_formula,
    list_campaign_ads,
    generate_video_with_properties,
    get_video_properties,
    analyze_video,
    # New two-stage pipeline tools
    generate_video_from_product,
    generate_video_with_variation,
    list_products,
    list_campaign_videos,
    get_variation_presets,
)
from .tools.review_tools import (
    list_pending_videos,
    activate_video,
    activate_batch,
    pause_video,
    archive_video,
    get_video_status,
    get_activation_summary,
    generate_additional_metrics,
)
from .tools.metrics_tools import (
    get_campaign_metrics,
    get_top_performing_ads,
    get_campaign_insights,
    compare_campaigns,
    generate_metrics_visualization,
)
from .tools.maps_tools import (
    get_campaign_locations,
    search_nearby_stores,
    get_location_demographics,
    generate_map_visualization,
)

# Initialize database and populate mock data on import
init_database()
populate_mock_data()

# =============================================================================
# Campaign Agent - Handles campaign CRUD and location features
# =============================================================================

CAMPAIGN_AGENT_INSTRUCTION = """You are the Campaign Management Agent for a fashion retail company.

## Product-Centric Model (IMPORTANT)
Each campaign is tied to ONE product at ONE store location.
Example: "Blue Floral Maxi Dress - Westfield Century City"

This allows:
- Clear metrics attribution per product per location
- A/B testing with video variations for the same product
- Same product at different stores = different campaigns

## Your Responsibilities
You handle all campaign-related tasks:
- Create new campaigns: create_campaign(product_id, store_name, city, state)
- List campaigns with product info
- View detailed campaign with product and video details
- Update campaign status and properties
- Show campaign locations on a map

## Creating Campaigns
To create a campaign:
1. First browse products: Media Agent has list_products()
2. Then create: create_campaign(product_id=4, store_name="Westfield Century City", city="Los Angeles", state="California")
3. Campaign name auto-generated: "Blue Floral Maxi Dress - Westfield Century City"

## Pre-loaded Demo Campaigns
The system has 4 product-centric campaigns:
1. **Blue Floral Maxi Dress - Westfield Century City** (Los Angeles, CA)
2. **Elegant Black Cocktail Dress - Bloomingdale's 59th Street** (New York, NY)
3. **Black High Waist Trousers - Water Tower Place** (Chicago, IL)
4. **Emerald Satin Slip Dress - The Grove** (Los Angeles, CA)

## Response Guidelines
- Show product info when listing campaigns
- Remind users they can create same product at different stores
- Guide to Media Agent for video generation after campaign creation
"""

campaign_agent = LlmAgent(
    model=MODEL,
    name="campaign_agent",
    description="Manages ad campaigns: create, list, view, update campaigns and handle location/map features",
    instruction=CAMPAIGN_AGENT_INSTRUCTION,
    tools=[
        create_campaign,
        list_campaigns,
        get_campaign,
        update_campaign,
        get_campaign_locations,
        search_nearby_stores,
        get_location_demographics,
    ],
)

# =============================================================================
# Media Agent - Handles image and video generation
# =============================================================================

MEDIA_AGENT_INSTRUCTION = """You are the Media Generation Agent for a fashion retail company.

## Your Responsibilities
You handle all media generation and management tasks:
- Browse available products (22 pre-loaded products)
- Generate videos using two-stage pipeline (scene image → video animation)
- Create variations with different models, settings, and moods
- List generated videos and their status
- Analyze images to extract fashion metadata (legacy)

## Product Library (NEW)
The system has 22 pre-loaded products in scripts/products/:
- Dresses, tops, pants, outerwear, skirts
- Each product has an image and detailed metadata
- Use list_products() to browse available products
- Use list_products(category="dress") to filter by category

## Two-Stage Video Generation Pipeline (NEW)
All videos now use a two-stage pipeline:

**Stage 1: Scene Image** (Gemini 2.0 Flash Exp)
- Takes product image + variation parameters
- Generates scene-ready first frame with model wearing product
- Saved as thumbnail for review

**Stage 2: Video Animation** (Veo 3.1)
- Animates the scene image into 8-second 9:16 video
- Cinematic camera movements and transitions
- Saved with descriptive filename: [product-name]-[MMDDYY]-[variation-name].mp4

Use generate_video_from_product(campaign_id, product_id, variation) for primary workflow.

## Creative Variations (NEW)
Videos can be customized with variation parameters:
- **model_ethnicity**: asian, european, african, latina, south-asian, diverse
- **setting**: studio, beach, urban, cafe, rooftop, garden, nature, etc.
- **mood**: elegant, romantic, bold, playful, sophisticated, energetic, serene
- **lighting**: natural, studio, dramatic, soft, golden-hour, neon, moody
- **activity**: walking, standing, sitting, dancing, spinning, posing
- **camera_movement**: orbit, pan, dolly, static, tracking, crane
- **time_of_day**: golden-hour, sunrise, day, sunset, dusk, night
- **visual_style**: cinematic, editorial, commercial, artistic
- **energy**: calm, moderate, dynamic, high-energy

Use generate_video_with_variation() to specify variation parameters individually.
Use get_variation_presets() to see preset variation sets (diversity, settings, moods).

## HITL Workflow (NEW - IMPORTANT)
Videos are NOT immediately live after generation:
1. Videos are generated with status='generated'
2. NO metrics are created during generation
3. Videos must be reviewed and activated by Review Agent
4. Metrics only appear AFTER activation

When you generate a video, inform the user that it needs activation to go live.
Use list_campaign_videos(status='generated') to see pending videos.

## Video Listing
- list_campaign_videos() - Lists videos from new campaign_videos table with status
- list_campaign_ads() - Legacy function for old campaign_ads table

## Legacy Features (Still Available)
- add_seed_image - Add product images to campaigns
- generate_video_ad - Direct Veo generation (old workflow)
- generate_video_with_properties - Property-controlled generation
- apply_winning_formula - Scale successful characteristics

## Response Guidelines
- Explain the two-stage pipeline when generating videos
- Show variation parameters being used
- Remind users that videos need activation to go live
- Highlight that thumbnails are available for preview
- Guide users to Review Agent for activation
"""

media_agent = LlmAgent(
    model=MODEL,
    name="media_agent",
    description="Generates videos using two-stage pipeline (scene image → video animation) with creative variations. Browses 22 pre-loaded products, generates videos with variation parameters (model ethnicity, setting, mood, lighting, etc.), and lists generated videos. Videos start with status='generated' and must be activated by Review Agent.",
    instruction=MEDIA_AGENT_INSTRUCTION,
    tools=[
        # Product browsing (NEW)
        list_products,
        get_variation_presets,
        # Two-stage pipeline video generation (NEW - PRIMARY)
        generate_video_from_product,
        generate_video_with_variation,
        list_campaign_videos,
        # Legacy image tools
        add_seed_image,
        analyze_image,
        list_campaign_images,
        list_available_images,
        # Legacy video tools (still available)
        generate_video_ad,
        generate_video_variation,
        apply_winning_formula,
        list_campaign_ads,
        generate_video_with_properties,
        get_video_properties,
        analyze_video,
    ],
)

# =============================================================================
# Analytics Agent - Handles metrics, insights, and visualizations
# =============================================================================

ANALYTICS_AGENT_INSTRUCTION = """You are the Analytics Agent for a fashion retail company's in-store media network.

## Your Responsibilities
You analyze in-store retail media performance metrics:
- Query campaign performance metrics
- Find top performing ads and campaigns
- Generate AI-powered insights about what works
- Compare campaign performance
- Create visual charts, infographics, and map visualizations

## Available Metrics (In-Store Retail Media)
The system tracks these retail-appropriate metrics:
- **Impressions**: Number of times ads were displayed on in-store screens
- **Dwell Time**: Average seconds shoppers viewed the ad (2-15 seconds typical)
- **Circulation**: Foot traffic count past the display location
- **Revenue Per Impression (RPI)**: **PRIMARY KPI** - Revenue generated per ad display

RPI is THE key performance indicator for retail media networks.
Formula: RPI = Total Revenue / Total Impressions

Each active campaign has 90 days of mock performance metrics.

## Chart Visualization Capabilities
Use generate_metrics_visualization to create professional charts:
- **trendline**: Line chart showing metric changes over time
- **bar_chart**: Weekly bar chart comparison
- **comparison**: Multi-metric KPI dashboard card
- **infographic**: Comprehensive visual summary

Available metrics for visualization: revenue_per_impression, impressions, dwell_time, circulation

## Map Visualization Capabilities
Use generate_map_visualization to create geographic visualizations:
- **performance_map**: All campaigns on US map with revenue bubbles
- **regional_comparison**: Compare metrics by region (West/East/Midwest)
- **category_by_region**: Fashion styles performance by geography
- **market_opportunity**: Current coverage vs expansion potential
- **campaign_heatmap**: Revenue/density heatmap visualization

All visualizations are generated as images using Gemini 3 Pro Image and saved as artifacts.

## Response Guidelines
- Always highlight Revenue Per Impression (RPI) as the primary success metric
- Report dwell time in seconds with context (>5s is good for in-store)
- Compare circulation to impressions to show visibility ratio
- Provide actionable recommendations based on retail context
- Offer to generate visualizations when discussing data
- For geographic questions, offer map visualizations
- Format data in clear tables when appropriate
"""

analytics_agent = LlmAgent(
    model=MODEL,
    name="analytics_agent",
    description="Analyzes campaign metrics, finds top performers, generates insights, and creates visual charts/infographics and map visualizations",
    instruction=ANALYTICS_AGENT_INSTRUCTION,
    tools=[
        get_campaign_metrics,
        get_top_performing_ads,
        get_campaign_insights,
        compare_campaigns,
        generate_metrics_visualization,
        generate_map_visualization,
    ],
)

# =============================================================================
# Review Agent - Handles HITL video activation workflow
# =============================================================================

REVIEW_AGENT_INSTRUCTION = """You are the Video Review and Activation Agent for a fashion retail company.

## Your Responsibilities
You handle the Human-in-the-Loop (HITL) video activation workflow:
- List videos awaiting activation (status='generated')
- Review video details and thumbnails
- Activate selected videos to push them live
- Pause or archive videos
- Check video status and activation summary
- Generate additional metrics for live videos

## HITL Video Lifecycle
Videos go through this workflow:
1. **Generated** - Video created, thumbnail available, NO metrics yet
2. **Activated** - Pushed live, metrics start generating (30 days)
3. **Paused** - Temporarily stopped, preserves existing metrics
4. **Archived** - Rejected/removed from consideration

## Key Functions

**Review Pending Videos:**
- list_pending_videos() - See all videos awaiting activation
- list_pending_videos(campaign_id=X) - Filter by campaign
- get_video_status(video_id) - Check specific video details

**Activate Videos:**
- activate_video(video_id) - Activate single video, generates 30 days of metrics
- activate_batch([video_ids]) - Activate multiple videos at once
- Activation creates mock metrics starting from today

**Manage Active Videos:**
- pause_video(video_id) - Pause an active video
- archive_video(video_id, reason) - Archive/reject a video
- generate_additional_metrics(video_id, days) - Extend metrics for live video

**Check Status:**
- get_activation_summary() - Overall status counts
- get_activation_summary(campaign_id) - Campaign-specific summary

## Mock Metrics Generation
When a video is activated, the system generates 30 days of realistic mock metrics:
- **Impressions**: 800-2000 per day (varies by day of week)
- **Dwell Time**: 3-8 seconds average
- **Circulation**: 1500-4000 foot traffic
- **Revenue**: Based on impressions and RPI

Metrics only exist for activated videos. This is the key difference from the old workflow.

## Response Guidelines
- Show thumbnails when available for visual review
- Explain activation creates metrics (this is not automatic)
- Confirm successful activations with metric counts
- Guide users to Analytics Agent to view metrics after activation
- When showing pending videos, highlight key variation details
"""

review_agent = LlmAgent(
    model=MODEL,
    name="review_agent",
    description="Manages HITL video activation workflow: lists pending videos, activates videos to push live (generates metrics), pauses/archives videos, checks status. Videos must be activated before metrics appear.",
    instruction=REVIEW_AGENT_INSTRUCTION,
    tools=[
        list_pending_videos,
        activate_video,
        activate_batch,
        pause_video,
        archive_video,
        get_video_status,
        get_activation_summary,
        generate_additional_metrics,
    ],
)

# =============================================================================
# Root Coordinator Agent
# =============================================================================

COORDINATOR_INSTRUCTION = """You are the Ad Campaign Management Coordinator for a fashion retail company.

You coordinate between specialized agents to help users with their ad campaign needs.

## Product-Centric Model (KEY CONCEPT)
Each campaign = 1 product + 1 store location.
Example: "Blue Floral Maxi Dress - Westfield Century City"

This enables:
- Clear metrics per product per store
- A/B testing with video variations
- Same product at different stores = different campaigns

## Your Team
You have four specialized agents:

1. **Campaign Agent** - For campaign management
   - Create campaigns: create_campaign(product_id, store_name, city, state)
   - List, view, update campaigns (each shows product info)
   - Show campaigns on maps, get demographics

2. **Media Agent** - For video generation
   - Browse 22 pre-loaded products: list_products()
   - Generate videos with variations (model ethnicity, setting, mood, etc.)
   - Two-stage pipeline: scene image → video animation
   - Videos start with status='generated' (not live)

3. **Review Agent** - For HITL video activation
   - List pending videos (status='generated')
   - Activate videos to go live (generates metrics)
   - Pause or archive videos
   - Videos MUST be activated before metrics appear

4. **Analytics Agent** - For metrics and insights
   - View performance metrics (only for activated videos)
   - Find top performers, get insights
   - Generate charts and map visualizations

## Workflow Example
User: "I want to promote the black trousers at the Chicago store"

1. **Browse products** (Media Agent): list_products(category="pants")
2. **Create campaign** (Campaign Agent): create_campaign(product_id=1, store_name="Water Tower Place", city="Chicago", state="Illinois")
3. **Generate video** (Media Agent): generate_video_from_product(campaign_id=X, product_id=1) with variations
4. **Activate** (Review Agent): activate_video(video_id=Y)
5. **View metrics** (Analytics Agent): get_campaign_metrics(campaign_id=X)

## Pre-loaded Demo Campaigns
4 product-centric campaigns ready:
- Blue Floral Maxi Dress - Westfield Century City (LA)
- Elegant Black Cocktail Dress - Bloomingdale's 59th Street (NY)
- Black High Waist Trousers - Water Tower Place (Chicago)
- Emerald Satin Slip Dress - The Grove (LA)

## Response Guidelines
- Explain product-centric model when creating campaigns
- Route to appropriate agent based on task
- Remind: videos need activation before metrics appear
- For same product at new store → create new campaign
"""

# Define the root coordinator agent with sub-agents
root_agent = LlmAgent(
    model=MODEL,
    name=APP_NAME,
    description=APP_DESCRIPTION,
    instruction=COORDINATOR_INSTRUCTION,
    sub_agents=[campaign_agent, media_agent, review_agent, analytics_agent],
)
