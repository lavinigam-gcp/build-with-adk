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

"""Google Maps tools for campaign location visualization."""

import json
import os
import time
from typing import Optional

from google import genai
from google.genai import types
from google.adk.tools import ToolContext

from ..config import GOOGLE_MAPS_API_KEY
from ..database.db import get_db_cursor


def get_campaign_locations() -> dict:
    """Get geographic locations of all campaigns for map display.

    Geocodes campaign city/state to coordinates and includes metrics summary
    for map visualization.

    Returns:
        Dictionary with campaign locations and coordinates
    """
    try:
        import googlemaps
    except ImportError:
        return {
            "status": "error",
            "message": "googlemaps package not installed. Run: pip install googlemaps"
        }

    api_key = GOOGLE_MAPS_API_KEY
    if not api_key:
        return {
            "status": "error",
            "message": "GOOGLE_MAPS_API_KEY environment variable not set"
        }

    gmaps = googlemaps.Client(key=api_key)

    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT
                c.id,
                c.name,
                c.category,
                c.city,
                c.state,
                c.status,
                COUNT(DISTINCT ca.id) as ad_count,
                SUM(cm.revenue) as total_revenue,
                SUM(cm.impressions) as total_impressions
            FROM campaigns c
            LEFT JOIN campaign_ads ca ON c.id = ca.campaign_id
            LEFT JOIN campaign_metrics cm ON c.id = cm.campaign_id
            GROUP BY c.id
        ''')

        campaigns = cursor.fetchall()

    locations = []
    geocode_cache = {}

    for campaign in campaigns:
        location_key = f"{campaign['city']}, {campaign['state']}"

        # Use cache to avoid duplicate geocoding
        if location_key not in geocode_cache:
            try:
                geocode_result = gmaps.geocode(location_key)
                if geocode_result:
                    lat = geocode_result[0]['geometry']['location']['lat']
                    lng = geocode_result[0]['geometry']['location']['lng']
                    geocode_cache[location_key] = {"lat": lat, "lng": lng}
                else:
                    geocode_cache[location_key] = None
            except Exception as e:
                geocode_cache[location_key] = None

        coords = geocode_cache.get(location_key)

        locations.append({
            "campaign_id": campaign["id"],
            "name": campaign["name"],
            "category": campaign["category"],
            "status": campaign["status"],
            "location": {
                "city": campaign["city"],
                "state": campaign["state"],
                "coordinates": coords
            },
            "metrics": {
                "ad_count": campaign["ad_count"] or 0,
                "total_revenue": round(campaign["total_revenue"], 2) if campaign["total_revenue"] else 0,
                "total_impressions": int(campaign["total_impressions"]) if campaign["total_impressions"] else 0
            }
        })

    # Generate Google Maps URL for visualization
    if locations:
        # Create a simple map URL centered on US
        map_center = "39.8283,-98.5795"  # Center of US
        markers = []
        for loc in locations:
            if loc["location"]["coordinates"]:
                lat = loc["location"]["coordinates"]["lat"]
                lng = loc["location"]["coordinates"]["lng"]
                markers.append(f"markers=color:red%7Clabel:{loc['name'][0]}%7C{lat},{lng}")

        map_url = f"https://www.google.com/maps/dir/?api=1&origin={map_center}&destination={map_center}"
    else:
        map_url = None

    return {
        "status": "success",
        "campaign_count": len(locations),
        "locations": locations,
        "map_visualization": {
            "center": {"lat": 39.8283, "lng": -98.5795},
            "zoom": 4,
            "map_url": map_url
        }
    }


def search_nearby_stores(
    city: str,
    state: str,
    business_type: str = "fashion store",
    radius_meters: int = 5000
) -> dict:
    """Search for fashion retail stores near a campaign location.

    Useful for competitive analysis and location strategy.

    Args:
        city: City name
        state: State abbreviation
        business_type: Type of business to search (default: "fashion store")
        radius_meters: Search radius in meters (default: 5000)

    Returns:
        Dictionary with nearby places
    """
    try:
        import googlemaps
    except ImportError:
        return {
            "status": "error",
            "message": "googlemaps package not installed. Run: pip install googlemaps"
        }

    api_key = GOOGLE_MAPS_API_KEY
    if not api_key:
        return {
            "status": "error",
            "message": "GOOGLE_MAPS_API_KEY environment variable not set"
        }

    gmaps = googlemaps.Client(key=api_key)

    try:
        # Geocode the location first
        location_str = f"{city}, {state}"
        geocode_result = gmaps.geocode(location_str)

        if not geocode_result:
            return {
                "status": "error",
                "message": f"Could not geocode location: {location_str}"
            }

        lat = geocode_result[0]['geometry']['location']['lat']
        lng = geocode_result[0]['geometry']['location']['lng']

        # Search for nearby places
        places_result = gmaps.places_nearby(
            location=(lat, lng),
            radius=radius_meters,
            keyword=business_type
        )

        places = []
        for place in places_result.get('results', [])[:10]:  # Limit to 10 results
            places.append({
                "name": place.get('name'),
                "address": place.get('vicinity'),
                "rating": place.get('rating'),
                "user_ratings_total": place.get('user_ratings_total'),
                "place_id": place.get('place_id'),
                "types": place.get('types', []),
                "location": {
                    "lat": place.get('geometry', {}).get('location', {}).get('lat'),
                    "lng": place.get('geometry', {}).get('location', {}).get('lng')
                }
            })

        return {
            "status": "success",
            "search_location": location_str,
            "search_type": business_type,
            "radius_meters": radius_meters,
            "results_count": len(places),
            "places": places
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Places search failed: {str(e)}"
        }


def get_location_demographics(city: str, state: str) -> dict:
    """Get demographic and market information for a location.

    Note: This provides simulated demographic data for demo purposes.
    In production, this would integrate with real demographic data sources.

    Args:
        city: City name
        state: State abbreviation

    Returns:
        Dictionary with location demographics and market data
    """
    # Simulated demographic data for demo purposes
    # In production, this would use real census/demographic APIs
    city_data = {
        "Los Angeles, CA": {
            "population": 3900000,
            "median_age": 35,
            "median_income": 65000,
            "fashion_market_index": 92,
            "style_preference": ["casual", "athleisure", "bohemian"]
        },
        "New York, NY": {
            "population": 8300000,
            "median_age": 36,
            "median_income": 72000,
            "fashion_market_index": 98,
            "style_preference": ["formal", "contemporary", "luxury"]
        },
        "Chicago, IL": {
            "population": 2700000,
            "median_age": 34,
            "median_income": 58000,
            "fashion_market_index": 78,
            "style_preference": ["professional", "classic", "urban"]
        },
        "Seattle, WA": {
            "population": 750000,
            "median_age": 36,
            "median_income": 85000,
            "fashion_market_index": 72,
            "style_preference": ["casual", "outdoor", "sustainable"]
        }
    }

    location_key = f"{city}, {state}"
    data = city_data.get(location_key)

    if data:
        return {
            "status": "success",
            "location": location_key,
            "demographics": data,
            "market_insight": f"{city} has a fashion market index of {data['fashion_market_index']}/100, "
                            f"with preferences for {', '.join(data['style_preference'])} styles."
        }
    else:
        return {
            "status": "success",
            "location": location_key,
            "demographics": {
                "population": "Data not available",
                "fashion_market_index": 50,
                "style_preference": ["general"]
            },
            "market_insight": f"Detailed demographic data not available for {location_key}. Using default market assumptions."
        }


# Simulated coordinates for demo (avoid API calls for visualization)
CITY_COORDINATES = {
    "Los Angeles, CA": {"lat": 34.0522, "lng": -118.2437},
    "New York, NY": {"lat": 40.7128, "lng": -74.0060},
    "Chicago, IL": {"lat": 41.8781, "lng": -87.6298},
    "Seattle, WA": {"lat": 47.6062, "lng": -122.3321},
}

# Region mapping for analysis
REGION_MAPPING = {
    "CA": "West Coast",
    "WA": "West Coast",
    "OR": "West Coast",
    "NY": "East Coast",
    "NJ": "East Coast",
    "MA": "East Coast",
    "IL": "Midwest",
    "OH": "Midwest",
    "MI": "Midwest",
    "TX": "South",
    "FL": "South",
    "GA": "South",
}


async def generate_map_visualization(
    visualization_type: str = "performance_map",
    metric: str = "revenue",
    tool_context: ToolContext = None
) -> dict:
    """Generate a map-based visualization of campaign performance using Gemini 3 Pro Image.

    Creates professional geographic visualizations as images using AI image generation.
    The generated map is saved as an ADK artifact for viewing in the web UI.

    Args:
        visualization_type: Type of map visualization - one of:
            - performance_map: All campaigns on US map with metric bubbles
            - regional_comparison: Compare metrics by region (West/East/Midwest)
            - category_by_region: Fashion styles performance by geography
            - market_opportunity: Current coverage vs expansion potential
            - campaign_heatmap: Revenue/density heatmap visualization
        metric: Metric to visualize - one of: revenue, impressions, engagement_rate, clicks
        tool_context: ADK ToolContext for artifact storage

    Returns:
        Dictionary with visualization details and artifact info
    """
    print(f"[DEBUG MAP VIZ] Starting generate_map_visualization")
    print(f"[DEBUG MAP VIZ] visualization_type={visualization_type}, metric={metric}")

    valid_types = ["performance_map", "regional_comparison", "category_by_region",
                   "market_opportunity", "campaign_heatmap"]
    valid_metrics = ["revenue", "impressions", "engagement_rate", "clicks"]

    if visualization_type not in valid_types:
        return {
            "status": "error",
            "message": f"Invalid visualization_type. Must be one of: {', '.join(valid_types)}"
        }

    if metric not in valid_metrics:
        return {
            "status": "error",
            "message": f"Invalid metric. Must be one of: {', '.join(valid_metrics)}"
        }

    # Fetch all campaign data with metrics
    print(f"[DEBUG MAP VIZ] Step 1: Fetching campaign data from database...")
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT
                c.id,
                c.name,
                c.category,
                c.city,
                c.state,
                c.status,
                COUNT(DISTINCT ca.id) as ad_count,
                SUM(cm.impressions) as total_impressions,
                SUM(cm.views) as total_views,
                SUM(cm.clicks) as total_clicks,
                SUM(cm.revenue) as total_revenue,
                AVG(cm.engagement_rate) as avg_engagement
            FROM campaigns c
            LEFT JOIN campaign_ads ca ON c.id = ca.campaign_id
            LEFT JOIN campaign_metrics cm ON c.id = cm.campaign_id
            GROUP BY c.id
            ORDER BY total_revenue DESC
        ''')
        campaigns = cursor.fetchall()

    if not campaigns:
        return {
            "status": "error",
            "message": "No campaign data available for visualization"
        }

    print(f"[DEBUG MAP VIZ] Step 2: Found {len(campaigns)} campaigns")

    # Process campaign data
    campaign_data = []
    regional_data = {}
    category_data = {}
    total_revenue = 0
    total_impressions = 0

    for camp in campaigns:
        location_key = f"{camp['city']}, {camp['state']}"
        coords = CITY_COORDINATES.get(location_key, {"lat": 39.8, "lng": -98.5})
        region = REGION_MAPPING.get(camp['state'], "Other")

        revenue = round(camp['total_revenue'], 2) if camp['total_revenue'] else 0
        impressions = int(camp['total_impressions']) if camp['total_impressions'] else 0
        engagement = round(camp['avg_engagement'], 2) if camp['avg_engagement'] else 0
        clicks = int(camp['total_clicks']) if camp['total_clicks'] else 0

        total_revenue += revenue
        total_impressions += impressions

        camp_info = {
            "id": camp['id'],
            "name": camp['name'],
            "category": camp['category'],
            "city": camp['city'],
            "state": camp['state'],
            "location": location_key,
            "coords": coords,
            "region": region,
            "status": camp['status'],
            "ad_count": camp['ad_count'] or 0,
            "revenue": revenue,
            "impressions": impressions,
            "clicks": clicks,
            "engagement_rate": engagement,
        }
        campaign_data.append(camp_info)

        # Aggregate by region
        if region not in regional_data:
            regional_data[region] = {"revenue": 0, "impressions": 0, "campaigns": 0, "engagement_sum": 0}
        regional_data[region]["revenue"] += revenue
        regional_data[region]["impressions"] += impressions
        regional_data[region]["campaigns"] += 1
        regional_data[region]["engagement_sum"] += engagement

        # Aggregate by category
        cat = camp['category'] or "other"
        if cat not in category_data:
            category_data[cat] = {"revenue": 0, "impressions": 0, "campaigns": 0, "locations": []}
        category_data[cat]["revenue"] += revenue
        category_data[cat]["impressions"] += impressions
        category_data[cat]["campaigns"] += 1
        category_data[cat]["locations"].append(location_key)

    # Calculate regional averages
    for region in regional_data:
        if regional_data[region]["campaigns"] > 0:
            regional_data[region]["avg_engagement"] = round(
                regional_data[region]["engagement_sum"] / regional_data[region]["campaigns"], 2
            )

    print(f"[DEBUG MAP VIZ] Step 3: Data aggregation complete")
    print(f"[DEBUG MAP VIZ]   - Total revenue: ${total_revenue:,.2f}")
    print(f"[DEBUG MAP VIZ]   - Total impressions: {total_impressions:,}")
    print(f"[DEBUG MAP VIZ]   - Regions: {list(regional_data.keys())}")
    print(f"[DEBUG MAP VIZ]   - Categories: {list(category_data.keys())}")

    # Print campaign details
    for camp in campaign_data:
        print(f"[DEBUG MAP VIZ]   - {camp['name']} ({camp['location']}): ${camp['revenue']:,.2f} revenue, {camp['impressions']:,} impressions")

    # Build visualization prompt based on type
    print(f"[DEBUG MAP VIZ] Step 4: Building prompt for visualization_type='{visualization_type}'...")

    if visualization_type == "performance_map":
        # Create location markers string
        markers_desc = ""
        for camp in campaign_data:
            status_color = "green" if camp['status'] == 'active' else "gray"
            markers_desc += f"- {camp['city']}, {camp['state']}: {camp['name']}\n"
            markers_desc += f"  Revenue: ${camp['revenue']:,.2f} | Impressions: {camp['impressions']:,}\n"
            markers_desc += f"  Status: {camp['status']} ({status_color} marker)\n"

        visualization_prompt = f"""Create a professional, modern infographic map of the United States showing advertising campaign performance:

MAP SPECIFICATIONS:
- Style: Clean, modern business dashboard map visualization
- Geographic Scope: United States (continental)
- Theme: Dark blue ocean, light gray land with state borders

CAMPAIGN LOCATIONS TO MARK (with bubbles sized by revenue):
{markers_desc}

VISUAL ELEMENTS:
1. Each location gets a circular bubble marker
2. Bubble SIZE represents revenue (larger = more revenue)
3. Bubble COLOR:
   - Green = Active campaigns
   - Gray = Draft/Inactive campaigns
4. Each bubble has a small label with city name

DATA SUMMARY PANEL (bottom or side):
- Total Revenue: ${total_revenue:,.2f}
- Total Impressions: {total_impressions:,}
- Active Campaigns: {sum(1 for c in campaign_data if c['status'] == 'active')}

STYLE REQUIREMENTS:
- Modern, flat design aesthetic
- Professional color palette (blues, greens, grays)
- Clean sans-serif typography
- Subtle drop shadows for depth
- Include a legend explaining bubble size = revenue

Create a high-quality, executive-ready map visualization suitable for business presentations."""

    elif visualization_type == "regional_comparison":
        # Build regional comparison data
        region_desc = ""
        for region, data in sorted(regional_data.items(), key=lambda x: x[1]['revenue'], reverse=True):
            region_desc += f"- {region}:\n"
            region_desc += f"  Revenue: ${data['revenue']:,.2f}\n"
            region_desc += f"  Impressions: {data['impressions']:,}\n"
            region_desc += f"  Campaigns: {data['campaigns']}\n"
            region_desc += f"  Avg Engagement: {data.get('avg_engagement', 0):.2f}%\n"

        visualization_prompt = f"""Create a professional regional comparison infographic showing advertising performance across US regions:

INFOGRAPHIC SPECIFICATIONS:
- Layout: US map with regions highlighted + comparison bar charts
- Regions: West Coast, East Coast, Midwest (each in different color)

REGIONAL DATA:
{region_desc}

VISUAL LAYOUT:
1. TOP SECTION: Stylized US map with regions color-coded
   - West Coast (California, Washington): Blue
   - East Coast (New York): Red/Orange
   - Midwest (Illinois): Green

2. BOTTOM SECTION: Horizontal bar chart comparison
   - Compare {metric} across all regions
   - Show actual values on bars
   - Rank from highest to lowest

3. KEY INSIGHTS BOX:
   - Best performing region highlighted
   - Percentage comparison between regions

STYLE:
- Modern dashboard aesthetic
- Bold, clear typography
- High contrast for readability
- Professional business visualization
- Include legend for colors

Create an executive summary view of regional advertising performance."""

    elif visualization_type == "category_by_region":
        # Build category performance data
        category_desc = ""
        for cat, data in sorted(category_data.items(), key=lambda x: x[1]['revenue'], reverse=True):
            category_desc += f"- {cat.title()} Fashion:\n"
            category_desc += f"  Revenue: ${data['revenue']:,.2f}\n"
            category_desc += f"  Locations: {', '.join(data['locations'])}\n"

        visualization_prompt = f"""Create a professional infographic showing which fashion categories perform best in which geographic regions:

INFOGRAPHIC SPECIFICATIONS:
- Theme: Fashion retail performance by location
- Style: Modern, editorial magazine quality

CATEGORY PERFORMANCE DATA:
{category_desc}

VISUAL LAYOUT:
1. STYLIZED US MAP with fashion icons at each location:
   - Los Angeles: Summer/casual wear (sun icon)
   - New York: Formal/evening wear (dress icon)
   - Chicago: Professional/business wear (blazer icon)
   - Seattle: Essentials/cozy wear (sweater icon)

2. CATEGORY CARDS (grid below map):
   Each card shows:
   - Category name with icon
   - Best performing location
   - Revenue in that category
   - Style descriptors

3. INSIGHTS PANEL:
   - "Summer styles perform best on West Coast"
   - "Formal wear leads in NYC"
   - Key regional preferences

STYLE REQUIREMENTS:
- Fashion-forward, editorial aesthetic
- Elegant typography (mix of serif and sans-serif)
- Soft, sophisticated color palette
- Include category icons (dress, blazer, sweater)
- Magazine-quality layout

Create a beautiful visualization for fashion retail strategy."""

    elif visualization_type == "market_opportunity":
        # Get demographic data for analysis
        demographics = {}
        for loc in ["Los Angeles, CA", "New York, NY", "Chicago, IL", "Seattle, WA"]:
            city, state = loc.split(", ")
            demo_result = get_location_demographics(city, state)
            if demo_result["status"] == "success":
                demographics[loc] = demo_result["demographics"]

        opportunity_desc = ""
        for loc, demo in demographics.items():
            camp = next((c for c in campaign_data if c['location'] == loc), None)
            current_revenue = camp['revenue'] if camp else 0
            market_index = demo.get('fashion_market_index', 50)
            population = demo.get('population', 'N/A')

            # Calculate opportunity score (market index - current penetration)
            opportunity_score = market_index - (current_revenue / 1000) if current_revenue else market_index

            opportunity_desc += f"- {loc}:\n"
            opportunity_desc += f"  Population: {population:,} | Market Index: {market_index}/100\n"
            opportunity_desc += f"  Current Revenue: ${current_revenue:,.2f}\n"
            opportunity_desc += f"  Style Preferences: {', '.join(demo.get('style_preference', []))}\n"

        visualization_prompt = f"""Create a market opportunity map showing current campaign coverage versus expansion potential:

INFOGRAPHIC SPECIFICATIONS:
- Theme: Market expansion strategy visualization
- Style: Strategic planning dashboard

MARKET DATA:
{opportunity_desc}

VISUAL LAYOUT:
1. US MAP showing opportunity levels:
   - Current locations marked with solid circles
   - Opportunity level shown by halo/glow intensity
   - Green glow = high opportunity
   - Yellow glow = moderate opportunity

2. OPPORTUNITY SCORECARD (side panel):
   For each market:
   - Current revenue bar
   - Market potential bar (based on fashion market index)
   - Gap = expansion opportunity

3. EXPANSION RECOMMENDATIONS:
   - Top 2 markets for growth
   - Underserved style categories
   - Population-based opportunity

4. KEY METRICS SUMMARY:
   - Total addressable market
   - Current market penetration
   - Growth potential %

STYLE:
- Strategic, data-driven aesthetic
- Color gradient from current (blue) to opportunity (green)
- Clean executive dashboard look
- Include growth arrow indicators

Create a strategic market opportunity visualization for expansion planning."""

    else:  # campaign_heatmap
        # Build heatmap data
        heatmap_desc = ""
        for camp in campaign_data:
            intensity = "High" if camp['revenue'] > 30000 else "Medium" if camp['revenue'] > 15000 else "Low"
            heatmap_desc += f"- {camp['location']}: {intensity} intensity (${camp['revenue']:,.2f})\n"

        visualization_prompt = f"""Create a heatmap visualization showing campaign revenue density across the United States:

INFOGRAPHIC SPECIFICATIONS:
- Style: Modern heatmap with glowing intensity
- Theme: Revenue concentration visualization

HEATMAP DATA POINTS:
{heatmap_desc}

VISUAL LAYOUT:
1. US MAP BASE:
   - Dark background for contrast
   - Subtle state borders

2. HEATMAP OVERLAY:
   - Glowing circles at each campaign location
   - Intensity (brightness/size) based on revenue
   - Color gradient: Blue (low) → Yellow (medium) → Red/Orange (high)
   - Soft glow/bloom effect for visual appeal

3. INTENSITY LEGEND:
   - Low: < $15,000 (blue, small glow)
   - Medium: $15,000 - $30,000 (yellow, medium glow)
   - High: > $30,000 (red/orange, large glow)

4. SUMMARY STATISTICS:
   - Total revenue: ${total_revenue:,.2f}
   - Campaign concentration areas
   - Revenue per region

STYLE:
- Dark mode dashboard aesthetic
- Neon/glowing effect for data points
- Modern data visualization style
- Include color scale legend

Create a visually striking revenue heatmap suitable for executive dashboards."""

    print(f"[DEBUG MAP VIZ] Step 5: Complete prompt being sent to Gemini 3 Pro Image:")
    print(f"[DEBUG MAP VIZ] {'='*60}")
    print(visualization_prompt[:500] + "..." if len(visualization_prompt) > 500 else visualization_prompt)
    print(f"[DEBUG MAP VIZ] {'='*60}")
    print(f"[DEBUG MAP VIZ] Prompt length: {len(visualization_prompt)} characters")

    try:
        print("[DEBUG MAP VIZ] Step 6: Calling Gemini 3 Pro Image API...")
        client = genai.Client()

        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[visualization_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9",
                )
            )
        )
        print(f"[DEBUG MAP VIZ]   - Response received, parts count: {len(response.parts) if response.parts else 0}")

        # Extract image from response
        generated_image = None
        for i, part in enumerate(response.parts):
            has_inline = hasattr(part, 'inline_data') and part.inline_data is not None
            print(f"[DEBUG MAP VIZ]   - Part {i}: has inline_data={has_inline}")
            if part.inline_data:
                generated_image = part
                print(f"[DEBUG MAP VIZ]   - Image found in part {i}, size: {len(part.inline_data.data)} bytes")
                break

        if generated_image is None:
            print("[DEBUG MAP VIZ]   - ERROR: No image found in response")
            return {
                "status": "error",
                "message": "Failed to generate map visualization. Try a different visualization type."
            }

        # Save as ADK artifact
        timestamp = int(time.time())
        filename = f"map_{visualization_type}_{metric}_{timestamp}.png"

        print(f"[DEBUG MAP VIZ] Step 7: Saving artifact...")
        if tool_context:
            print(f"[DEBUG MAP VIZ]   - Filename: {filename}")
            image_bytes = generated_image.inline_data.data
            image_artifact = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
            version = await tool_context.save_artifact(filename=filename, artifact=image_artifact)
            print(f"[DEBUG MAP VIZ]   - Artifact saved successfully, version: {version}")
            artifact_saved = True
        else:
            print("[DEBUG MAP VIZ]   - WARNING: No tool_context, artifact not saved")
            artifact_saved = False
            version = None

        print(f"[DEBUG MAP VIZ] Step 8: SUCCESS - Map visualization complete!")

        return {
            "status": "success",
            "message": f"Generated {visualization_type} map visualization",
            "visualization": {
                "type": visualization_type,
                "metric": metric,
                "filename": filename,
                "artifact_saved": artifact_saved,
                "artifact_version": version,
            },
            "data_summary": {
                "campaigns_shown": len(campaign_data),
                "total_revenue": total_revenue,
                "total_impressions": total_impressions,
                "regions": list(regional_data.keys()),
                "categories": list(category_data.keys()),
            },
            "campaigns": [
                {
                    "name": c["name"],
                    "location": c["location"],
                    "revenue": c["revenue"],
                    "status": c["status"]
                }
                for c in campaign_data
            ]
        }

    except Exception as e:
        import traceback
        print(f"[DEBUG MAP VIZ] EXCEPTION: {str(e)}")
        print(f"[DEBUG MAP VIZ] Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Failed to generate map visualization: {str(e)}"
        }
