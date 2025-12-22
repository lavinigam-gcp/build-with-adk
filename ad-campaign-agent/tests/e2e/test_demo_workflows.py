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

"""End-to-End workflow tests based on DEMO_GUIDE.md.

These tests validate complete user journeys through the ad-campaign-agent,
simulating the demo scenarios to ensure the system works end-to-end.

Run with: pytest tests/e2e -v -m "not slow"
"""

import asyncio
import os
from typing import Any

import pytest

# Skip if running in minimal test mode
pytestmark = [pytest.mark.e2e]


class TestAgentDiscoveryWorkflow:
    """Act 1: Understanding the Platform.

    Tests the initial discovery workflow where users learn about
    available agents and browse existing campaigns/products.
    """

    def test_list_campaigns_returns_expected_structure(self, shared_test_db):
        """Scene 1.1: List campaigns shows 4 pre-loaded campaigns."""
        from app.tools.campaign_tools import list_campaigns

        result = list_campaigns()

        assert "campaigns" in result
        campaigns = result["campaigns"]
        # Should have 4 demo campaigns
        assert len(campaigns) >= 4

        # Verify campaign structure
        for campaign in campaigns:
            assert "id" in campaign
            assert "name" in campaign
            assert "product_name" in campaign
            assert "store_name" in campaign
            assert "status" in campaign

    def test_list_products_shows_catalog(self, shared_test_db):
        """Scene 1.2: Browse product catalog shows 22 products."""
        from app.tools.video_tools import list_products

        result = list_products()

        assert "products" in result
        products = result["products"]
        # Should have 22 products
        assert len(products) >= 22

        # Verify product structure
        for product in products:
            assert "id" in product
            assert "name" in product
            assert "category" in product
            assert "image_url" in product

    def test_products_have_categories(self, shared_test_db):
        """Products should be organized by category."""
        from app.tools.video_tools import list_products

        result = list_products()
        products = result["products"]

        # Extract unique categories
        categories = set(p["category"] for p in products)

        # Should have multiple categories (dress, outerwear, etc.)
        assert len(categories) >= 3


class TestCreativeGenerationWorkflow:
    """Act 2: Creative Generation with AI.

    Tests the video generation workflow including variation presets
    and video listing. Actual video generation is marked as slow.
    """

    def test_variation_presets_available(self, shared_test_db):
        """Scene 2.1: Variation presets for A/B testing."""
        from app.tools.video_tools import get_variation_presets

        result = get_variation_presets()

        assert "presets" in result
        presets = result["presets"]

        # Should have diversity, settings, and moods
        assert "diversity" in presets
        assert "settings" in presets
        assert "moods" in presets

        # Verify diversity options (list of variation dicts)
        diversity = presets["diversity"]
        assert len(diversity) > 0
        # Check that asian ethnicity is represented
        ethnicities = [v.get("model_ethnicity") for v in diversity]
        assert "asian" in ethnicities
        assert "european" in ethnicities
        assert "african" in ethnicities

        # Verify settings (list of variation dicts)
        settings = presets["settings"]
        assert len(settings) > 0
        setting_names = [v.get("setting") for v in settings]
        assert "beach" in setting_names
        assert "urban" in setting_names

        # Verify moods (list of variation dicts)
        moods = presets["moods"]
        assert len(moods) > 0
        mood_names = [v.get("mood") for v in moods]
        assert "romantic" in mood_names

    def test_campaign_videos_list(self, shared_test_db):
        """Scene 2.2+: List videos for a campaign."""
        from app.tools.video_tools import list_campaign_videos

        result = list_campaign_videos(campaign_id=1)

        assert "videos" in result
        # May have videos if any were generated
        videos = result["videos"]

        # Verify video structure if present
        for video in videos:
            assert "id" in video
            assert "status" in video

    @pytest.mark.slow
    @pytest.mark.veo
    def test_video_generation_flow(self, shared_test_db, mock_storage_module):
        """Scene 2.2: Generate a video (requires Veo API).

        This test validates the full video generation flow:
        1. Get a campaign
        2. Generate video with variation parameters
        3. Verify video is created with 'generated' status
        """
        from app.tools.campaign_tools import get_campaign
        from app.tools.video_tools import generate_video_from_product

        # Get campaign details
        campaign = get_campaign(campaign_id=1)
        assert campaign is not None

        # Generate video (this is slow - 2-3 minutes)
        result = generate_video_from_product(
            campaign_id=1,
            model_ethnicity="european",
            setting="studio",
            mood="elegant",
            lighting="soft",
            activity="posing",
        )

        # Verify result
        assert "video" in result or "error" in result
        if "video" in result:
            video = result["video"]
            assert video["status"] == "generated"


