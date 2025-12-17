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

"""Mock data population for the Ad Campaign Agent demo."""

import json
import random
from datetime import datetime, timedelta
from .db import get_connection


def generate_mock_video_properties(image_metadata: dict, campaign_name: str) -> dict:
    """Generate mock video properties based on image metadata.

    Args:
        image_metadata: The image metadata dictionary
        campaign_name: The campaign name for context

    Returns:
        Dictionary of mock video properties
    """
    # Map moods from image metadata to VideoProperties enum values
    mood_mapping = {
        "dreamy, romantic, aspirational": "romantic",
        "elegant, sophisticated, glamorous": "sophisticated",
        "bold, modern, confident": "bold",
        "confident, professional, chic": "sophisticated",
        "playful, feminine, cosmopolitan": "playful",
        "sophisticated, minimalist, polished": "elegant",
        "cozy, intellectual, warm": "warm",
    }

    raw_mood = image_metadata.get("mood", "elegant")
    mood = mood_mapping.get(raw_mood, "elegant")

    # Determine energy level based on movement description
    movement = image_metadata.get("movement", "")
    if "confidently" in movement or "dynamically" in movement or "strides" in movement:
        energy_level = "dynamic"
    elif "gracefully" in movement or "gently" in movement or "subtly" in movement:
        energy_level = "moderate"
    elif "twirls" in movement:
        energy_level = "dynamic"
    else:
        energy_level = "moderate"

    # Determine camera movement based on camera_style
    camera_style = image_metadata.get("camera_style", "")
    if "circles" in camera_style or "orbits" in camera_style:
        camera_movement = "orbit"
    elif "pans" in camera_style:
        camera_movement = "pan"
    elif "tracks" in camera_style or "follows" in camera_style:
        camera_movement = "track"
    elif "zooms" in camera_style:
        camera_movement = "slow_zoom"
    else:
        camera_movement = "orbit"

    # Determine setting type from setting_description
    setting_desc = image_metadata.get("setting_description", "").lower()
    if "studio" in setting_desc:
        setting_type = "studio"
        lighting_style = "studio"
    elif "outdoor" in setting_desc or "meadow" in setting_desc or "field" in setting_desc:
        setting_type = "outdoor"
        lighting_style = "natural"
    elif "urban" in setting_desc or "street" in setting_desc or "city" in setting_desc:
        setting_type = "urban"
        lighting_style = "natural"
    elif "night" in setting_desc:
        setting_type = "urban"
        lighting_style = "dramatic"
    else:
        setting_type = "studio"
        lighting_style = "studio"

    # Determine time of day
    if "golden hour" in setting_desc or "sun-drenched" in setting_desc or "sunny" in setting_desc:
        time_of_day = "golden_hour"
    elif "night" in setting_desc:
        time_of_day = "night"
    else:
        time_of_day = "day"

    # Color temperature based on mood
    if mood in ["warm", "romantic"]:
        color_temperature = "warm"
    elif mood in ["bold", "sophisticated"]:
        color_temperature = "neutral"
    else:
        color_temperature = "neutral"

    # Determine warmth
    has_warmth = mood in ["warm", "romantic", "playful"] or "warm" in setting_desc.lower()

    # Extract colors from clothing description
    clothing_desc = image_metadata.get("clothing_description", "").lower()
    dominant_colors = []
    color_keywords = ["red", "blue", "green", "pink", "white", "beige", "olive", "black", "gold"]
    for color in color_keywords:
        if color in clothing_desc:
            dominant_colors.append(color)
    if not dominant_colors:
        dominant_colors = ["neutral"]

    # Build style tags
    style_tags = ["fashion", "professional"]
    if "Summer" in campaign_name:
        style_tags.extend(["summer", "breezy", "casual"])
    elif "Evening" in campaign_name or "Formal" in campaign_name:
        style_tags.extend(["formal", "evening", "elegant"])
    elif "Professional" in campaign_name:
        style_tags.extend(["business", "professional", "chic"])
    elif "Fall" in campaign_name:
        style_tags.extend(["autumn", "cozy", "layering"])

    return {
        "mood": mood,
        "mood_intensity": round(random.uniform(0.6, 0.9), 2),
        "has_warmth": has_warmth,
        "visual_style": "cinematic",
        "camera_movement": camera_movement,
        "lighting_style": lighting_style,
        "energy_level": energy_level,
        "movement_amount": round(random.uniform(0.4, 0.7), 2),
        "color_temperature": color_temperature,
        "dominant_colors": dominant_colors,
        "color_saturation": round(random.uniform(0.6, 0.8), 2),
        "subject_count": 1,
        "garment_visibility": round(random.uniform(0.7, 0.9), 2),
        "has_multiple_outfits": False,
        "audio_type": "none",
        "has_dialogue": False,
        "music_tempo": None,
        "audio_mood": None,
        "style_tags": style_tags,
        "quality_score": round(random.uniform(0.7, 0.9), 2),
        "setting_type": setting_type,
        "time_of_day": time_of_day,
        "background_complexity": round(random.uniform(0.2, 0.5), 2),
        "aspect_ratio": "9:16",
        "has_text_overlays": False,
        "has_brand_elements": False
    }

