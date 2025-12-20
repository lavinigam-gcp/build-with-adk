#!/usr/bin/env python3
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

"""Creative Director Video Ad Generator.

This script acts as a creative marketing director to generate multiple video ad
variations from a single product image. The product article stays consistent
while the context varies: different models, settings, moods, camera angles,
props, and more.

The goal is to create diverse, compelling video ads that can be A/B tested
to find what resonates with different audiences.

Usage:
    # Generate variations for a product
    python -m scripts.creative_video_generator \\
        --product scripts/products/emerald-satin-slip-dress.png \\
        --variations scripts/creative_briefs/slip-dress-variations.json

    # Generate with preset creative brief
    python -m scripts.creative_video_generator \\
        --product scripts/products/black-leather-moto-jacket.png \\
        --preset diversity

    # List available presets
    python -m scripts.creative_video_generator --list-presets

Output:
    Videos are saved to scripts/products/videos/ with descriptive names:
    {product-name}-{MMDDYY}-{variation-key}.mp4
"""

import argparse
import asyncio
import io
import json
import os
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

from PIL import Image as PILImage
from google import genai
from google.genai import types

# Script directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_DIR = os.path.join(SCRIPT_DIR, "products")
VIDEOS_DIR = os.path.join(PRODUCTS_DIR, "videos")
BRIEFS_DIR = os.path.join(SCRIPT_DIR, "creative_briefs")

# Model configuration
VIDEO_MODEL = "veo-3.1-generate-preview"
IMAGE_ANALYSIS_MODEL = "gemini-2.0-flash"
SCENE_IMAGE_MODEL = "gemini-2.0-flash-exp"  # For generating scene-ready first frames
ASPECT_RATIO = "9:16"
DURATION_SECONDS = 8
RESOLUTION = "1080p"

# Rate limiting for Veo (video generation takes 2-5 minutes)
VIDEO_POLL_INTERVAL = 20  # seconds
VIDEO_MAX_WAIT = 600  # 10 minutes max


# =============================================================================
# Creative Variation Dimensions
# =============================================================================

@dataclass
class CreativeVariation:
    """Defines a single creative variation for video generation."""
    name: str  # Unique variation identifier (e.g., "beach-romantic-asian")

    # Model characteristics
    model_ethnicity: str = "diverse"  # asian, european, african, latina, middle-eastern, south-asian, diverse
    model_description: str = ""  # Override for specific model description

    # Setting/Location
    setting: str = "studio"  # beach, urban, cafe, rooftop, studio, garden, street, luxury-interior, nature
    location_detail: str = ""  # Additional location specifics

    # Time and Season
    season: str = "neutral"  # summer, winter, fall, spring, neutral
    time_of_day: str = "day"  # golden-hour, sunrise, day, sunset, dusk, night
    weather: str = "clear"  # clear, cloudy, rainy, snowy, foggy

    # Mood and Atmosphere
    mood: str = "elegant"  # romantic, energetic, sophisticated, playful, bold, mysterious, serene, confident
    energy: str = "moderate"  # calm, moderate, dynamic, high-energy

    # Camera and Movement
    camera_movement: str = "orbit"  # orbit, pan, dolly, static, tracking, crane, handheld
    camera_angle: str = "eye-level"  # low-angle, eye-level, high-angle, dutch-angle

    # Props and Companions
    props: List[str] = field(default_factory=list)  # dog, cat, coffee, umbrella, flowers, sunglasses, bag

    # Model Activity
    activity: str = "walking"  # walking, standing, sitting, dancing, spinning, posing, running

    # Lighting
    lighting: str = "natural"  # natural, studio, dramatic, soft, golden, neon, moody

    # Visual Style
    visual_style: str = "cinematic"  # cinematic, editorial, commercial, artistic, documentary
    color_grading: str = "neutral"  # warm, cool, neutral, vintage, high-contrast


# =============================================================================
# Creative Brief Presets
# =============================================================================