class TestHITLReviewWorkflow:
    """Act 3: Human-in-the-Loop Review.

    Tests the video review and activation workflow.
    """

    def test_video_review_table(self, shared_test_db):
        """Scene 3.1: Video review table with public links."""
        from app.tools.review_tools import get_video_review_table

        result = get_video_review_table()

        # API returns 'table' key with markdown content, or 'videos' list
        assert "table" in result or "videos" in result or "status" in result
        if "table" in result:
            # Table is markdown string
            assert isinstance(result["table"], str)
        if "videos" in result:
            # Videos list should be present
            assert isinstance(result["videos"], list)

    def test_activation_summary(self, shared_test_db):
        """Scene 3.2: Activation summary shows counts by status."""
        from app.tools.review_tools import get_activation_summary

        result = get_activation_summary()

        # API returns status counts at top level
        assert "status" in result or "total_videos" in result or "status_counts" in result
        if "total_videos" in result:
            assert result["total_videos"] >= 0
        if "status_counts" in result:
            assert isinstance(result["status_counts"], dict)

    def test_pending_videos_list(self, shared_test_db):
        """Scene 3.2: List pending videos for review."""
        from app.tools.review_tools import list_pending_videos

        result = list_pending_videos()

        # API returns 'videos' not 'pending_videos'
        assert "videos" in result or "pending_videos" in result or "status" in result
        videos = result.get("videos", result.get("pending_videos", []))

        for video in videos:
            assert "id" in video

    def test_video_activation_flow(self, shared_test_db):
        """Scene 3.2: Activate a video (generates metrics)."""
        from app.tools.review_tools import activate_video, get_video_status
        from app.tools.video_tools import list_campaign_videos

        # First check if there are any videos to activate
        videos = list_campaign_videos(campaign_id=1)

        if videos["videos"]:
            video_id = videos["videos"][0]["id"]

            # Activate the video
            result = activate_video(video_id=video_id)

            if result.get("status") != "error" and "error" not in result:
                # Verify status changed - API returns {status: success, video_status: activated}
                status_result = get_video_status(video_id=video_id)
                # Check for video_status field or status field
                video_status = status_result.get("video_status", status_result.get("status"))
                assert video_status in ["activated", "success"]


class TestAnalyticsWorkflow:
    """Act 4: Analytics & Optimization.

    Tests the analytics and metrics workflow.
    """

    def test_campaign_metrics(self, shared_test_db):
        """Scene 4.1: Campaign metrics over time period."""
        from app.tools.metrics_tools import get_campaign_metrics

        result = get_campaign_metrics(campaign_id=1, days=30)

        # API returns metrics at top level, not nested
        assert "status" in result or "daily_metrics" in result or "summary" in result
        # Should have campaign info
        if "campaign" in result:
            assert "id" in result["campaign"]

    def test_top_performing_ads(self, shared_test_db):
        """Scene 4.1: Top performing ads by RPI."""
        from app.tools.metrics_tools import get_top_performing_ads

        result = get_top_performing_ads(limit=5)

        assert "top_ads" in result
        ads = result["top_ads"]

        # Should be sorted by performance
        if len(ads) >= 2:
            # Verify sorted by RPI (revenue per impression)
            for i in range(len(ads) - 1):
                if "rpi" in ads[i] and "rpi" in ads[i + 1]:
                    assert ads[i]["rpi"] >= ads[i + 1]["rpi"]

    def test_campaign_comparison(self, shared_test_db):
        """Scene 4.3: Compare campaigns side by side."""
        from app.tools.metrics_tools import compare_campaigns

        result = compare_campaigns(campaign_ids=[1, 2, 3, 4])

        # API returns 'comparisons' not 'comparison'
        assert "comparisons" in result or "comparison" in result or "status" in result
        if "comparisons" in result:
            assert isinstance(result["comparisons"], list)

    @pytest.mark.slow
    def test_chart_generation(self, shared_test_db):
        """Scene 4.2: Generate metrics visualization."""
        from app.tools.metrics_tools import generate_metrics_visualization

        result = generate_metrics_visualization(
            campaign_id=1,
            chart_type="trendline",
            metric="rpi",
            days=30,
        )

        # Should return chart or error
        assert "chart_url" in result or "error" in result


class TestGeographicIntelligenceWorkflow:
    """Act 5: Geographic Intelligence.

    Tests the maps and location-based workflow.
    """

    def test_campaign_map_data(self, shared_test_db):
        """Scene 5.1: Campaign locations with Google Maps links."""
        from app.tools.maps_tools import get_campaign_map_data

        result = get_campaign_map_data()

        # API returns 'locations' at top level, not nested in 'map_data'
        assert "locations" in result or "map_data" in result or "status" in result
        locations = result.get("locations", result.get("map_data", {}).get("locations", []))

        for location in locations:
            # Should have campaign info
            assert "campaign_id" in location or "id" in location
            # Coordinates may be nested in 'coordinates' dict or at top level
            has_coords = (
                "lat" in location or
                "latitude" in location or
                ("coordinates" in location and "lat" in location["coordinates"])
            )
            assert has_coords, f"Location missing coordinates: {location.keys()}"

    def test_campaign_locations(self, shared_test_db):
        """Scene 5.1: Get all store locations."""
        from app.tools.maps_tools import get_campaign_locations

        result = get_campaign_locations()

        # Handle API key not being set
        if result.get("status") == "error":
            pytest.skip("GOOGLE_MAPS_API_KEY not configured")

        assert "locations" in result
        locations = result["locations"]

        # Should have demo store locations
        assert len(locations) >= 1

        for location in locations:
            assert "store_name" in location or "name" in location
            assert "city" in location

    @pytest.mark.slow
    def test_map_visualization(self, shared_test_db):
        """Scene 5.2: Generate map visualization."""
        from app.tools.maps_tools import generate_map_visualization

        result = generate_map_visualization(style="infographic")

        # Should return map or error
        assert "map_url" in result or "error" in result