# Pre-defined campaigns matching the seed images
MOCK_CAMPAIGNS = [
    {
        "name": "Summer Blooms 2025",
        "description": "Light and breezy summer dresses for the fashion-forward woman",
        "category": "summer",
        "city": "Los Angeles",
        "state": "CA",
        "status": "active",
        "images": [
            {
                "filename": "dress_summer_dress_004.jpg",
                "metadata": {
                    "model_description": "a woman with blonde hair",
                    "clothing_description": "a flowing floral wrap dress in pink and white",
                    "setting_description": "In a sun-drenched meadow with wildflowers",
                    "garment_type": "summer dress",
                    "movement": "billows gracefully in the breeze",
                    "camera_style": "slowly pans around",
                    "key_feature": "vibrant floral pattern against golden hour light",
                    "mood": "dreamy, romantic, aspirational"
                }
            }
        ]
    },
    {
        "name": "Evening Elegance Collection",
        "description": "Sophisticated formal wear for special occasions",
        "category": "formal",
        "city": "New York",
        "state": "NY",
        "status": "active",
        "images": [
            {
                "filename": "dress_formal_dress_002.jpg",
                "metadata": {
                    "model_description": "a woman with red hair",
                    "clothing_description": "a striking red floral fitted gown",
                    "setting_description": "In an elegant studio with soft lighting",
                    "garment_type": "formal gown",
                    "movement": "poses elegantly with subtle movements",
                    "camera_style": "smoothly circles",
                    "key_feature": "intricate red floral pattern and form-fitting silhouette",
                    "mood": "elegant, sophisticated, glamorous"
                }
            },
            {
                "filename": "dress_formal_dress_003.jpg",
                "metadata": {
                    "model_description": "a woman with dark hair",
                    "clothing_description": "an olive green strapless bandage dress",
                    "setting_description": "Under city lights at night with an urban backdrop",
                    "garment_type": "bandage dress",
                    "movement": "walks confidently through the scene",
                    "camera_style": "follows dynamically",
                    "key_feature": "sleek bandage construction and bold color",
                    "mood": "bold, modern, confident"
                }
            }
        ]
    },
    {
        "name": "Urban Professional",
        "description": "Contemporary business casual for the modern professional",
        "category": "professional",
        "city": "Chicago",
        "state": "IL",
        "status": "active",
        "images": [
            {
                "filename": "top_blouse_002.jpg",
                "metadata": {
                    "model_description": "a stylish woman wearing sunglasses",
                    "clothing_description": "a crisp white classic button-down shirt",
                    "setting_description": "On a sunny urban street with modern architecture",
                    "garment_type": "classic blouse",
                    "movement": "strides confidently down the street",
                    "camera_style": "tracks alongside",
                    "key_feature": "clean lines and timeless white fabric",
                    "mood": "confident, professional, chic"
                }
            },
            {
                "filename": "top_blouse_003.jpg",
                "metadata": {
                    "model_description": "a woman with brunette hair",
                    "clothing_description": "a light blue cinched waist blouse",
                    "setting_description": "In a charming European city square",
                    "garment_type": "fitted blouse",
                    "movement": "twirls gently to show the silhouette",
                    "camera_style": "orbits gracefully",
                    "key_feature": "flattering cinched waist and soft blue color",
                    "mood": "playful, feminine, cosmopolitan"
                }
            },
            {
                "filename": "top_blouse_004.jpg",
                "metadata": {
                    "model_description": "a model with a minimalist aesthetic",
                    "clothing_description": "a beige oversized blazer",
                    "setting_description": "In a clean, minimalist studio space",
                    "garment_type": "oversized blazer",
                    "movement": "adjusts the blazer with subtle gestures",
                    "camera_style": "slowly zooms in",
                    "key_feature": "luxurious oversized fit and neutral beige tone",
                    "mood": "sophisticated, minimalist, polished"
                }
            }
        ]
    },
    {
        "name": "Fall Essentials",
        "description": "Cozy knits and layering pieces for the autumn season",
        "category": "essentials",
        "city": "Seattle",
        "state": "WA",
        "status": "draft",
        "images": [
            {
                "filename": "top_sweater_003.jpg",
                "metadata": {
                    "model_description": "a woman wearing glasses with an intellectual look",
                    "clothing_description": "a beige ribbed turtleneck sweater",
                    "setting_description": "In a cozy studio with warm lighting",
                    "garment_type": "turtleneck sweater",
                    "movement": "adjusts glasses while showing the sweater texture",
                    "camera_style": "slowly pulls back",
                    "key_feature": "rich ribbed texture and warm neutral color",
                    "mood": "cozy, intellectual, warm"
                }
            }
        ]
    }
]


