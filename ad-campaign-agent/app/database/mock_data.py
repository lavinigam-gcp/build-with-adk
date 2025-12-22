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

"""Mock data population for the Ad Campaign Agent demo.

Uses NEW schema (product-centric model):
- products: 22 pre-loaded fashion products
- campaigns: Each campaign = 1 product + 1 store location
- campaign_videos: Videos with HITL lifecycle status
- video_metrics: Metrics only for activated videos
"""

import json
import random
from datetime import datetime, timedelta
from .db import get_connection
from .products_data import PRODUCTS


# =============================================================================
# Product-Centric Campaign Definitions (NEW MODEL)
# =============================================================================
# Each campaign = 1 product + 1 store location
# Campaign name auto-generated: "{Product Name} - {Store Name}"

MOCK_CAMPAIGNS = [
    {
        "product_name": "blue-floral-maxi-dress",
        "store_name": "Westfield Century City",
        "city": "Los Angeles",
        "state": "CA",
        "category": "summer",
        "status": "active",
    },
    {
        "product_name": "elegant-black-cocktail-dress",
        "store_name": "Bloomingdale's 59th Street",
        "city": "New York",
        "state": "NY",
        "category": "formal",
        "status": "active",
    },
    {
        "product_name": "black-high-waist-trousers",
        "store_name": "Water Tower Place",
        "city": "Chicago",
        "state": "IL",
        "category": "professional",
        "status": "active",
    },
    {
        # Changed from emerald-satin-slip-dress (no real videos) to sage-satin-camisole
        "product_name": "sage-satin-camisole",
        "store_name": "The Grove",
        "city": "Los Angeles",
        "state": "CA",
        "category": "essentials",  # 'casual' not in CHECK constraint; using 'essentials'
        "status": "active",
    },
]

# =============================================================================
# REAL Videos in GCS (gs://kaggle-on-gcp-ad-campaign-assets/generated/)
# =============================================================================
# These are actual Veo-generated videos that exist in the bucket.
# Each campaign gets multiple real videos with thumbnails.

REAL_VIDEOS = {
    "blue-floral-maxi-dress": [
        {
            "filename": "blue-floral-maxi-dress-122025-asian-beach-romantic.mp4",
            "thumbnail": "blue-floral-maxi-dress-122025-asian-beach-romantic-thumbnail.png",
            "variation": {"model_ethnicity": "asian", "setting": "beach", "mood": "romantic", "time_of_day": "day"},
        },
        {
            "filename": "blue-floral-maxi-dress-122025-european-urban-bold.mp4",
            "thumbnail": "blue-floral-maxi-dress-122025-european-urban-bold-thumbnail.png",
            "variation": {"model_ethnicity": "european", "setting": "urban", "mood": "bold", "time_of_day": "day"},
        },
        {
            "filename": "blue-floral-maxi-dress-122225-latina-beach-romantic.mp4",
            "thumbnail": "blue-floral-maxi-dress-122225-latina-beach-romantic-thumbnail.png",
            "variation": {"model_ethnicity": "latina", "setting": "beach", "mood": "romantic", "time_of_day": "day"},
        },
    ],
    "elegant-black-cocktail-dress": [
        {
            "filename": "elegant-black-cocktail-dress-122225-diverse-rooftop-sophisticated.mp4",
            "thumbnail": "elegant-black-cocktail-dress-122225-diverse-rooftop-sophisticated-thumbnail.png",
            "variation": {"model_ethnicity": "diverse", "setting": "rooftop", "mood": "sophisticated", "time_of_day": "day"},
        },
    ],
    "black-high-waist-trousers": [
        {
            "filename": "black-high-waist-trousers-122025-african-studio-sophisticated.mp4",
            "thumbnail": "black-high-waist-trousers-122025-african-studio-sophisticated-thumbnail.png",
            "variation": {"model_ethnicity": "african", "setting": "studio", "mood": "sophisticated", "time_of_day": "day"},
        },
        {
            "filename": "black-high-waist-trousers-122025-asian-cafe-sophisticated.mp4",
            "thumbnail": "black-high-waist-trousers-122025-asian-cafe-sophisticated-thumbnail.png",
            "variation": {"model_ethnicity": "asian", "setting": "cafe", "mood": "sophisticated", "time_of_day": "day"},
        },
        {
            "filename": "black-high-waist-trousers-122025-latina-rooftop-bold.mp4",
            "thumbnail": "black-high-waist-trousers-122025-latina-rooftop-bold-thumbnail.png",
            "variation": {"model_ethnicity": "latina", "setting": "rooftop", "mood": "bold", "time_of_day": "day"},
        },
    ],
    "sage-satin-camisole": [
        {
            "filename": "sage-satin-camisole-122225-african-studio-bold.mp4",
            "thumbnail": "sage-satin-camisole-122225-african-studio-bold-thumbnail.png",
            "variation": {"model_ethnicity": "african", "setting": "studio", "mood": "bold", "time_of_day": "day"},
        },
        {
            "filename": "sage-satin-camisole-122225-asian-cafe-sophisticated.mp4",
            "thumbnail": "sage-satin-camisole-122225-asian-cafe-sophisticated-thumbnail.png",
            "variation": {"model_ethnicity": "asian", "setting": "cafe", "mood": "sophisticated", "time_of_day": "day"},
        },
        {
            "filename": "sage-satin-camisole-122225-european-urban-elegant.mp4",
            "thumbnail": "sage-satin-camisole-122225-european-urban-elegant-thumbnail.png",
            "variation": {"model_ethnicity": "european", "setting": "urban", "mood": "elegant", "time_of_day": "day"},
        },
    ],
}