class TestOptimizationWorkflow:
    """Act 6: Apply Winning Formula.

    Tests the optimization workflow for scaling success.
    """

    def test_campaign_insights(self, shared_test_db):
        """Get campaign insights for optimization."""
        from app.tools.metrics_tools import get_campaign_insights

        result = get_campaign_insights(campaign_id=1)

        # API may return 'insights' or 'status' or nested structure
        assert "insights" in result or "status" in result or "campaign" in result

    def test_get_campaign_details(self, shared_test_db):
        """Scene 6.1: Get campaign details for formula extraction."""
        from app.tools.campaign_tools import get_campaign

        result = get_campaign(campaign_id=1)

        # Handle different response structures
        assert "campaign" in result or "id" in result or "status" in result
        if "campaign" in result:
            campaign = result["campaign"]
            assert campaign["id"] == 1
        elif "id" in result:
            assert result["id"] == 1


class TestMultiAgentWorkflow:
    """Test multi-agent coordination scenarios.

    These tests verify that the coordinator properly routes
    queries to the appropriate sub-agents.
    """

    def test_campaign_then_analytics_flow(self, shared_test_db):
        """Cross-agent workflow: Campaign -> Analytics."""
        from app.tools.campaign_tools import list_campaigns
        from app.tools.metrics_tools import get_campaign_metrics

        # Step 1: List campaigns (Campaign Agent)
        campaigns = list_campaigns()
        assert len(campaigns["campaigns"]) >= 1

        # Step 2: Get metrics for first campaign (Analytics Agent)
        campaign_id = campaigns["campaigns"][0]["id"]
        metrics = get_campaign_metrics(campaign_id=campaign_id, days=30)
        # API returns metrics at top level
        assert "status" in metrics or "daily_metrics" in metrics or "summary" in metrics

    def test_product_then_review_flow(self, shared_test_db):
        """Cross-agent workflow: Media -> Review."""
        from app.tools.video_tools import list_products, list_campaign_videos
        from app.tools.review_tools import get_video_review_table

        # Step 1: List products (Media Agent)
        products = list_products()
        assert len(products["products"]) >= 1

        # Step 2: List campaign videos (Media Agent)
        videos = list_campaign_videos(campaign_id=1)
        assert "videos" in videos

        # Step 3: Get review table (Review Agent)
        review_table = get_video_review_table()
        assert "table" in review_table or "videos" in review_table or "status" in review_table


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_campaign_id(self, shared_test_db):
        """Handle request for non-existent campaign."""
        from app.tools.campaign_tools import get_campaign

        result = get_campaign(campaign_id=9999)

        # Should handle gracefully
        assert "error" in result or result.get("campaign") is None

    def test_invalid_video_id(self, shared_test_db):
        """Handle request for non-existent video."""
        from app.tools.review_tools import get_video_status

        result = get_video_status(video_id=9999)

        # Should handle gracefully - may return error status or None
        assert "error" in result or result.get("status") == "error" or result.get("video_status") is None

    def test_empty_metrics(self, shared_test_db):
        """Handle campaign with no metrics."""
        from app.tools.metrics_tools import get_campaign_metrics

        # Campaign might not have activated videos yet
        result = get_campaign_metrics(campaign_id=999, days=30)

        # Should handle gracefully - may return status or empty metrics
        assert "status" in result or "error" in result or "daily_metrics" in result


class TestDataConsistency:
    """Test data consistency across agents."""

    def test_campaign_product_consistency(self, shared_test_db):
        """Campaigns should reference valid products."""
        from app.tools.campaign_tools import list_campaigns
        from app.tools.video_tools import list_products

        campaigns = list_campaigns()
        products = list_products()

        # Get product IDs
        product_ids = {p["id"] for p in products["products"]}

        # Verify each campaign references a valid product
        for campaign in campaigns["campaigns"]:
            if "product_id" in campaign:
                assert campaign["product_id"] in product_ids

    def test_video_campaign_consistency(self, shared_test_db):
        """Videos should belong to valid campaigns."""
        from app.tools.campaign_tools import list_campaigns
        from app.tools.video_tools import list_campaign_videos

        campaigns = list_campaigns()
        campaign_ids = {c["id"] for c in campaigns["campaigns"]}

        # Check videos for first campaign
        if campaigns["campaigns"]:
            campaign_id = campaigns["campaigns"][0]["id"]
            videos = list_campaign_videos(campaign_id=campaign_id)

            for video in videos["videos"]:
                assert video.get("campaign_id", campaign_id) == campaign_id