PRESET_BRIEFS = {
    "diversity": {
        "description": "Model diversity showcase - same product, different representations",
        "variations": [
            CreativeVariation(
                name="asian-urban-confident",
                model_ethnicity="asian",
                setting="urban",
                mood="confident",
                lighting="natural",
                activity="walking",
                time_of_day="golden-hour"
            ),
            CreativeVariation(
                name="european-studio-elegant",
                model_ethnicity="european",
                setting="studio",
                mood="elegant",
                lighting="studio",
                activity="posing",
                visual_style="editorial"
            ),
            CreativeVariation(
                name="african-rooftop-bold",
                model_ethnicity="african",
                setting="rooftop",
                mood="bold",
                lighting="golden",
                time_of_day="sunset",
                activity="standing"
            ),
            CreativeVariation(
                name="latina-beach-playful",
                model_ethnicity="latina",
                setting="beach",
                mood="playful",
                lighting="natural",
                season="summer",
                activity="walking"
            ),
            CreativeVariation(
                name="south-asian-garden-romantic",
                model_ethnicity="south-asian",
                setting="garden",
                mood="romantic",
                lighting="soft",
                time_of_day="golden-hour",
                props=["flowers"]
            ),
        ]
    },
    "settings": {
        "description": "Location variety - same product in different environments",
        "variations": [
            CreativeVariation(
                name="beach-summer",
                setting="beach",
                season="summer",
                mood="playful",
                lighting="natural",
                time_of_day="day"
            ),
            CreativeVariation(
                name="urban-night",
                setting="urban",
                time_of_day="night",
                mood="bold",
                lighting="neon",
                visual_style="cinematic"
            ),
            CreativeVariation(
                name="cafe-morning",
                setting="cafe",
                time_of_day="morning",
                mood="sophisticated",
                props=["coffee"],
                activity="sitting"
            ),
            CreativeVariation(
                name="luxury-interior",
                setting="luxury-interior",
                mood="elegant",
                lighting="soft",
                visual_style="editorial"
            ),
            CreativeVariation(
                name="nature-fall",
                setting="nature",
                season="fall",
                mood="serene",
                lighting="golden",
                time_of_day="golden-hour"
            ),
        ]
    },
    "moods": {
        "description": "Emotional variety - same product, different feelings",
        "variations": [
            CreativeVariation(
                name="romantic-soft",
                mood="romantic",
                lighting="soft",
                setting="garden",
                camera_movement="slow-pan",
                color_grading="warm"
            ),
            CreativeVariation(
                name="energetic-dynamic",
                mood="energetic",
                energy="high-energy",
                setting="urban",
                camera_movement="tracking",
                activity="walking"
            ),
            CreativeVariation(
                name="mysterious-moody",
                mood="mysterious",
                lighting="moody",
                time_of_day="dusk",
                color_grading="cool",
                visual_style="cinematic"
            ),
            CreativeVariation(
                name="playful-fun",
                mood="playful",
                energy="dynamic",
                setting="beach",
                activity="dancing",
                props=["sunglasses"]
            ),
            CreativeVariation(
                name="confident-bold",
                mood="confident",
                setting="rooftop",
                lighting="dramatic",
                camera_angle="low-angle",
                visual_style="editorial"
            ),
        ]
    },
    "props": {
        "description": "Lifestyle props - add context and storytelling",
        "variations": [
            CreativeVariation(
                name="with-dog",
                props=["dog"],
                setting="park",
                mood="playful",
                activity="walking"
            ),
            CreativeVariation(
                name="with-cat",
                props=["cat"],
                setting="luxury-interior",
                mood="serene",
                activity="sitting"
            ),
            CreativeVariation(
                name="coffee-morning",
                props=["coffee"],
                setting="cafe",
                time_of_day="morning",
                mood="sophisticated"
            ),
            CreativeVariation(
                name="umbrella-rain",
                props=["umbrella"],
                weather="rainy",
                setting="urban",
                mood="romantic"
            ),
            CreativeVariation(
                name="flowers-romantic",
                props=["flowers"],
                setting="garden",
                mood="romantic",
                lighting="soft"
            ),
        ]
    },
    "seasons": {
        "description": "Seasonal variety - same product across seasons",
        "variations": [
            CreativeVariation(
                name="summer-beach",
                season="summer",
                setting="beach",
                lighting="natural",
                mood="playful"
            ),
            CreativeVariation(
                name="fall-nature",
                season="fall",
                setting="nature",
                lighting="golden",
                mood="serene",
                color_grading="warm"
            ),
            CreativeVariation(
                name="winter-snowy",
                season="winter",
                weather="snowy",
                setting="urban",
                mood="elegant",
                lighting="soft"
            ),
            CreativeVariation(
                name="spring-garden",
                season="spring",
                setting="garden",
                props=["flowers"],
                mood="romantic",
                lighting="natural"
            ),
        ]
    },
    "camera-styles": {
        "description": "Camera technique variety - different filming approaches",
        "variations": [
            CreativeVariation(
                name="orbit-360",
                camera_movement="orbit",
                camera_angle="eye-level",
                setting="studio",
                lighting="studio"
            ),
            CreativeVariation(
                name="dolly-dramatic",
                camera_movement="dolly",
                camera_angle="low-angle",
                lighting="dramatic",
                visual_style="cinematic"
            ),
            CreativeVariation(
                name="tracking-dynamic",
                camera_movement="tracking",
                activity="walking",
                energy="dynamic",
                setting="urban"
            ),
            CreativeVariation(
                name="static-editorial",
                camera_movement="static",
                visual_style="editorial",
                lighting="studio",
                mood="confident"
            ),
            CreativeVariation(
                name="crane-epic",
                camera_movement="crane",
                camera_angle="high-angle",
                setting="rooftop",
                time_of_day="sunset"
            ),
        ]
    },
    "full-matrix": {
        "description": "Complete creative matrix - comprehensive variation coverage",
        "variations": [
            # Diversity + Settings combinations
            CreativeVariation(name="asian-urban-night", model_ethnicity="asian", setting="urban", time_of_day="night", mood="bold"),
            CreativeVariation(name="european-beach-summer", model_ethnicity="european", setting="beach", season="summer", mood="playful"),
            CreativeVariation(name="african-studio-elegant", model_ethnicity="african", setting="studio", mood="elegant", visual_style="editorial"),
            CreativeVariation(name="latina-cafe-sophisticated", model_ethnicity="latina", setting="cafe", mood="sophisticated", props=["coffee"]),
            CreativeVariation(name="south-asian-garden-romantic", model_ethnicity="south-asian", setting="garden", mood="romantic", lighting="soft"),
            # Mood + Activity combinations
            CreativeVariation(name="confident-walking-urban", mood="confident", activity="walking", setting="urban", camera_movement="tracking"),
            CreativeVariation(name="playful-dancing-beach", mood="playful", activity="dancing", setting="beach", energy="high-energy"),
            CreativeVariation(name="serene-sitting-nature", mood="serene", activity="sitting", setting="nature", lighting="golden"),
            CreativeVariation(name="mysterious-posing-night", mood="mysterious", activity="posing", time_of_day="night", lighting="moody"),
            CreativeVariation(name="romantic-spinning-garden", mood="romantic", activity="spinning", setting="garden", camera_movement="orbit"),
        ]
    }
}


