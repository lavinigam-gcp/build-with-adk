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
    generate_seed_image,
)
from .tools.video_tools import (
    generate_video_ad,
    generate_video_variation,
    apply_winning_formula,
    list_campaign_ads,
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

## Your Responsibilities
You handle all campaign-related tasks:
- Create new ad campaigns with US location targeting (city, state)
- List and search existing campaigns
- View detailed campaign information
- Update campaign status and properties
- Show campaign locations on a map
- Search for nearby stores and get location demographics

## Pre-loaded Demo Campaigns
The system has 4 pre-loaded campaigns:
1. **Summer Blooms 2025** (Los Angeles, CA) - Summer dresses
2. **Evening Elegance Collection** (New York, NY) - Formal wear
3. **Urban Professional** (Chicago, IL) - Business casual
4. **Fall Essentials** (Seattle, WA) - Cozy knits (draft)

## Response Guidelines
- Be concise and provide clear campaign details
- When listing campaigns, include status and location
- Use geographic tools for map and location requests
- Always confirm successful operations
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
- Generate seed images using Gemini 3 Pro Image (Nano Banana)
- Add existing seed images to campaigns
- Analyze images to extract fashion metadata
- Generate video ads using Veo 3.1
- Create video variations for A/B testing
- List campaign images and ads

## Available Seed Images
Existing images in the `selected/` folder:
- `dress_summer_dress_004.jpg` - Floral wrap dress, outdoor field setting
- `dress_formal_dress_002.jpg` - Red floral fitted gown, studio
- `dress_formal_dress_003.jpg` - Olive strapless bandage dress, nighttime outdoor
- `top_blouse_002.jpg` - White classic shirt, urban setting
- `top_blouse_003.jpg` - Light blue cinched blouse, European city
- `top_blouse_004.jpg` - Beige oversized blazer, minimalist studio
- `top_sweater_003.jpg` - Beige ribbed turtleneck, studio

## Video Generation Tips
- Veo 3.1 creates cinematic fashion videos from seed images
- Videos can be 5 or 8 seconds long
- The prompt is auto-generated from image analysis metadata
- You can also provide custom prompts for specific effects
- Generated videos are saved as ADK artifacts

## Applying Winning Formulas
Use apply_winning_formula to scale what's working:
- Takes characteristics (mood, setting, camera_style) from top-performing ads
- Applies them to generate new videos for other campaigns
- Can auto-select the top performer or use a specific ad
- Preserves successful elements while using new campaign's clothing/imagery

## Image Generation Tips
- Use generate_seed_image to create new fashion images with AI
- Images are automatically analyzed for metadata
- Generated images are saved locally and as ADK artifacts

## Response Guidelines
- Explain the prompt being used for video generation
- Describe generated media in detail
- Highlight key characteristics of images and videos
- Provide status updates for long-running operations
"""

media_agent = LlmAgent(
    model=MODEL,
    name="media_agent",
    description="Generates and manages images and videos: creates seed images with Gemini 3 Pro, generates video ads with Veo 3.1, analyzes images, creates variations, applies winning formulas from top performers",
    instruction=MEDIA_AGENT_INSTRUCTION,
    tools=[
        generate_seed_image,
        add_seed_image,
        analyze_image,
        list_campaign_images,
        list_available_images,
        generate_video_ad,
        generate_video_variation,
        apply_winning_formula,
        list_campaign_ads,
    ],
)

# =============================================================================
# Analytics Agent - Handles metrics, insights, and visualizations
# =============================================================================

ANALYTICS_AGENT_INSTRUCTION = """You are the Analytics Agent for a fashion retail company.

## Your Responsibilities
You handle all analytics and insights tasks:
- Query campaign performance metrics (impressions, views, clicks, revenue)
- Find top performing ads and campaigns
- Generate AI-powered insights about what works
- Compare campaign performance
- Create visual charts, infographics, and map visualizations using AI image generation

## Available Metrics
The system tracks:
- **Impressions**: Number of times ads were shown
- **Views**: Number of video views (3+ seconds)
- **Clicks**: Click-through to product pages
- **Revenue**: Attributed revenue from ad engagement

Each active campaign has 90 days of mock performance metrics.

## Chart Visualization Capabilities
Use generate_metrics_visualization to create professional charts:
- **trendline**: Line chart showing metric changes over time
- **bar_chart**: Weekly bar chart comparison
- **comparison**: Multi-metric KPI dashboard card
- **infographic**: Comprehensive visual summary

## Map Visualization Capabilities
Use generate_map_visualization to create geographic visualizations:
- **performance_map**: All campaigns on US map with revenue bubbles
- **regional_comparison**: Compare metrics by region (West/East/Midwest)
- **category_by_region**: Fashion styles performance by geography
- **market_opportunity**: Current coverage vs expansion potential
- **campaign_heatmap**: Revenue/density heatmap visualization

All visualizations are generated as images using Gemini 3 Pro Image and saved as artifacts.

## Response Guidelines
- Summarize key metrics with actual numbers
- Highlight trends and patterns
- Identify characteristics of top performers
- Provide actionable recommendations
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
# Root Coordinator Agent
# =============================================================================

COORDINATOR_INSTRUCTION = """You are the Ad Campaign Management Coordinator for a fashion retail company.

You coordinate between specialized agents to help users with their ad campaign needs.

## Your Team
You have three specialized agents:

1. **Campaign Agent** - For campaign management and locations
   - Create, list, view, update campaigns
   - Show campaigns on maps
   - Search nearby stores, get demographics

2. **Media Agent** - For image and video generation
   - Generate seed images with AI (Gemini 3 Pro Image)
   - Generate video ads with Veo 3.1
   - Analyze images, add seed images to campaigns
   - Create video variations for A/B testing
   - Apply winning formulas from top performers to other campaigns

3. **Analytics Agent** - For metrics and insights
   - View campaign performance metrics
   - Find top performing ads
   - Get AI-powered insights
   - Compare campaign performance
   - Generate visual charts and infographics
   - Create map visualizations (performance maps, regional comparisons, heatmaps)

## When to Delegate
- Campaign questions (list, create, update, locations) → Campaign Agent
- Media generation (images, videos, analysis) → Media Agent
- Metrics and analysis (performance, insights, charts) → Analytics Agent

## Demo Flow
When users want a full demo, guide them through:
1. List campaigns (Campaign Agent)
2. Show campaign details and images (Campaign Agent + Media Agent)
3. Generate a video ad (Media Agent)
4. View performance metrics (Analytics Agent)
5. Get insights and top performers (Analytics Agent)
6. Compare campaigns (Analytics Agent)
7. Show campaigns on a map (Campaign Agent)

## Response Guidelines
- Route requests to the appropriate specialized agent
- Provide brief context before delegating
- Summarize results from agents
- Guide users through the demo flow if asked
"""

# Define the root coordinator agent with sub-agents
root_agent = LlmAgent(
    model=MODEL,
    name=APP_NAME,
    description=APP_DESCRIPTION,
    instruction=COORDINATOR_INSTRUCTION,
    sub_agents=[campaign_agent, media_agent, analytics_agent],
)
