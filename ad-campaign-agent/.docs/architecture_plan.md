# Ad Campaign Agent - Architecture Plan

## Overview

A simple, controlled ADK agent for ad campaign management demo showcasing the end-to-end journey from campaign creation to video ad generation using Veo 3.1.

**Target Users:** Campaign Manager, Creative Director, Store Operations Manager, Director of Retail Media Networks

---

## Demo Journey Flow

```
Campaign Creation → Add Seed Images → Generate Video Ad → Add Mock Metrics →
Analysis & Insights → Trendlines → Show Campaigns on Map
```

---

## Seed Images Analysis

Based on the images in `ad-campaign-agent/selected/`, we have **7 fashion items** that can form **3-4 campaigns**:

| Image | Category | Description | Suggested Campaign |
|-------|----------|-------------|-------------------|
| `dress_summer_dress_004.jpg` | Summer Dress | Floral wrap dress, outdoor/field setting, blonde model | Summer Collection 2025 |
| `dress_formal_dress_002.jpg` | Formal Dress | Red floral fitted gown, studio setting, red-haired model | Evening Elegance |
| `dress_formal_dress_003.jpg` | Formal Dress | Olive strapless bandage dress, nighttime outdoor | Evening Elegance |
| `top_blouse_002.jpg` | Blouse | White classic shirt, sunglasses, urban chic | Urban Professional |
| `top_blouse_003.jpg` | Blouse | Light blue cinched blouse, European city setting | Urban Professional |
| `top_blouse_004.jpg` | Blazer | Beige oversized blazer, minimalist studio | Urban Professional |
| `top_sweater_003.jpg` | Sweater | Beige ribbed turtleneck, glasses, studio | Fall Essentials |

### Suggested Demo Campaigns

1. **Summer Collection 2025** - Dresses for warm weather
2. **Evening Elegance** - Formal wear for special occasions
3. **Urban Professional** - Business casual tops and blazers
4. **Fall Essentials** - Cozy sweaters and layering pieces

---

## Technical Architecture

### Agent Structure (Simple Single-Agent Design)

```
ad-campaign-agent/
├── __init__.py
├── agent.py              # Main LlmAgent with all tools
├── tools/
│   ├── __init__.py
│   ├── campaign_tools.py  # Campaign CRUD operations
│   ├── video_tools.py     # Veo 3.1 video generation
│   ├── metrics_tools.py   # Mock metrics generation
│   └── analysis_tools.py  # Data analysis helpers
├── database/
│   ├── __init__.py
│   ├── models.py          # SQLite models
│   └── mock_data.py       # Initial mock data
├── selected/              # Seed images (existing)
├── generated/             # Generated video ads output
└── .docs/                 # Documentation
```

### Core Components

#### 1. Database Schema (SQLite)

```python
# campaigns table
- id: INTEGER PRIMARY KEY
- name: TEXT
- description: TEXT
- category: TEXT (summer, formal, professional, essentials)
- city: TEXT
- state: TEXT (US states only)
- status: TEXT (draft, active, paused, completed)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

# campaign_images table
- id: INTEGER PRIMARY KEY
- campaign_id: INTEGER FK
- image_path: TEXT
- image_type: TEXT (seed, reference)
- metadata: JSON (model, setting, colors, style)

# campaign_ads table
- id: INTEGER PRIMARY KEY
- campaign_id: INTEGER FK
- video_path: TEXT
- prompt_used: TEXT
- generation_config: JSON
- created_at: TIMESTAMP

# campaign_metrics table (mock data)
- id: INTEGER PRIMARY KEY
- campaign_id: INTEGER FK
- ad_id: INTEGER FK
- date: DATE
- impressions: INTEGER
- views: INTEGER
- clicks: INTEGER
- revenue: DECIMAL
- cost_per_impression: DECIMAL
- engagement_rate: DECIMAL
```

#### 2. Main Agent Definition

```python
from google.adk.agents import LlmAgent
from google.adk.tools import built_in_code_execution
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

root_agent = LlmAgent(
    model='gemini-2.0-flash',
    name='ad_campaign_agent',
    instruction="""You are an Ad Campaign Management Agent for a fashion retail company.

    You help users:
    1. Create and manage ad campaigns with location targeting (US cities/states)
    2. Add seed images to campaigns and analyze their characteristics
    3. Generate video ads using Veo 3.1 based on seed images
    4. View and analyze campaign performance metrics
    5. Create trendlines and data visualizations
    6. Display campaign locations on maps

    Always be concise and focus on actionable insights.
    When generating video ads, create compelling prompts based on image analysis.
    For analysis, use code execution to create charts and trendlines.
    """,
    tools=[
        # Campaign management tools
        create_campaign,
        list_campaigns,
        get_campaign,
        update_campaign,

        # Image management
        add_seed_image,
        analyze_image,
        list_campaign_images,

        # Video generation (Veo 3.1)
        generate_video_ad,
        generate_video_variation,

        # Metrics
        get_campaign_metrics,
        get_top_performing_ads,
        compare_campaigns,

        # Built-in tools
        built_in_code_execution(),  # For data analysis & charts

        # Google Maps MCP
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='npx',
                    args=["-y", "@modelcontextprotocol/server-google-maps"],
                    env={"GOOGLE_MAPS_API_KEY": os.environ.get("GOOGLE_MAPS_API_KEY")}
                ),
            ),
        )
    ],
)
```