# =============================================================================
# Prompt Building
# =============================================================================

def analyze_product_image(image_path: str) -> dict:
    """Analyze product image to extract metadata for prompt building.

    Args:
        image_path: Path to the product image

    Returns:
        Dictionary with product metadata
    """
    print(f"Analyzing product image: {image_path}")

    # Read image
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")

    prompt = """Analyze this fashion product image and extract metadata in JSON format:

{
    "garment_type": "Type of garment (e.g., 'slip dress', 'blazer', 'jeans')",
    "garment_description": "Detailed description of the garment",
    "color": "Primary color(s) of the garment",
    "fabric": "Apparent fabric type",
    "style": "Style category (e.g., 'formal', 'casual', 'bohemian')",
    "key_features": ["list", "of", "distinctive", "features"],
    "suggested_occasions": ["list", "of", "suitable", "occasions"],
    "suggested_pairings": ["list", "of", "complementary", "items"]
}

Respond ONLY with the JSON object."""

    client = genai.Client()
    response = client.models.generate_content(
        model=IMAGE_ANALYSIS_MODEL,
        contents=[image_part, prompt]
    )

    response_text = response.text.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()

    try:
        metadata = json.loads(response_text)
    except json.JSONDecodeError:
        metadata = {
            "garment_type": "fashion item",
            "garment_description": "elegant clothing piece",
            "color": "neutral",
            "fabric": "quality fabric",
            "style": "versatile",
            "key_features": [],
            "suggested_occasions": [],
            "suggested_pairings": []
        }

    print(f"  Garment: {metadata.get('garment_type', 'unknown')}")
    print(f"  Color: {metadata.get('color', 'unknown')}")
    print(f"  Style: {metadata.get('style', 'unknown')}")

    return metadata