def generate_mock_metrics(campaign_id: int, ad_id: int, days: int = 90) -> list:
    """Generate realistic-looking mock metrics for a campaign.

    Args:
        campaign_id: The campaign ID
        ad_id: The ad ID (can be None for campaign-level metrics)
        days: Number of days of metrics to generate

    Returns:
        List of metric dictionaries
    """
    metrics = []
    today = datetime.now().date()

    # Base values with campaign-specific multipliers
    campaign_multipliers = {
        1: 1.2,   # Summer Blooms - best performer
        2: 0.9,   # Evening Elegance
        3: 1.0,   # Urban Professional
        4: 0.7,   # Fall Essentials (draft, lower metrics)
    }
    multiplier = campaign_multipliers.get(campaign_id, 1.0)

    base_impressions = random.randint(15000, 35000) * multiplier

    for day_offset in range(days):
        date = today - timedelta(days=day_offset)

        # Add some weekly patterns (higher on weekends)
        day_of_week = date.weekday()
        weekend_boost = 1.3 if day_of_week >= 5 else 1.0

        # Add trend (slight increase over time)
        trend_factor = 1 + (day_offset * 0.002)

        # Add random variation
        daily_variation = random.uniform(0.8, 1.2)

        impressions = int(base_impressions * weekend_boost * daily_variation / trend_factor)
        views = int(impressions * random.uniform(0.25, 0.40))
        clicks = int(views * random.uniform(0.02, 0.05))

        # Revenue: higher for better performing campaigns
        revenue_per_impression = random.uniform(0.02, 0.06) * multiplier
        revenue = round(impressions * revenue_per_impression, 2)

        cost_per_impression = round(revenue / impressions if impressions > 0 else 0, 4)
        engagement_rate = round((clicks / views * 100) if views > 0 else 0, 2)

        metrics.append({
            "campaign_id": campaign_id,
            "ad_id": ad_id,
            "date": date.isoformat(),
            "impressions": impressions,
            "views": views,
            "clicks": clicks,
            "revenue": revenue,
            "cost_per_impression": cost_per_impression,
            "engagement_rate": engagement_rate
        })

    return metrics


def populate_mock_data() -> dict:
    """Populate the database with mock campaign data.

    Creates 4 campaigns with seed images and 90 days of mock metrics each.

    Returns:
        Dictionary with counts of created records
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM campaigns")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return {"status": "skipped", "message": "Mock data already exists"}

    campaigns_created = 0
    images_created = 0
    ads_created = 0
    metrics_created = 0

    for campaign_data in MOCK_CAMPAIGNS:
        # Insert campaign
        cursor.execute('''
            INSERT INTO campaigns (name, description, category, city, state, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            campaign_data["name"],
            campaign_data["description"],
            campaign_data["category"],
            campaign_data["city"],
            campaign_data["state"],
            campaign_data["status"]
        ))
        campaign_id = cursor.lastrowid
        campaigns_created += 1

        # Insert images for this campaign
        for image_data in campaign_data["images"]:
            cursor.execute('''
                INSERT INTO campaign_images (campaign_id, image_path, image_type, metadata)
                VALUES (?, ?, ?, ?)
            ''', (
                campaign_id,
                image_data["filename"],
                "seed",
                json.dumps(image_data["metadata"])
            ))
            image_id = cursor.lastrowid
            images_created += 1

            # Create a mock ad for active campaigns
            if campaign_data["status"] == "active":
                # Generate mock video properties based on image metadata
                video_properties = generate_mock_video_properties(
                    image_data["metadata"],
                    campaign_data["name"]
                )

                cursor.execute('''
                    INSERT INTO campaign_ads (campaign_id, image_id, video_path, prompt_used, status, video_properties)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    campaign_id,
                    image_id,
                    f"generated/campaign_{campaign_id}_ad_{image_id}.mp4",
                    f"Fashion video featuring {image_data['metadata'].get('clothing_description', 'elegant clothing')}",
                    "completed",
                    json.dumps(video_properties)
                ))
                ad_id = cursor.lastrowid
                ads_created += 1

                # Generate metrics for this ad
                metrics = generate_mock_metrics(campaign_id, ad_id, days=90)
                for metric in metrics:
                    cursor.execute('''
                        INSERT INTO campaign_metrics
                        (campaign_id, ad_id, date, impressions, views, clicks, revenue, cost_per_impression, engagement_rate)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        metric["campaign_id"],
                        metric["ad_id"],
                        metric["date"],
                        metric["impressions"],
                        metric["views"],
                        metric["clicks"],
                        metric["revenue"],
                        metric["cost_per_impression"],
                        metric["engagement_rate"]
                    ))
                    metrics_created += 1

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "campaigns_created": campaigns_created,
        "images_created": images_created,
        "ads_created": ads_created,
        "metrics_created": metrics_created
    }