---

## Tool Implementations

### 1. Campaign Management Tools

```python
def create_campaign(
    name: str,
    description: str,
    category: str,
    city: str,
    state: str
) -> dict:
    """Create a new ad campaign with location targeting."""
    # Insert into SQLite campaigns table
    # Return campaign details

def list_campaigns(status: str = None) -> list:
    """List all campaigns, optionally filtered by status."""

def get_campaign(campaign_id: int) -> dict:
    """Get detailed campaign info including images and ads."""

def update_campaign(campaign_id: int, **kwargs) -> dict:
    """Update campaign properties."""
```

### 2. Image Management Tools

```python
def add_seed_image(
    campaign_id: int,
    image_path: str,
    metadata: dict = None
) -> dict:
    """Add a seed image to a campaign."""

def analyze_image(image_path: str) -> dict:
    """Analyze image using Gemini to extract:
    - Model characteristics (gender, hair color, etc.)
    - Setting (outdoor, studio, urban, etc.)
    - Clothing details (color, style, pattern)
    - Mood/atmosphere
    Returns structured metadata for video prompt generation.
    """
```

### 3. Video Generation Tools (Veo 3.1)

```python
from google import genai
from google.genai import types

def generate_video_ad(
    campaign_id: int,
    image_id: int = None,
    custom_prompt: str = None,
    duration_seconds: int = 5
) -> dict:
    """Generate a video ad using Veo 3.1.

    If image_id provided, uses that image as reference.
    If custom_prompt provided, uses that; otherwise generates from image analysis.
    """
    client = genai.Client()

    # Get image and its metadata
    image_data = get_campaign_image(image_id)
    image = types.Image.from_file(image_data['path'])

    # Build prompt from metadata or use custom
    if custom_prompt:
        prompt = custom_prompt
    else:
        prompt = generate_video_prompt(image_data['metadata'])

    # Generate video
    operation = client.models.generate_videos(
        model="veo-3.1-generate-preview",
        prompt=prompt,
        image=image,
        config=types.GenerateVideosConfig(
            number_of_videos=1,
            duration_seconds=duration_seconds,
        ),
    )

    # Poll for completion
    while not operation.done:
        time.sleep(10)
        operation = client.operations.get(operation)

    # Save video
    video = operation.response.generated_videos[0]
    output_path = f"generated/campaign_{campaign_id}_ad_{int(time.time())}.mp4"
    video.video.save(output_path)

    # Record in database
    save_campaign_ad(campaign_id, output_path, prompt)

    return {"video_path": output_path, "prompt": prompt}

def generate_video_variation(
    ad_id: int,
    variation_prompt: str = None
) -> dict:
    """Generate a variation of a well-performing ad.

    Uses the original ad's seed image with modified prompt
    to create alternative versions for A/B testing.
    """
```

### 4. Metrics Tools (Mock Data)

```python
def get_campaign_metrics(
    campaign_id: int,
    days: int = 30
) -> dict:
    """Get performance metrics for a campaign.

    Returns mock data including:
    - Daily impressions, views, clicks, revenue
    - Aggregated totals and averages
    - Cost per impression
    """

def get_top_performing_ads(
    metric: str = "revenue",
    limit: int = 5
) -> list:
    """Get top performing ads across all campaigns.

    Identifies key characteristics of successful ads:
    - Model type, setting, music style
    - Common variables in top performers
    """

def compare_campaigns(campaign_ids: list) -> dict:
    """Compare performance metrics across multiple campaigns."""
```

### 5. Prompt Generation Helper

```python
def generate_video_prompt(metadata: dict) -> str:
    """Generate a compelling video prompt from image metadata.

    Example output:
    "A cinematic fashion video featuring a woman with blonde hair
    wearing a flowing floral summer dress. She walks gracefully
    through a sun-drenched meadow, the dress billowing in a gentle
    breeze. Camera slowly pans, capturing the vibrant pink and
    white floral pattern against the golden hour light.
    Atmosphere: dreamy, romantic, aspirational."
    """
```

---

## Mock Data Strategy

### Initial Campaign Data
Pre-populate with 3-4 campaigns using the seed images:

```python
MOCK_CAMPAIGNS = [
    {
        "name": "Summer Blooms 2025",
        "category": "summer",
        "city": "Los Angeles",
        "state": "CA",
        "images": ["dress_summer_dress_004.jpg"],
        "status": "active"
    },
    {
        "name": "Evening Elegance Collection",
        "category": "formal",
        "city": "New York",
        "state": "NY",
        "images": ["dress_formal_dress_002.jpg", "dress_formal_dress_003.jpg"],
        "status": "active"
    },
    {
        "name": "Urban Professional",
        "category": "professional",
        "city": "Chicago",
        "state": "IL",
        "images": ["top_blouse_002.jpg", "top_blouse_003.jpg", "top_blouse_004.jpg"],
        "status": "active"
    },
    {
        "name": "Fall Essentials",
        "category": "essentials",
        "city": "Seattle",
        "state": "WA",
        "images": ["top_sweater_003.jpg"],
        "status": "draft"
    }
]
```

### Mock Metrics Generation

```python
def generate_mock_metrics(campaign_id: int, days: int = 90) -> list:
    """Generate realistic-looking mock metrics.

    - Base impressions: 10,000-50,000/day
    - Views: 20-40% of impressions
    - Clicks: 2-5% of views
    - Revenue: $0.02-0.08 per impression
    - Add random variation and trend lines
    - Top campaigns get better metrics
    """
```

---

## Demo Scenarios

### Scenario 1: Campaign Overview
```
User: "Which campaigns are currently running?"
Agent: Lists active campaigns with summary stats
```

### Scenario 2: Top Performer Analysis
```
User: "Which video/ad is performing the best?"
Agent: "Summer Blooms Campaign #1 is performing best with $0.04 per impression.
        Key characteristics: female model, blonde, outdoor field setting,
        floral pattern, golden hour lighting."
```

### Scenario 3: Video Generation
```
User: "Generate a new ad for the Summer collection using this dress image"
Agent:
1. Analyzes image characteristics
2. Generates compelling prompt
3. Calls Veo 3.1 API
4. Returns video with prompt used
```

### Scenario 4: Variation Generation
```
User: "Generate variations of the top performing ads"
Agent: Creates variations with modified prompts (different setting, mood, etc.)
```

### Scenario 5: Data Analysis
```
User: "Show a trendline for the last 3 campaigns over the last three months"
Agent: Uses code_execution to create matplotlib/plotly chart
```

### Scenario 6: Geographic View
```
User: "Show campaigns on a map"
Agent: Uses Google Maps MCP to display campaign locations with metrics overlay
```

---

## Environment Setup

### Required Environment Variables
```bash
export GOOGLE_API_KEY="your-gemini-api-key"
export GOOGLE_MAPS_API_KEY="your-maps-api-key"
```

### Dependencies
```
google-genai>=1.0.0
google-adk>=1.0.0
sqlite3 (built-in)
Pillow
matplotlib
pandas
```

---

## Testing Strategy

### Local Testing
```bash
# Start API server for testing
adk api_server

# Test individual endpoints
curl -X POST http://localhost:8000/...
```

### ADK Web Testing
```bash
# Start web UI
adk web --port 8000

# Open browser to http://localhost:8000
# Interact with agent through chat interface
```

---

## Implementation Priority

### Phase 1: Core Infrastructure
1. SQLite database setup with models
2. Campaign CRUD tools
3. Mock data population
4. Basic agent with campaign tools

### Phase 2: Image & Video
1. Image analysis tool (using Gemini)
2. Prompt generation helper
3. Veo 3.1 video generation integration
4. Video variation generation

### Phase 3: Analytics
1. Mock metrics generation
2. Metrics query tools
3. Code execution for charts/trendlines
4. Top performer analysis

### Phase 4: Visualization
1. Google Maps MCP integration
2. Campaign location display
3. Final demo polish

---

## Key Design Decisions

1. **Single Agent Architecture**: Keep it simple with one LlmAgent and function tools (no sub-agents needed for demo scope)

2. **SQLite for Persistence**: Lightweight, no external dependencies, perfect for demo

3. **AI Studio Gemini API**: Prioritize AI Studio over Vertex AI for simpler setup

4. **Mock Metrics**: Generate realistic-looking data rather than real tracking

5. **Code Execution for Analysis**: Use built-in ADK tool for charts rather than custom visualization tools

6. **MCP for Maps**: Leverage existing Google Maps MCP server rather than building custom integration

---

## Sources

- [ADK Documentation](https://google.github.io/adk-docs)
- [Veo 3.1 Video Generation API](https://ai.google.dev/gemini-api/docs/video)
- [Google Gen AI Python SDK](https://github.com/googleapis/python-genai)
- [ADK Code Execution Tool](https://google.github.io/adk-docs/tools/built-in-tools)
- [ADK MCP Tools](https://google.github.io/adk-docs/tools/mcp-tools)