def build_creative_prompt(
    product_metadata: dict,
    variation: CreativeVariation
) -> str:
    """Build a compelling video prompt from product metadata and creative variation.

    This is the core creative director logic - translating product + variation
    into a cinematic prompt that will produce compelling video ads.

    Args:
        product_metadata: Analyzed product metadata
        variation: Creative variation parameters

    Returns:
        Optimized video generation prompt
    """
    # Extract product details
    garment_description = product_metadata.get("garment_description", "")
    garment_type = product_metadata.get("garment_type", "elegant fashion piece")
    color = product_metadata.get("color", "")
    fabric = product_metadata.get("fabric", "")
    key_features = product_metadata.get("key_features", [])

    # Build garment description (prefer full description, avoid duplication)
    if garment_description:
        # Use full description directly (it usually includes color/fabric already)
        garment_desc = garment_description.strip().rstrip(".,;")
    else:
        # Build from components
        garment_desc = f"{color} {fabric} {garment_type}".strip().rstrip(".,;")

    if not garment_desc:
        garment_desc = "elegant fashion piece"

    # Build model description based on ethnicity
    ethnicity_map = {
        "asian": "a graceful Asian woman with sleek dark hair",
        "european": "a striking European woman with refined features",
        "african": "a stunning African woman with radiant skin",
        "latina": "a vibrant Latina woman with warm features",
        "middle-eastern": "an elegant Middle Eastern woman with captivating eyes",
        "south-asian": "a beautiful South Asian woman with flowing dark hair",
        "diverse": "a beautiful woman",
    }
    model_desc = variation.model_description or ethnicity_map.get(variation.model_ethnicity, "a beautiful woman")

    # Build setting description
    setting_map = {
        "beach": "on a pristine sandy beach with gentle waves",
        "urban": "in a stylish urban cityscape",
        "cafe": "at an elegant European-style café",
        "rooftop": "on a luxurious rooftop terrace overlooking the city",
        "studio": "in a minimalist professional studio",
        "garden": "in a lush, blooming garden",
        "street": "on a charming cobblestone street",
        "luxury-interior": "in an opulent luxury interior",
        "nature": "in a serene natural landscape",
        "park": "in a beautiful sunlit park",
    }
    setting_desc = setting_map.get(variation.setting, f"in a {variation.setting} setting")
    if variation.location_detail:
        setting_desc += f" {variation.location_detail}"

    # Add seasonal/weather context
    season_additions = {
        "summer": "with warm summer sunlight",
        "winter": "with crisp winter atmosphere",
        "fall": "surrounded by autumn colors",
        "spring": "with fresh spring blossoms",
    }
    if variation.season in season_additions:
        setting_desc += f" {season_additions[variation.season]}"

    if variation.weather == "rainy":
        setting_desc += " with gentle rain falling"
    elif variation.weather == "snowy":
        setting_desc += " with soft snow gently falling"

    # Build time of day
    time_map = {
        "golden-hour": "during magical golden hour",
        "sunrise": "at sunrise with soft morning light",
        "day": "in natural daylight",
        "sunset": "at sunset with warm orange hues",
        "dusk": "at dusk with purple twilight",
        "night": "at night with atmospheric city lights",
        "morning": "in soft morning light",
    }
    time_desc = time_map.get(variation.time_of_day, "")

    # Build mood/atmosphere
    mood_map = {
        "romantic": "with romantic, dreamy atmosphere",
        "energetic": "with vibrant, dynamic energy",
        "sophisticated": "with sophisticated elegance",
        "playful": "with playful, joyful spirit",
        "bold": "with bold, confident presence",
        "mysterious": "with mysterious allure",
        "serene": "with serene, peaceful calm",
        "confident": "with confident, empowered grace",
        "elegant": "with timeless elegance",
    }
    mood_desc = mood_map.get(variation.mood, f"with {variation.mood} atmosphere")

    # Build activity description
    activity_map = {
        "walking": "walking gracefully",
        "standing": "standing confidently",
        "sitting": "seated elegantly",
        "dancing": "moving rhythmically",
        "spinning": "spinning gracefully, letting the fabric flow",
        "posing": "striking elegant poses",
        "running": "moving dynamically",
    }
    activity_desc = activity_map.get(variation.activity, variation.activity)

    # Build camera description
    camera_map = {
        "orbit": "Camera slowly orbits around the subject",
        "pan": "Camera pans smoothly across the scene",
        "dolly": "Camera dollies in dramatically",
        "static": "Camera holds steady with subtle movement",
        "tracking": "Camera tracks alongside the subject",
        "crane": "Camera sweeps with crane-like movement",
        "handheld": "Camera has subtle handheld movement",
        "slow-pan": "Camera pans slowly and deliberately",
    }
    camera_desc = camera_map.get(variation.camera_movement, f"Camera {variation.camera_movement}")

    # Camera angle
    angle_map = {
        "low-angle": "from a powerful low angle",
        "eye-level": "at eye level",
        "high-angle": "from an elevated perspective",
        "dutch-angle": "with dynamic dutch angle",
    }
    angle_desc = angle_map.get(variation.camera_angle, "")
    if angle_desc:
        camera_desc += f" {angle_desc}"

    # Build lighting
    lighting_map = {
        "natural": "Natural lighting",
        "studio": "Professional studio lighting",
        "dramatic": "Dramatic contrast lighting",
        "soft": "Soft, diffused lighting",
        "golden": "Warm golden hour lighting",
        "neon": "Atmospheric neon lighting",
        "moody": "Moody, atmospheric lighting",
    }
    lighting_desc = lighting_map.get(variation.lighting, f"{variation.lighting} lighting")

    # Build props
    props_desc = ""
    if variation.props:
        prop_phrases = {
            "dog": "accompanied by a friendly dog",
            "cat": "with an elegant cat nearby",
            "coffee": "holding a cup of coffee",
            "umbrella": "with a stylish umbrella",
            "flowers": "surrounded by beautiful flowers",
            "sunglasses": "wearing chic sunglasses",
            "bag": "carrying a designer bag",
        }
        prop_parts = [prop_phrases.get(p, f"with {p}") for p in variation.props]
        props_desc = ", ".join(prop_parts)

    # Build visual style
    style_map = {
        "cinematic": "Cinematic",
        "editorial": "High-fashion editorial",
        "commercial": "Polished commercial",
        "artistic": "Artistic",
        "documentary": "Documentary-style",
    }
    style_desc = style_map.get(variation.visual_style, variation.visual_style)

    # Color grading
    grading_map = {
        "warm": "warm color grading",
        "cool": "cool, desaturated tones",
        "neutral": "natural color balance",
        "vintage": "vintage film aesthetic",
        "high-contrast": "high-contrast dramatic look",
    }
    grading_desc = grading_map.get(variation.color_grading, "")

    # Construct the final prompt
    prompt_parts = [
        f"{style_desc} fashion video advertisement featuring {model_desc} wearing a stunning {garment_desc}.",
        f"She is {activity_desc} {setting_desc} {time_desc}.",
    ]

    if props_desc:
        prompt_parts.append(f"She is {props_desc}.")

    if key_features:
        features_text = ", ".join(key_features[:3])
        prompt_parts.append(f"The camera captures the garment's {features_text}.")

    prompt_parts.extend([
        f"{camera_desc}, showcasing the garment's movement and drape.",
        f"{lighting_desc} {mood_desc}.",
    ])

    if grading_desc:
        prompt_parts.append(f"Color grading: {grading_desc}.")

    prompt_parts.append("Professional high-end fashion advertisement. 8 seconds. Vertical 9:16 format.")

    return " ".join(prompt_parts)


def generate_video_filename(
    product_name: str,
    variation: CreativeVariation,
    output_dir: str
) -> str:
    """Generate descriptive video filename following naming convention.

    Format: {product-name}-{MMDDYY}-{variation-name}.mp4

    Args:
        product_name: Base product name
        variation: The creative variation used
        output_dir: Output directory (for checking existing files)

    Returns:
        Filename (without directory path)
    """
    date_str = datetime.now().strftime("%m%d%y")

    # Clean product name
    clean_product = product_name.lower().replace(" ", "-").replace("_", "-")
    while "--" in clean_product:
        clean_product = clean_product.replace("--", "-")
    clean_product = clean_product.strip("-")

    # Clean variation name
    clean_variation = variation.name.lower().replace(" ", "-").replace("_", "-")

    base_filename = f"{clean_product}-{date_str}-{clean_variation}"

    # Check for existing files and add sequence if needed
    filename = base_filename
    sequence = 1
    while os.path.exists(os.path.join(output_dir, f"{filename}.mp4")):
        sequence += 1
        filename = f"{base_filename}-{sequence}"

    return f"{filename}.mp4"


# =============================================================================
# Scene Image Generation (Stage 1)
# =============================================================================