# Legacy variation presets (for new video generation)
MOCK_VARIATIONS = [
    {"model_ethnicity": "asian", "setting": "beach", "mood": "romantic", "time_of_day": "golden-hour"},
    {"model_ethnicity": "european", "setting": "urban", "mood": "sophisticated", "time_of_day": "day"},
    {"model_ethnicity": "african", "setting": "studio", "mood": "bold", "time_of_day": "day"},
    {"model_ethnicity": "latina", "setting": "rooftop", "mood": "romantic", "time_of_day": "sunset"},
]


def _get_product_by_name(product_name: str) -> dict:
    """Find a product by its hyphenated name."""
    for product in PRODUCTS:
        if product["name"] == product_name:
            return product
    return None


def _generate_campaign_name(product_name: str, store_name: str) -> str:
    """Generate campaign name from product and store.

    Example: "blue-floral-maxi-dress" + "Westfield Century City"
             -> "Blue Floral Maxi Dress - Westfield Century City"
    """
    # Convert hyphenated name to title case
    product_title = product_name.replace("-", " ").title()
    return f"{product_title} - {store_name}"


def _generate_mock_video_metrics(video_id: int, campaign_id: int, days: int = 30) -> list:
    """Generate realistic in-store retail media metrics for an activated video.

    Metrics generated:
    - impressions: Number of ad displays on in-store screens (800-2000/day)
    - dwell_time_seconds: Average seconds viewing (3-8 seconds)
    - circulation: Foot traffic past display location (1500-4000/day)
    - revenue: Revenue for RPI calculation ($30-$120/day)

    RPI (revenue_per_impression) is computed on-the-fly as revenue/impressions.

    Args:
        video_id: The video ID in campaign_videos table
        campaign_id: The campaign ID for location multiplier
        days: Number of days of metrics to generate

    Returns:
        List of metric dictionaries
    """
    metrics = []
    today = datetime.now().date()

    # Campaign-specific multipliers (some stores perform better)
    campaign_multipliers = {
        1: 1.2,   # Los Angeles flagship store
        2: 0.9,   # NYC boutique
        3: 1.0,   # Chicago baseline
        4: 0.7,   # Smaller market
    }
    multiplier = campaign_multipliers.get(campaign_id, 1.0)

    # Base metrics for in-store retail
    base_impressions = int(random.randint(800, 2000) * multiplier)
    base_circulation = int(base_impressions * random.uniform(1.5, 2.5))

    for day_offset in range(days):
        date = today - timedelta(days=day_offset)

        # Weekend patterns (more shoppers on weekends)
        day_of_week = date.weekday()
        weekend_boost = 1.4 if day_of_week >= 5 else 1.0

        # Daily variation
        daily_variation = random.uniform(0.85, 1.15)

        # Calculate metrics
        impressions = int(base_impressions * weekend_boost * daily_variation)
        circulation = int(base_circulation * weekend_boost * random.uniform(0.9, 1.1))

        # Dwell time: 3-8 seconds, weekend shoppers browse longer
        base_dwell = random.uniform(3.0, 8.0)
        weekend_dwell_boost = 1.2 if day_of_week >= 5 else 1.0
        dwell_time = round(min(base_dwell * weekend_dwell_boost, 12.0), 1)

        # Revenue: $0.02-$0.08 per impression for retail media
        revenue_per_impression = random.uniform(0.02, 0.08) * multiplier
        revenue = round(impressions * revenue_per_impression, 2)

        metrics.append({
            "video_id": video_id,
            "metric_date": date.isoformat(),
            "impressions": impressions,
            "dwell_time_seconds": dwell_time,
            "circulation": circulation,
            "revenue": revenue
        })

    return metrics


