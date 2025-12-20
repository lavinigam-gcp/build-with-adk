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

"""Prompt builders for two-stage video generation pipeline.

Stage 1: Scene Image Prompt - Creates first frame with model wearing product
Stage 2: Video Animation Prompt - Animates the scene image
"""

from typing import Dict, Any, List
from ..models.variation import CreativeVariation


def build_scene_image_prompt(
    product: Dict[str, Any],
    variation: CreativeVariation
) -> str:
    """Build a prompt for generating a scene-ready first frame image.

    This creates an image of a model wearing the product in the desired setting,
    which will be used as the first frame for video generation.

    Args:
        product: Product dictionary with metadata
        variation: Creative variation parameters

    Returns:
        Optimized image generation prompt
    """
    # Extract product details
    garment_description = product.get("details", "")
    garment_type = product.get("style", product.get("category", "elegant fashion piece"))
    color = product.get("color", "")
    fabric = product.get("fabric", "")

    if garment_description:
        garment_desc = f"{color} {fabric} {garment_type}".strip()
    else:
        garment_desc = f"{color} {fabric} {garment_type}".strip()

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
        "cafe": "at an elegant European-style cafe with soft ambient lighting",
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

    # Key features from product
    key_features = product.get("details", "fabric texture and construction")

    # Construct the scene image prompt
    prompt = f"""{style_desc} of {model_desc} wearing a stunning {garment_desc}.

She is {pose_desc} {setting_desc} {time_desc}{props_desc}.

{lighting_desc}. The garment is clearly visible with all its details: {key_features}.

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
    product: Dict[str, Any],
    variation: CreativeVariation
) -> str:
    """Build a prompt focused on animating an existing scene image.

    Since Stage 1 creates the scene, this prompt focuses on movement and animation.

    Args:
        product: Product dictionary with metadata
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


def build_creative_prompt(
    product: Dict[str, Any],
    variation: CreativeVariation
) -> str:
    """Build a single-stage video prompt (fallback when not using two-stage).

    This combines scene and animation into one prompt for direct video generation.

    Args:
        product: Product dictionary with metadata
        variation: Creative variation parameters

    Returns:
        Full video generation prompt
    """
    # Extract product details
    garment_type = product.get("style", product.get("category", "elegant fashion piece"))
    color = product.get("color", "")
    fabric = product.get("fabric", "")
    garment_desc = f"{color} {fabric} {garment_type}".strip() or "elegant fashion piece"

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

    # Build setting
    setting_map = {
        "beach": "on a pristine sandy beach",
        "urban": "in a stylish urban cityscape",
        "cafe": "at an elegant European-style cafe",
        "rooftop": "on a luxurious rooftop terrace",
        "studio": "in a minimalist professional studio",
        "garden": "in a lush, blooming garden",
        "street": "on a charming cobblestone street",
        "luxury-interior": "in an opulent luxury interior",
        "nature": "in a serene natural landscape",
        "park": "in a beautiful sunlit park",
    }
    setting_desc = setting_map.get(variation.setting, f"in a {variation.setting} setting")

    # Time of day
    time_map = {
        "golden-hour": "during magical golden hour",
        "sunrise": "at sunrise with soft morning light",
        "day": "in natural daylight",
        "sunset": "at sunset with warm orange hues",
        "dusk": "at dusk with purple twilight",
        "night": "at night with atmospheric city lights",
    }
    time_desc = time_map.get(variation.time_of_day, "")

    # Activity
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

    # Camera
    camera_map = {
        "orbit": "Camera slowly orbits around the subject",
        "pan": "Camera pans smoothly across the scene",
        "dolly": "Camera dollies in dramatically",
        "static": "Camera holds steady with subtle movement",
        "tracking": "Camera tracks alongside the subject",
        "crane": "Camera sweeps with crane-like movement",
        "handheld": "Camera has subtle handheld movement",
    }
    camera_desc = camera_map.get(variation.camera_movement, f"Camera {variation.camera_movement}")

    # Lighting
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

    # Style
    style_map = {
        "cinematic": "Cinematic",
        "editorial": "High-fashion editorial",
        "commercial": "Polished commercial",
        "artistic": "Artistic",
        "documentary": "Documentary-style",
    }
    style_desc = style_map.get(variation.visual_style, variation.visual_style)

    # Construct prompt
    prompt = f"""{style_desc} fashion video advertisement featuring {model_desc} wearing a stunning {garment_desc}.

She is {activity_desc} {setting_desc} {time_desc}.

{camera_desc}, showcasing the garment's movement and drape.

{lighting_desc}.

Professional high-end fashion advertisement. 8 seconds. Vertical 9:16 format."""

    return prompt