def build_scene_image_prompt(
    product_metadata: dict,
    variation: CreativeVariation
) -> str:
    """Build a prompt for generating a scene-ready first frame image.

    This creates an image of a model wearing the product in the desired setting,
    which will be used as the first frame for video generation.

    Args:
        product_metadata: Analyzed product metadata
        variation: Creative variation parameters

    Returns:
        Optimized image generation prompt
    """
    # Extract product details
    garment_description = product_metadata.get("garment_description", "")
    garment_type = product_metadata.get("garment_type", "elegant fashion piece")
    key_features = product_metadata.get("key_features", [])

    if garment_description:
        garment_desc = garment_description.strip().rstrip(".,;")
    else:
        color = product_metadata.get("color", "")
        fabric = product_metadata.get("fabric", "")
        garment_desc = f"{color} {fabric} {garment_type}".strip().rstrip(".,;")

    if not garment_desc:
        garment_desc = "elegant fashion piece"

    # Build model description
    ethnicity_map = {
        "asian": "a graceful Asian woman with sleek dark hair",
        "european": "a striking European woman with refined features",
        "african": "a stunning African woman with radiant skin",
        "latina": "a vibrant Latina woman with warm features",
        "middle-eastern": "an elegant Middle Eastern woman with captivating eyes",
        "south-asian": "a beautiful South Asian woman with flowing dark hair",
        "diverse": "a beautiful woman",
    }
    model_desc = variation.model_description or ethnicity_map.get(variation.model_ethnicity, "a beautiful woman")

    # Build setting description
    setting_map = {
        "beach": "on a pristine sandy beach with gentle waves in the background",
        "urban": "in a stylish urban cityscape with modern architecture",
        "cafe": "at an elegant European-style café with soft ambient lighting",
        "rooftop": "on a luxurious rooftop terrace overlooking a city skyline",
        "studio": "in a minimalist professional photography studio",
        "garden": "in a lush, blooming garden with vibrant flowers",
        "street": "on a charming cobblestone street in a European city",
        "luxury-interior": "in an opulent luxury interior with elegant furnishings",
        "nature": "in a serene natural landscape with beautiful scenery",
        "park": "in a beautiful sunlit park with trees and greenery",
    }
    setting_desc = setting_map.get(variation.setting, f"in a {variation.setting} setting")

    # Time of day
    time_map = {
        "golden-hour": "during golden hour with warm, soft light",
        "sunrise": "at sunrise with soft pink and orange morning light",
        "day": "in bright natural daylight",
        "sunset": "at sunset with warm orange and purple hues",
        "dusk": "at dusk with purple twilight ambiance",
        "night": "at night with atmospheric city lights and ambient glow",
        "morning": "in soft morning light",
    }
    time_desc = time_map.get(variation.time_of_day, "")

    # Pose/activity for still image
    pose_map = {
        "walking": "mid-stride in an elegant walking pose",
        "standing": "standing confidently with poised posture",
        "sitting": "seated elegantly with graceful posture",
        "dancing": "in a dynamic dance pose with flowing movement",
        "spinning": "with fabric flowing as if mid-spin",
        "posing": "striking an elegant fashion pose",
        "running": "in dynamic motion",
    }
    pose_desc = pose_map.get(variation.activity, "in an elegant pose")

    # Lighting
    lighting_map = {
        "natural": "Natural, soft lighting",
        "studio": "Professional studio lighting with soft shadows",
        "dramatic": "Dramatic contrast lighting with deep shadows",
        "soft": "Soft, diffused ethereal lighting",
        "golden": "Warm golden hour lighting",
        "neon": "Atmospheric neon lighting with colorful accents",
        "moody": "Moody, atmospheric low-key lighting",
    }
    lighting_desc = lighting_map.get(variation.lighting, f"{variation.lighting} lighting")

    # Props
    props_desc = ""
    if variation.props:
        prop_phrases = {
            "dog": "with a friendly dog beside her",
            "cat": "with an elegant cat nearby",
            "coffee": "holding a stylish cup of coffee",
            "umbrella": "holding a chic umbrella",
            "flowers": "surrounded by beautiful fresh flowers",
            "sunglasses": "wearing stylish designer sunglasses",
            "bag": "carrying a luxury designer handbag",
        }
        prop_parts = [prop_phrases.get(p, f"with {p}") for p in variation.props]
        props_desc = ", " + ", ".join(prop_parts)

    # Visual style
    style_map = {
        "cinematic": "Cinematic fashion photography",
        "editorial": "High-fashion editorial photography",
        "commercial": "Polished commercial advertising photography",
        "artistic": "Artistic fashion photography",
        "documentary": "Natural documentary-style photography",
    }
    style_desc = style_map.get(variation.visual_style, "Professional fashion photography")

    # Construct the scene image prompt
    prompt = f"""{style_desc} of {model_desc} wearing a stunning {garment_desc}.

She is {pose_desc} {setting_desc} {time_desc}{props_desc}.

{lighting_desc}. The garment is clearly visible with all its details: {', '.join(key_features[:3]) if key_features else 'fabric texture and construction'}.

REQUIREMENTS:
- Full body or 3/4 shot showing the complete garment
- Model facing camera or slight angle
- Sharp focus on the garment and model
- Professional fashion advertisement quality
- Vertical 9:16 aspect ratio composition
- The scene should look like the perfect first frame of a fashion video ad

Style: Luxury fashion campaign, magazine-quality, aspirational."""

    return prompt


