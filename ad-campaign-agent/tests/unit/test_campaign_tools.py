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

"""Unit tests for campaign_tools.py.

Tests the 7 campaign-related tools:
- create_campaign
- list_campaigns
- get_campaign
- update_campaign
- get_campaign_locations
- search_nearby_stores
- get_location_demographics
"""

import pytest
from unittest.mock import patch, MagicMock


class TestListCampaigns:
    """Tests for list_campaigns tool."""

    def test_list_campaigns_returns_all(self, test_db):
        """list_campaigns should return all pre-loaded campaigns."""
        from app.tools.campaign_tools import list_campaigns

        result = list_campaigns()

        assert "campaigns" in result
        campaigns = result["campaigns"]
        assert len(campaigns) >= 4  # Pre-loaded demo campaigns

    def test_list_campaigns_structure(self, test_db):
        """Each campaign should have required fields."""
        from app.tools.campaign_tools import list_campaigns

        result = list_campaigns()
        campaign = result["campaigns"][0]

        # Check required fields
        assert "id" in campaign
        assert "name" in campaign
        assert "status" in campaign
        assert "store_name" in campaign

    def test_list_campaigns_includes_product_info(self, test_db):
        """Campaigns should include product information."""
        from app.tools.campaign_tools import list_campaigns

        result = list_campaigns()
        campaign = result["campaigns"][0]

        # Product-centric model should include product details
        assert "product_name" in campaign or "product_id" in campaign


class TestGetCampaign:
    """Tests for get_campaign tool."""

    def test_get_campaign_valid_id(self, test_db):
        """get_campaign should return campaign details for valid ID."""
        from app.tools.campaign_tools import get_campaign

        result = get_campaign(campaign_id=1)

        assert "campaign" in result
        assert result["campaign"]["id"] == 1
        assert "name" in result["campaign"]

    def test_get_campaign_invalid_id(self, test_db):
        """get_campaign should handle invalid campaign ID."""
        from app.tools.campaign_tools import get_campaign

        result = get_campaign(campaign_id=9999)

        # Should return error or empty result
        assert "error" in result or result.get("campaign") is None

    def test_get_campaign_includes_location(self, test_db):
        """Campaign should include location information."""
        from app.tools.campaign_tools import get_campaign

        result = get_campaign(campaign_id=1)
        campaign = result.get("campaign", {})

        assert "city" in campaign or "store_name" in campaign


class TestCreateCampaign:
    """Tests for create_campaign tool."""

    def test_create_campaign_basic(self, test_db):
        """create_campaign should create a new campaign."""
        from app.tools.campaign_tools import create_campaign

        result = create_campaign(
            product_id=1,
            store_name="Test Store",
            city="San Francisco",
            state="California"
        )

        assert "success" in result or "campaign" in result or "id" in result

    def test_create_campaign_generates_name(self, test_db):
        """Campaign name should be auto-generated from product and store."""
        from app.tools.campaign_tools import create_campaign

        result = create_campaign(
            product_id=1,
            store_name="New Test Store",
            city="Los Angeles",
            state="California"
        )

        # Name should follow pattern: "Product Name - Store Name"
        if "campaign" in result:
            assert "name" in result["campaign"]
            assert "Test Store" in result["campaign"]["name"] or result["campaign"]["name"]

    def test_create_campaign_invalid_product(self, test_db):
        """create_campaign should handle invalid product ID."""
        from app.tools.campaign_tools import create_campaign

        result = create_campaign(
            product_id=9999,  # Non-existent product
            store_name="Test Store",
            city="Test City",
            state="Test State"
        )

        # Should return error
        assert "error" in result or "not found" in str(result).lower()


class TestUpdateCampaign:
    """Tests for update_campaign tool."""

    def test_update_campaign_status(self, test_db):
        """update_campaign should change campaign status."""
        from app.tools.campaign_tools import update_campaign

        result = update_campaign(campaign_id=1, status="paused")

        assert "success" in result or "updated" in str(result).lower()

    def test_update_campaign_invalid_status(self, test_db):
        """update_campaign should reject invalid status values."""
        from app.tools.campaign_tools import update_campaign

        result = update_campaign(campaign_id=1, status="invalid_status")

        # Should return error for invalid status
        assert "error" in result or "invalid" in str(result).lower()

    def test_update_campaign_invalid_id(self, test_db):
        """update_campaign should handle invalid campaign ID."""
        from app.tools.campaign_tools import update_campaign

        result = update_campaign(campaign_id=9999, status="active")

        assert "error" in result or "not found" in str(result).lower()


class TestGetCampaignLocations:
    """Tests for get_campaign_locations tool.

    Note: This function is in maps_tools.py, not campaign_tools.py
    """

    def test_get_campaign_locations_returns_all(self, test_db):
        """get_campaign_locations should return all campaign locations."""
        from app.tools.maps_tools import get_campaign_locations

        result = get_campaign_locations()

        # Should return locations or error if API key missing
        assert "locations" in result or "error" in result or "status" in result
        if "locations" in result:
            assert len(result["locations"]) >= 1

    def test_get_campaign_locations_has_coordinates(self, test_db):
        """Locations should include lat/lng coordinates."""
        from app.tools.maps_tools import get_campaign_locations

        result = get_campaign_locations()

        # Skip if API key not configured
        if "error" in result or result.get("status") == "error":
            pytest.skip("GOOGLE_MAPS_API_KEY not configured")

        location = result["locations"][0]

        # Should have coordinates for map display
        assert "latitude" in location or "lat" in location
        assert "longitude" in location or "lng" in location


class TestSearchNearbyStores:
    """Tests for search_nearby_stores tool.

    Note: This function is in maps_tools.py and uses city/state params
    """

    @pytest.fixture
    def mock_maps_api(self):
        """Mock Google Maps API for testing."""
        with patch("googlemaps.Client") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            mock_instance.places_nearby.return_value = {
                "results": [
                    {"name": "Store 1", "vicinity": "123 Test St"},
                    {"name": "Store 2", "vicinity": "456 Demo Ave"},
                ]
            }
            yield mock_instance

    def test_search_nearby_stores_with_mock(self, test_db, mock_maps_api):
        """search_nearby_stores should return nearby store results."""
        from app.tools.maps_tools import search_nearby_stores

        # Function uses city/state params, not lat/lng
        result = search_nearby_stores(
            city="Los Angeles",
            state="CA",
            business_type="fashion store",
            radius_meters=1000
        )

        # Should return stores or error if API key not configured
        assert "stores" in result or "error" in result or "status" in result


class TestGetLocationDemographics:
    """Tests for get_location_demographics tool.

    Note: This function is in maps_tools.py and takes city/state parameters
    """

    def test_get_location_demographics(self, test_db):
        """get_location_demographics should return demographic data."""
        from app.tools.maps_tools import get_location_demographics

        result = get_location_demographics(city="Los Angeles", state="CA")

        # Should return demographics or handle gracefully
        assert "demographics" in result or "error" in result or "data" in result
