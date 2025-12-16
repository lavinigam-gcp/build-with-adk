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

import os
from typing import Optional

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