def build_video_animation_prompt(
    product_metadata: dict,
    variation: CreativeVariation
) -> str:
    """Build a prompt focused on animating an existing scene image.

    Since Stage 1 creates the scene, this prompt focuses on movement and animation.

    Args:
        product_metadata: Analyzed product metadata
        variation: Creative variation parameters

    Returns:
        Animation-focused video prompt
    """
    # Activity animation descriptions
    activity_animation = {
        "walking": "The model walks gracefully forward, the garment flowing with each step",
        "standing": "The model shifts weight subtly, the fabric catching the light",
        "sitting": "The model moves gracefully, adjusting position elegantly",
        "dancing": "The model moves rhythmically, the garment swirling beautifully",
        "spinning": "The model spins slowly, the fabric flowing outward dramatically",
        "posing": "The model transitions between elegant poses fluidly",
        "running": "The model moves dynamically, fabric flowing with motion",
    }
    activity_desc = activity_animation.get(variation.activity, "The model moves gracefully")

    # Camera movement
    camera_map = {
        "orbit": "Camera slowly orbits around the model",
        "pan": "Camera pans smoothly across the scene",
        "dolly": "Camera dollies in slowly toward the model",
        "static": "Camera holds steady with subtle breathing movement",
        "tracking": "Camera tracks alongside the model's movement",
        "crane": "Camera sweeps with elegant crane movement",
        "handheld": "Camera has subtle natural handheld movement",
        "slow-pan": "Camera pans very slowly and deliberately",
    }
    camera_desc = camera_map.get(variation.camera_movement, "Camera moves smoothly")

    # Environmental motion
    env_motion = []
    if variation.setting == "beach":
        env_motion.append("waves gently rolling in the background")
    elif variation.setting == "urban":
        env_motion.append("city life flowing in the background")
    elif variation.setting == "garden":
        env_motion.append("flowers swaying gently in the breeze")
    elif variation.setting == "nature":
        env_motion.append("leaves rustling softly")

    if variation.weather == "rainy":
        env_motion.append("rain falling gently")
    elif variation.weather == "snowy":
        env_motion.append("snow falling softly")

    env_desc = ", ".join(env_motion) if env_motion else "subtle ambient movement"

    # Mood/energy
    energy_map = {
        "calm": "slow, graceful, meditative pace",
        "moderate": "smooth, elegant movement",
        "dynamic": "energetic, fluid motion",
        "high-energy": "vibrant, dynamic, fast-paced movement",
    }
    energy_desc = energy_map.get(variation.energy, "elegant movement")

    prompt = f"""{activity_desc}. {camera_desc}, showcasing the garment's movement, drape, and fabric flow.

The scene has {env_desc}. The movement is {energy_desc}.

Focus on:
- The fabric's natural flow and drape as the model moves
- Lighting playing across the garment's surface
- Smooth, professional camera work
- High-end fashion advertisement aesthetic

8 seconds. Vertical 9:16. Cinematic quality. Professional fashion video ad."""

    return prompt


async def generate_scene_image(
    product_image_path: str,
    product_metadata: dict,
    variation: CreativeVariation,
    output_dir: str
) -> tuple[bytes, str]:
    """Generate a scene-ready first frame image using the product as reference.

    Stage 1 of the two-stage pipeline: Creates an image of a model wearing
    the product in the desired setting.

    Args:
        product_image_path: Path to the product catalog image
        product_metadata: Analyzed product metadata
        variation: Creative variation parameters
        output_dir: Directory to save the scene image

    Returns:
        Tuple of (image_bytes, scene_prompt)
    """
    print(f"  Stage 1: Generating scene image...")

    # Build the scene image prompt
    scene_prompt = build_scene_image_prompt(product_metadata, variation)

    # Load product image as reference
    with open(product_image_path, "rb") as f:
        product_image_bytes = f.read()

    product_image_part = types.Part.from_bytes(
        data=product_image_bytes,
        mime_type="image/png"
    )

    # Create the full prompt with product reference
    full_prompt = f"""Using this product image as reference for the EXACT garment design, colors, and details, generate a new fashion photograph:

{scene_prompt}

CRITICAL: The garment in the generated image must match the reference product image EXACTLY - same design, same color, same fabric appearance, same details. Only the model and setting should be different."""

    client = genai.Client()

    response = client.models.generate_content(
        model=SCENE_IMAGE_MODEL,
        contents=[product_image_part, full_prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
        )
    )

    # Extract generated image
    scene_image_bytes = None
    for part in response.parts:
        if part.inline_data:
            scene_image_bytes = part.inline_data.data
            break

    if scene_image_bytes is None:
        raise ValueError("No scene image generated")

    # Save scene image for reference
    product_name = os.path.splitext(os.path.basename(product_image_path))[0]
    scene_filename = f"{product_name}-{variation.name}-scene.png"
    scene_path = os.path.join(output_dir, scene_filename)
    with open(scene_path, "wb") as f:
        f.write(scene_image_bytes)
    print(f"    Scene image saved: {scene_path}")

    return scene_image_bytes, scene_prompt


# =============================================================================
# Video Generation (Stage 2)
# =============================================================================

