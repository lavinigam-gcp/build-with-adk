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

"""Google Maps Places API search tool for competitor mapping."""

from google.adk.tools import ToolContext


def search_places(query: str, tool_context: ToolContext) -> dict:
    """Search for places using Google Maps Places API.

    This tool searches for businesses/places matching the query using the
    Google Maps Places API. It returns real competitor data including names,
    addresses, ratings, and other relevant information.

    Args:
        query: Search query combining business type and location.
               Example: "fitness studio near KR Puram, Bangalore, India"

    Returns:
        dict: A dictionary containing:
            - status: "success" or "error"
            - results: List of places found with details
            - count: Number of results found
            - error_message: Error details if status is "error"
    """
    try:
        import googlemaps

        # Get API key from session state
        maps_api_key = tool_context.state.get("maps_api_key", "")

        if not maps_api_key:
            return {
                "status": "error",
                "error_message": "Maps API key not found in session state. Please set 'maps_api_key' in initial state.",
                "results": [],
                "count": 0,
            }

        # Initialize Google Maps client
        gmaps = googlemaps.Client(key=maps_api_key)

        # Perform places search
        result = gmaps.places(query)

        # Extract and format results
        places = []
        for place in result.get("results", []):
            places.append({
                "name": place.get("name", "Unknown"),
                "address": place.get("formatted_address", place.get("vicinity", "N/A")),
                "rating": place.get("rating", 0),
                "user_ratings_total": place.get("user_ratings_total", 0),
                "price_level": place.get("price_level", "N/A"),
                "types": place.get("types", []),
                "business_status": place.get("business_status", "UNKNOWN"),
                "location": {
                    "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                    "lng": place.get("geometry", {}).get("location", {}).get("lng"),
                },
                "place_id": place.get("place_id", ""),
            })

        return {
            "status": "success",
            "results": places,
            "count": len(places),
            "next_page_token": result.get("next_page_token"),
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "results": [],
            "count": 0,
        }