def populate_mock_data() -> dict:
    """Populate the database with mock data using NEW schema.

    Creates:
    - 22 products (from products_data.py)
    - 4 product-centric campaigns
    - 1 activated video per campaign
    - 30 days of metrics per activated video

    IMPORTANT: Skips if data already exists (safe to call multiple times).

    Returns:
        Dictionary with counts of created records
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Check if data already exists - check BOTH old and new tables
    cursor.execute("SELECT COUNT(*) FROM campaigns")
    campaign_count = cursor.fetchone()[0]

    if campaign_count > 0:
        conn.close()
        return {"status": "skipped", "message": "Mock data already exists"}

    products_created = 0
    campaigns_created = 0
    videos_created = 0
    metrics_created = 0

    # Step 1: Insert all 22 products
    # Use INSERT OR IGNORE to handle multi-process race conditions (Agent Engine)
    for product in PRODUCTS:
        cursor.execute('''
            INSERT OR IGNORE INTO products (name, category, style, color, fabric, details, occasion, image_filename, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product["name"],
            product["category"],
            product.get("style", ""),
            product.get("color", ""),
            product.get("fabric", ""),
            product.get("details", ""),
            product.get("occasion", ""),
            product["image_filename"],
            json.dumps(product)
        ))
        products_created += 1

    # Step 2: Create product-centric campaigns
    for i, camp_data in enumerate(MOCK_CAMPAIGNS):
        # Find the product
        product = _get_product_by_name(camp_data["product_name"])
        if not product:
            continue

        # Get the product ID (1-indexed based on insertion order)
        cursor.execute("SELECT id FROM products WHERE name = ?", (product["name"],))
        product_row = cursor.fetchone()
        if not product_row:
            continue
        product_id = product_row[0]

        # Generate campaign name
        campaign_name = _generate_campaign_name(product["name"], camp_data["store_name"])

        # Insert campaign with product_id and store_name
        # Use INSERT OR IGNORE for multi-process safety
        cursor.execute('''
            INSERT OR IGNORE INTO campaigns (name, description, product_id, store_name, city, state, category, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            campaign_name,
            f"Campaign for {product['name']} at {camp_data['store_name']}",
            product_id,
            camp_data["store_name"],
            camp_data["city"],
            camp_data["state"],
            camp_data["category"],
            camp_data["status"]
        ))

        # Fetch the actual campaign_id (lastrowid is unreliable with INSERT OR IGNORE)
        cursor.execute("SELECT id FROM campaigns WHERE name = ?", (campaign_name,))
        campaign_row = cursor.fetchone()
        if not campaign_row:
            continue
        campaign_id = campaign_row[0]
        campaigns_created += 1

        # Step 3: Create activated videos using REAL GCS video files
        if camp_data["status"] == "active":
            product_name = product["name"]
            real_video_list = REAL_VIDEOS.get(product_name, [])

            # If no real videos exist for this product, create one placeholder
            if not real_video_list:
                variation = MOCK_VARIATIONS[i % len(MOCK_VARIATIONS)]
                variation_name = f"{variation['model_ethnicity']}-{variation['setting']}-{variation['time_of_day']}"
                date_str = datetime.now().strftime("%m%d%y")
                real_video_list = [{
                    "filename": f"{product_name}-{date_str}-{variation_name}.mp4",
                    "thumbnail": f"{product_name}-{date_str}-{variation_name}-thumbnail.png",
                    "variation": variation,
                }]

            # Insert ALL real videos for this campaign
            for video_data in real_video_list:
                variation = video_data["variation"]
                variation_name = f"{variation['model_ethnicity']}-{variation['setting']}-{variation['mood']}"

                cursor.execute('''
                    INSERT OR IGNORE INTO campaign_videos
                    (campaign_id, product_id, video_filename, thumbnail_path,
                     scene_prompt, video_prompt, pipeline_type,
                     variation_name, variation_params, duration_seconds, aspect_ratio,
                     status, activated_at, activated_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    campaign_id,
                    product_id,
                    video_data["filename"],
                    video_data["thumbnail"],
                    f"Scene: {variation['model_ethnicity']} model wearing {product_name} in {variation['setting']}",
                    f"Cinematic video of model in {product_name}, {variation['mood']} mood",
                    "two-stage",
                    variation_name,
                    json.dumps(variation),
                    8,
                    "9:16",
                    "activated",  # Pre-activated for demo
                    datetime.now().isoformat(),
                    "mock_data"
                ))

                # Fetch the actual video_id (lastrowid is unreliable with INSERT OR IGNORE)
                cursor.execute("SELECT id FROM campaign_videos WHERE video_filename = ?",
                              (video_data["filename"],))
                video_row = cursor.fetchone()
                if not video_row:
                    continue
                video_id = video_row[0]
                videos_created += 1

                # Step 4: Generate metrics for each activated video
                metrics = _generate_mock_video_metrics(video_id, campaign_id, days=30)
                for metric in metrics:
                    cursor.execute('''
                        INSERT OR IGNORE INTO video_metrics
                        (video_id, metric_date, impressions, dwell_time_seconds, circulation, revenue)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        metric["video_id"],
                        metric["metric_date"],
                        metric["impressions"],
                        metric["dwell_time_seconds"],
                        metric["circulation"],
                        metric["revenue"]
                    ))
                    metrics_created += 1

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "products_created": products_created,
        "campaigns_created": campaigns_created,
        "videos_created": videos_created,
        "metrics_created": metrics_created
    }