async def generate_video_ad(
    product_image_path: str,
    product_metadata: dict,
    variation: CreativeVariation,
    output_dir: str,
    save_prompt: bool = True,
    use_two_stage: bool = True
) -> dict:
    """Generate a single video ad using Veo 3.1.

    Uses a two-stage pipeline:
    1. Generate a scene-ready first frame image (model + setting)
    2. Animate that scene image with Veo

    Args:
        product_image_path: Path to the product image
        product_metadata: Analyzed product metadata
        variation: Creative variation to apply
        output_dir: Directory to save the video
        save_prompt: Whether to save the prompt to a text file
        use_two_stage: Use two-stage pipeline (scene image + video)

    Returns:
        Dictionary with generation result
    """
    os.makedirs(output_dir, exist_ok=True)

    product_name = os.path.splitext(os.path.basename(product_image_path))[0]

    print(f"\n{'='*60}")
    print(f"Generating: {variation.name}")
    print(f"{'='*60}")

    try:
        client = genai.Client()
        scene_prompt = None
        video_prompt = None

        if use_two_stage:
            # STAGE 1: Generate scene-ready first frame
            scene_image_bytes, scene_prompt = await generate_scene_image(
                product_image_path=product_image_path,
                product_metadata=product_metadata,
                variation=variation,
                output_dir=output_dir
            )

            # Use scene image for video generation
            image = types.Image(image_bytes=scene_image_bytes, mime_type="image/png")

            # Build animation-focused prompt for Stage 2
            video_prompt = build_video_animation_prompt(product_metadata, variation)
            print(f"  Stage 2: Animating scene...")
            print(f"  Animation prompt: {video_prompt[:200]}...")

        else:
            # Single-stage: Use product image directly (old behavior)
            print(f"Loading product image...")
            with open(product_image_path, "rb") as f:
                image_bytes = f.read()

            with PILImage.open(io.BytesIO(image_bytes)) as im:
                img_format = im.format or "PNG"

            mime_type = f"image/{img_format.lower()}"
            image = types.Image(image_bytes=image_bytes, mime_type=mime_type)

            video_prompt = build_creative_prompt(product_metadata, variation)
            print(f"Prompt preview:\n{video_prompt[:300]}...")

        # Start video generation
        print(f"  Starting Veo 3.1 video generation...")
        operation = client.models.generate_videos(
            model=VIDEO_MODEL,
            prompt=video_prompt,
            image=image,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=DURATION_SECONDS,
            ),
        )

        # Poll for completion
        waited = 0
        while not operation.done:
            if waited >= VIDEO_MAX_WAIT:
                return {
                    "status": "error",
                    "variation": variation.name,
                    "message": f"Video generation timed out after {VIDEO_MAX_WAIT}s"
                }

            print(f"  Waiting... ({waited}s elapsed)")
            await asyncio.sleep(VIDEO_POLL_INTERVAL)
            waited += VIDEO_POLL_INTERVAL
            operation = client.operations.get(operation)

        print(f"  Completed in {waited}s")

        # Check result
        if operation.result is None or not operation.result.generated_videos:
            return {
                "status": "error",
                "variation": variation.name,
                "message": "No video generated"
            }

        # Get video data
        generated_video = operation.result.generated_videos[0]

        # Handle Vertex AI vs Gemini Developer API
        is_vertex_ai = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"

        if is_vertex_ai:
            video_data = generated_video.video.video_bytes
        else:
            client.files.download(file=generated_video.video)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                temp_path = tmp.name
            generated_video.video.save(temp_path)
            with open(temp_path, "rb") as f:
                video_data = f.read()
            os.unlink(temp_path)

        # Save video
        output_filename = generate_video_filename(product_name, variation, output_dir)
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, "wb") as f:
            f.write(video_data)
        print(f"  Saved: {output_path}")

        # Save prompts for reference
        if save_prompt:
            prompt_filename = output_filename.replace(".mp4", ".txt")
            prompt_path = os.path.join(output_dir, prompt_filename)
            with open(prompt_path, "w") as f:
                f.write(f"Product: {product_name}\n")
                f.write(f"Variation: {variation.name}\n")
                f.write(f"Pipeline: {'Two-Stage (Scene + Animation)' if use_two_stage else 'Single-Stage'}\n")
                f.write(f"\nVariation Parameters:\n{json.dumps(asdict(variation), indent=2)}\n")
                if scene_prompt:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"STAGE 1 - Scene Image Prompt:\n{'='*60}\n")
                    f.write(f"{scene_prompt}\n")
                f.write(f"\n{'='*60}\n")
                f.write(f"{'STAGE 2 - ' if use_two_stage else ''}Video Generation Prompt:\n{'='*60}\n")
                f.write(f"{video_prompt}\n")
            print(f"  Prompts saved: {prompt_path}")

        return {
            "status": "success",
            "variation": variation.name,
            "filename": output_filename,
            "path": output_path,
            "scene_prompt": scene_prompt,
            "video_prompt": video_prompt,
            "generation_time": waited,
            "pipeline": "two-stage" if use_two_stage else "single-stage"
        }

    except Exception as e:
        import traceback
        print(f"  ERROR: {str(e)}")
        print(traceback.format_exc())
        return {
            "status": "error",
            "variation": variation.name,
            "message": str(e)
        }


async def generate_batch(
    product_image_path: str,
    variations: List[CreativeVariation],
    output_dir: str = VIDEOS_DIR,
    use_two_stage: bool = True
) -> List[dict]:
    """Generate video ads for multiple variations.

    Args:
        product_image_path: Path to the product image
        variations: List of creative variations
        output_dir: Output directory for videos
        use_two_stage: Use two-stage pipeline (scene image + video)

    Returns:
        List of generation results
    """
    os.makedirs(output_dir, exist_ok=True)

    # Analyze product image first
    print("\n" + "#"*60)
    print("# CREATIVE VIDEO GENERATION")
    print("#"*60)
    print(f"\nProduct: {product_image_path}")
    print(f"Variations: {len(variations)}")
    print(f"Pipeline: {'Two-Stage (Scene + Animation)' if use_two_stage else 'Single-Stage'}")
    print(f"Output: {output_dir}")

    product_metadata = analyze_product_image(product_image_path)

    results = []
    total = len(variations)

    for i, variation in enumerate(variations, 1):
        print(f"\n[{i}/{total}] Processing variation: {variation.name}")

        result = await generate_video_ad(
            product_image_path=product_image_path,
            product_metadata=product_metadata,
            variation=variation,
            output_dir=output_dir,
            use_two_stage=use_two_stage
        )
        results.append(result)

        if result["status"] == "success":
            print(f"  SUCCESS: {result['filename']} ({result['generation_time']}s)")
        else:
            print(f"  FAILED: {result['message']}")

    # Summary
    success = sum(1 for r in results if r["status"] == "success")
    failed = total - success

    print(f"\n{'='*60}")
    print("BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"  Total: {total}")
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")
    print(f"  Output: {output_dir}")

    return results


def load_variations_from_json(filepath: str) -> List[CreativeVariation]:
    """Load creative variations from a JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        List of CreativeVariation objects
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    variations_data = data.get("variations", data) if isinstance(data, dict) else data

    variations = []
    for v in variations_data:
        # Handle props as list
        if "props" in v and isinstance(v["props"], str):
            v["props"] = [v["props"]]
        variations.append(CreativeVariation(**v))

    return variations


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for the creative video generator."""
    parser = argparse.ArgumentParser(
        description="Creative Director Video Ad Generator - Generate multiple video ad variations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate with preset brief
  python -m scripts.creative_video_generator \\
      --product scripts/products/emerald-satin-slip-dress.png \\
      --preset diversity

  # Generate from custom JSON brief
  python -m scripts.creative_video_generator \\
      --product scripts/products/black-leather-moto-jacket.png \\
      --variations my-brief.json

  # List available presets
  python -m scripts.creative_video_generator --list-presets
        """
    )

    parser.add_argument(
        "--product", "-p",
        type=str,
        help="Path to the product image"
    )

    parser.add_argument(
        "--preset",
        type=str,
        choices=list(PRESET_BRIEFS.keys()),
        help="Use a preset creative brief"
    )

    parser.add_argument(
        "--variations", "-v",
        type=str,
        help="Path to JSON file with custom variations"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default=VIDEOS_DIR,
        help=f"Output directory (default: {VIDEOS_DIR})"
    )

    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List available preset briefs"
    )

    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze the product image, don't generate videos"
    )

    parser.add_argument(
        "--preview-prompts",
        action="store_true",
        help="Preview generated prompts without generating videos"
    )

    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Limit number of variations to generate (useful for testing)"
    )

    parser.add_argument(
        "--single-stage",
        action="store_true",
        help="Use single-stage pipeline (product image → video). Default is two-stage (product → scene → video)"
    )

    args = parser.parse_args()

    # List presets
    if args.list_presets:
        print("\nAvailable Creative Brief Presets:")
        print("="*60)
        for name, brief in PRESET_BRIEFS.items():
            print(f"\n{name.upper()}")
            print(f"  {brief['description']}")
            print(f"  Variations: {len(brief['variations'])}")
            for v in brief['variations']:
                print(f"    - {v.name}")
        print()
        return

    # Check for API credentials
    if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
        print("ERROR: GOOGLE_API_KEY or GOOGLE_GENAI_USE_VERTEXAI not set.")
        sys.exit(1)

    # Check product path
    if not args.product:
        parser.print_help()
        print("\nERROR: --product is required")
        sys.exit(1)

    if not os.path.exists(args.product):
        print(f"ERROR: Product image not found: {args.product}")
        sys.exit(1)

    # Analyze only mode
    if args.analyze_only:
        metadata = analyze_product_image(args.product)
        print("\nProduct Metadata:")
        print(json.dumps(metadata, indent=2))
        return

    # Get variations
    variations = []

    if args.preset:
        brief = PRESET_BRIEFS.get(args.preset)
        variations = brief["variations"]
        print(f"Using preset: {args.preset} ({len(variations)} variations)")

    elif args.variations:
        if not os.path.exists(args.variations):
            print(f"ERROR: Variations file not found: {args.variations}")
            sys.exit(1)
        variations = load_variations_from_json(args.variations)
        print(f"Loaded {len(variations)} variations from {args.variations}")

    else:
        parser.print_help()
        print("\nERROR: --preset or --variations is required")
        sys.exit(1)

    # Apply limit if specified
    if args.limit and args.limit < len(variations):
        variations = variations[:args.limit]
        print(f"Limited to {args.limit} variation(s)")

    # Determine pipeline mode
    use_two_stage = not args.single_stage

    # Preview prompts mode
    if args.preview_prompts:
        print(f"\n{'#'*60}")
        print("# PROMPT PREVIEW MODE")
        print(f"{'#'*60}")
        print(f"\nProduct: {args.product}")
        print(f"Variations: {len(variations)}")
        print(f"Pipeline: {'Two-Stage (Scene + Animation)' if use_two_stage else 'Single-Stage'}")

        product_metadata = analyze_product_image(args.product)

        for i, variation in enumerate(variations, 1):
            print(f"\n{'='*60}")
            print(f"[{i}/{len(variations)}] {variation.name}")
            print(f"{'='*60}")

            if use_two_stage:
                # Show both stage prompts
                scene_prompt = build_scene_image_prompt(product_metadata, variation)
                video_prompt = build_video_animation_prompt(product_metadata, variation)

                print(f"\n--- STAGE 1: Scene Image Prompt ---")
                print(scene_prompt)
                print(f"\n--- STAGE 2: Animation Prompt ---")
                print(video_prompt)
            else:
                # Single-stage prompt
                prompt = build_creative_prompt(product_metadata, variation)
                print(f"\n{prompt}")

            expected_filename = generate_video_filename(
                os.path.splitext(os.path.basename(args.product))[0],
                variation,
                args.output
            )
            print(f"\n→ Output: {expected_filename}")
        return

    # Run generation
    results = asyncio.run(generate_batch(
        product_image_path=args.product,
        variations=variations,
        output_dir=args.output,
        use_two_stage=use_two_stage
    ))

    # Exit with error if any failed
    if any(r["status"] == "error" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
