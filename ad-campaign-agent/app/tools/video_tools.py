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

"""Video generation tools using Veo 3.1 API."""

import io
import json
import os
import time
from typing import Optional, Dict, Any

from PIL import Image as PILImage
from google import genai
from google.genai import types
from google.adk.tools import ToolContext

from ..config import SELECTED_DIR, GENERATED_DIR, VIDEO_ANALYSIS_MODEL
from ..database.db import get_db_cursor
from ..database.mock_data import generate_mock_metrics
from ..models.video_properties import VideoProperties
from .. import storage


def generate_video_prompt(metadata: dict, campaign_info: dict = None) -> str:
    """Generate a compelling video prompt from image metadata.

    Creates cinematic fashion video descriptions based on:
    - Model characteristics (from image analysis)
    - Clothing details (color, style, pattern)
    - Setting suggestions
    - Campaign context

    Args:
        metadata: Image analysis metadata dictionary
        campaign_info: Optional campaign context for additional styling

    Returns:
        Generated video prompt string
    """
    model_desc = metadata.get("model_description", "a model")
    clothing_desc = metadata.get("clothing_description", "elegant clothing")
    setting_desc = metadata.get("setting_description", "In a beautiful setting")
    garment_type = metadata.get("garment_type", "outfit")
    movement = metadata.get("movement", "moves gracefully")
    camera_style = metadata.get("camera_style", "slowly pans")
    key_feature = metadata.get("key_feature", "the details")
    mood = metadata.get("mood", "elegant, aspirational")

    prompt = f"""A cinematic fashion video featuring {model_desc} wearing {clothing_desc}. {setting_desc}, the {garment_type} {movement}. Camera {camera_style}, capturing {key_feature}. Atmosphere: {mood}. Professional lighting, high-end fashion advertisement style."""

    return prompt


async def analyze_video(video_path: str) -> VideoProperties:
    """Analyze a generated video using Gemini to extract structured properties.

    Uses VIDEO_ANALYSIS_MODEL from config with structured output (JSON Schema from Pydantic).
    This enables correlation between video properties and performance metrics.

    Args:
        video_path: Path to the video file (filename, relative path, or absolute path)

    Returns:
        VideoProperties: Structured properties extracted from the video
    """
    print(f"[DEBUG analyze_video] Analyzing video: {video_path}")
    print(f"[DEBUG analyze_video] Storage mode: {storage.get_storage_mode()}")

    # Extract just the filename for storage operations
    # Handle various input formats: gs:// URLs, absolute paths, relative paths, or bare filenames
    if video_path.startswith("gs://"):
        # GCS URL: gs://bucket/generated/filename.mp4 -> filename.mp4
        filename = video_path.split("/")[-1]
    elif os.path.isabs(video_path):
        # Absolute local path: /path/to/filename.mp4 -> filename.mp4
        filename = os.path.basename(video_path)
    elif video_path.startswith("generated/"):
        # Relative path: generated/filename.mp4 -> filename.mp4
        filename = video_path.replace("generated/", "")
    else:
        # Already a filename
        filename = video_path

    print(f"[DEBUG analyze_video] Extracted filename: {filename}")

    # Check if video exists using storage abstraction
    if not storage.video_exists(filename):
        print(f"[DEBUG analyze_video] Video file not found: {filename}")
        # Return default properties if file not found
        return VideoProperties()

    client = genai.Client()

    # Read video file using storage abstraction
    print(f"[DEBUG analyze_video] Reading video file...")
    video_bytes = storage.read_video(filename)
    print(f"[DEBUG analyze_video] Video size: {len(video_bytes)} bytes")

    # Create video part for Gemini
    video_part = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")

    prompt = """Analyze this fashion video advertisement and extract structured properties.

Focus on:
1. **Mood and emotional tone**: What feeling does the video evoke? (quirky, warm, bold, serene, mysterious, playful, sophisticated, energetic, elegant, romantic)
2. **Mood intensity**: How strong is this mood? (0.0 to 1.0)
3. **Warmth**: Does the video convey warmth/comfort? (true/false)
4. **Visual style**: What is the overall visual treatment? (cinematic, documentary, editorial, commercial, artistic, minimalist, vintage, modern)
5. **Camera movement**: Primary camera movement (static, pan, orbit, track, dolly, crane, handheld, slow_zoom)
6. **Lighting style**: Lighting approach (natural, studio, dramatic, soft, high_key, low_key, golden_hour, neon)
7. **Energy level**: Pace and movement intensity (calm, moderate, dynamic, high_energy)
8. **Movement amount**: Amount of subject movement (0.0 to 1.0)
9. **Color temperature**: Overall color grading (warm, neutral, cool)
10. **Dominant colors**: List the primary 2-4 colors in the video
11. **Color saturation**: How saturated are the colors? (0.0 to 1.0)
12. **Subject count**: Number of models/subjects visible
13. **Garment visibility**: How prominently is the garment featured? (0.0 to 1.0)
14. **Setting type**: Setting category (outdoor, studio, urban, nature, indoor, beach, etc.)
15. **Time of day**: Time depicted (golden_hour, day, night, dawn, dusk)
16. **Style tags**: List of 3-5 descriptive style tags
17. **Audio type**: Type of audio if present (none, ambient, music_upbeat, music_calm, music_dramatic, dialogue, voiceover)
18. **Background complexity**: How complex/busy is the background? (0.0 to 1.0)

Respond with a JSON object matching the VideoProperties schema. Be precise and consistent in your analysis."""

    try:
        print(f"[DEBUG analyze_video] Calling Gemini {VIDEO_ANALYSIS_MODEL}...")
        response = client.models.generate_content(
            model=VIDEO_ANALYSIS_MODEL,
            contents=[video_part, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VideoProperties.model_json_schema()
            )
        )

        print(f"[DEBUG analyze_video] Response received")
        properties_dict = json.loads(response.text)
        print(f"[DEBUG analyze_video] Parsed properties: mood={properties_dict.get('mood')}, "
              f"energy={properties_dict.get('energy_level')}")

        return VideoProperties(**properties_dict)

    except Exception as e:
        print(f"[DEBUG analyze_video] Error analyzing video: {str(e)}")
        # Return default properties on error
        return VideoProperties()


def build_templated_prompt(
    base_metadata: dict,
    property_overrides: Optional[Dict[str, Any]] = None
) -> str:
    """Build a video prompt from templates with property overrides.

    This enables natural language control over video generation by allowing
    specific properties to be specified (mood, energy, style, etc.)

    Args:
        base_metadata: Image metadata (clothing, model description, etc.)
        property_overrides: Optional dict of properties to override defaults
            e.g., {"mood": "quirky", "energy_level": "high_energy", "color_temperature": "warm"}

    Returns:
        Generated prompt string
    """
    # Default properties
    props = {
        "mood": "elegant",
        "visual_style": "cinematic",
        "energy_level": "moderate",
        "color_temperature": "neutral",
        "camera_movement": "orbit",
        "lighting_style": "studio",
        "setting_type": "studio",
        "time_of_day": "day"
    }

    # Apply overrides
    if property_overrides:
        props.update(property_overrides)

    # Map mood to prompt fragments
    mood_map = {
        "quirky": "with a quirky, unexpected charm",
        "warm": "with warm, inviting atmosphere",
        "bold": "with bold, striking confidence",
        "serene": "with serene, peaceful elegance",
        "mysterious": "with an air of mystery and allure",
        "playful": "with playful, fun energy",
        "sophisticated": "with sophisticated refinement",
        "energetic": "with vibrant, high energy",
        "elegant": "with timeless elegance",
        "romantic": "with romantic, dreamy quality"
    }

    # Map energy to movement descriptions
    energy_map = {
        "calm": "moves gently and gracefully",
        "moderate": "moves with measured elegance",
        "dynamic": "moves with dynamic energy",
        "high_energy": "moves with vibrant, high energy"
    }

    # Map camera movement to descriptions
    camera_map = {
        "static": "Camera holds steady",
        "pan": "Camera pans smoothly",
        "orbit": "Camera slowly orbits around the subject",
        "track": "Camera tracks alongside the subject",
        "dolly": "Camera dollies in smoothly",
        "crane": "Camera moves with crane-like fluidity",
        "handheld": "Camera has subtle handheld movement",
        "slow_zoom": "Camera slowly zooms"
    }

    # Map visual style
    style_map = {
        "cinematic": "Cinematic",
        "documentary": "Documentary-style",
        "editorial": "High fashion editorial",
        "commercial": "Commercial",
        "artistic": "Artistic",
        "minimalist": "Minimalist",
        "vintage": "Vintage-inspired",
        "modern": "Modern contemporary"
    }

    # Build prompt components from metadata
    model_desc = base_metadata.get("model_description", "a model")
    clothing_desc = base_metadata.get("clothing_description", "elegant clothing")
    garment_type = base_metadata.get("garment_type", "outfit")

    # Get mapped values
    mood_text = mood_map.get(props["mood"], f"with {props['mood']} atmosphere")
    energy_text = energy_map.get(props["energy_level"], "moves gracefully")
    camera_text = camera_map.get(props["camera_movement"], f"Camera {props['camera_movement']}")
    style_text = style_map.get(props["visual_style"], props["visual_style"])

    # Build the templated prompt
    prompt = f"""{style_text} fashion video featuring {model_desc} wearing {clothing_desc}.
The subject {energy_text} {mood_text}.
{camera_text}, capturing the {garment_type} in {props['lighting_style']} lighting.
Color grading: {props['color_temperature']} tones.
Setting: {props['setting_type']} environment during {props['time_of_day']}.
Professional high-end fashion advertisement style."""

    return prompt


async def generate_video_ad(
    campaign_id: int,
    image_id: Optional[int] = None,
    custom_prompt: Optional[str] = None,
    duration_seconds: int = 6,
    tool_context: ToolContext = None
) -> dict:
    """Generate a video ad using Veo 3.1.

    Uses a seed image as reference and generates a cinematic fashion video.
    Polls for completion and saves to the generated/ folder.
    Optionally saves video as ADK artifact if tool_context is provided.

    Args:
        campaign_id: The campaign to generate the ad for
        image_id: Optional specific image ID to use. If not provided, uses the first image.
        custom_prompt: Optional custom prompt. If not provided, generates from image metadata.
        duration_seconds: Video duration (4, 6, or 8 seconds for Veo 3.1)
        tool_context: Optional ADK ToolContext for artifact storage

    Returns:
        Dictionary with video path and generation details
    """
    print(f"[DEBUG generate_video_ad] Starting for campaign_id={campaign_id}")
    print(f"[DEBUG generate_video_ad] image_id={image_id}, duration_seconds={duration_seconds}")
    print(f"[DEBUG generate_video_ad] custom_prompt={custom_prompt[:100] if custom_prompt else 'None'}...")

    # Veo 3.1 only accepts duration of 4, 6, or 8 seconds
    valid_durations = [4, 6, 8]
    if duration_seconds not in valid_durations:
        # Map to nearest valid duration
        if duration_seconds <= 4:
            duration_seconds = 4
        elif duration_seconds <= 6:
            duration_seconds = 6
        else:
            duration_seconds = 8
        print(f"[DEBUG generate_video_ad] Adjusted duration to: {duration_seconds}")

    # Ensure generated directory exists (only in local mode)
    if storage.get_storage_mode() == "local":
        os.makedirs(GENERATED_DIR, exist_ok=True)
        print(f"[DEBUG generate_video_ad] GENERATED_DIR: {GENERATED_DIR}")
    else:
        print(f"[DEBUG generate_video_ad] Using GCS storage, skipping local directory creation")

    with get_db_cursor() as cursor:
        # Get campaign info
        print(f"[DEBUG generate_video_ad] Fetching campaign {campaign_id} from database...")
        cursor.execute('SELECT * FROM campaigns WHERE id = ?', (campaign_id,))
        campaign = cursor.fetchone()
        if not campaign:
            print(f"[DEBUG generate_video_ad] Campaign {campaign_id} not found")
            return {
                "status": "error",
                "message": f"Campaign with ID {campaign_id} not found"
            }
        print(f"[DEBUG generate_video_ad] Found campaign: {campaign['name']}")

        # Get image
        if image_id:
            print(f"[DEBUG generate_video_ad] Fetching specific image {image_id}...")
            cursor.execute('''
                SELECT * FROM campaign_images
                WHERE id = ? AND campaign_id = ?
            ''', (image_id, campaign_id))
        else:
            print(f"[DEBUG generate_video_ad] Fetching first image for campaign...")
            cursor.execute('''
                SELECT * FROM campaign_images
                WHERE campaign_id = ?
                ORDER BY created_at
                LIMIT 1
            ''', (campaign_id,))

        image_row = cursor.fetchone()
        if not image_row:
            print(f"[DEBUG generate_video_ad] No images found for campaign {campaign_id}")
            return {
                "status": "error",
                "message": f"No images found for campaign {campaign_id}. Add a seed image first."
            }
        print(f"[DEBUG generate_video_ad] Found image: {image_row['image_path']}")

        image_filename = image_row["image_path"]
        image_path = storage.get_image_path(image_filename)
        print(f"[DEBUG generate_video_ad] Image path: {image_path}")
        print(f"[DEBUG generate_video_ad] Storage mode: {storage.get_storage_mode()}")
        if not storage.image_exists(image_filename):
            print(f"[DEBUG generate_video_ad] Image file not found: {image_filename}")
            return {
                "status": "error",
                "message": f"Image file not found: {image_filename}"
            }
        print(f"[DEBUG generate_video_ad] Image file exists")

        # Get or generate prompt
        if custom_prompt:
            prompt = custom_prompt
            print(f"[DEBUG generate_video_ad] Using custom prompt")
        else:
            metadata = json.loads(image_row["metadata"]) if image_row["metadata"] else {}
            campaign_info = {
                "name": campaign["name"],
                "category": campaign["category"],
                "city": campaign["city"],
                "state": campaign["state"]
            }
            prompt = generate_video_prompt(metadata, campaign_info)
            print(f"[DEBUG generate_video_ad] Generated prompt from metadata")
        print(f"[DEBUG generate_video_ad] Prompt: {prompt[:100]}...")

        # Create pending ad record
        print(f"[DEBUG generate_video_ad] Creating pending ad record...")
        cursor.execute('''
            INSERT INTO campaign_ads (campaign_id, image_id, video_path, prompt_used, duration_seconds, status)
            VALUES (?, ?, '', ?, ?, 'generating')
        ''', (campaign_id, image_row["id"], prompt, duration_seconds))
        ad_id = cursor.lastrowid
        print(f"[DEBUG generate_video_ad] Created ad record with id={ad_id}")

    # Generate video using Veo 3.1
    try:
        print(f"[DEBUG generate_video_ad] Initializing genai client...")
        client = genai.Client()

        # Load image using storage abstraction and convert to bytes for Veo API
        # This follows the official Veo documentation pattern
        print(f"[DEBUG generate_video_ad] Loading image...")
        image_bytes = storage.read_image(image_filename)
        print(f"[DEBUG generate_video_ad] Image bytes size: {len(image_bytes)}")

        # Use PIL to determine format and re-encode if needed
        with PILImage.open(io.BytesIO(image_bytes)) as im:
            print(f"[DEBUG generate_video_ad] Image format: {im.format}, size: {im.size}")
            img_format = im.format or "JPEG"

        # Create types.Image for Veo API (NOT types.Part)
        mime_type = f"image/{img_format.lower()}"
        print(f"[DEBUG generate_video_ad] Creating types.Image with mime_type={mime_type}")
        image = types.Image(image_bytes=image_bytes, mime_type=mime_type)

        # Start video generation
        print(f"[DEBUG generate_video_ad] Starting video generation with Veo 3.1...")
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=prompt,
            image=image,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=duration_seconds,
                # Note: enhance_prompt is NOT supported by veo-3.1-generate-preview
            ),
        )
        print(f"[DEBUG generate_video_ad] Video generation started, operation: {operation}")

        # Poll for completion (20 second intervals per official docs)
        max_wait_time = 600  # 10 minutes max for video generation
        poll_interval = 20  # 20 seconds per official docs
        waited = 0

        while not operation.done:
            if waited >= max_wait_time:
                print(f"[DEBUG generate_video_ad] Timed out after {max_wait_time} seconds")
                with get_db_cursor() as cursor:
                    cursor.execute('''
                        UPDATE campaign_ads SET status = 'failed' WHERE id = ?
                    ''', (ad_id,))
                return {
                    "status": "error",
                    "message": "Video generation timed out after 10 minutes",
                    "ad_id": ad_id
                }

            print(f"[DEBUG generate_video_ad] Waiting... ({waited}s elapsed)")
            time.sleep(poll_interval)
            waited += poll_interval
            operation = client.operations.get(operation)
            print(f"[DEBUG generate_video_ad] Operation done: {operation.done}")

        print(f"[DEBUG generate_video_ad] Operation completed after {waited}s")

        # Check if operation succeeded (use .result NOT .response per official docs)
        print(f"[DEBUG generate_video_ad] Checking result: {operation.result}")
        if operation.result is None or not operation.result.generated_videos:
            print(f"[DEBUG generate_video_ad] No result or no generated videos")
            with get_db_cursor() as cursor:
                cursor.execute('''
                    UPDATE campaign_ads SET status = 'failed' WHERE id = ?
                ''', (ad_id,))
            return {
                "status": "error",
                "message": "Video generation completed but returned no result. Check API quota and permissions.",
                "ad_id": ad_id,
                "prompt_used": prompt
            }

        print(f"[DEBUG generate_video_ad] Found {len(operation.result.generated_videos)} generated video(s)")

        # Get the generated video
        generated_video = operation.result.generated_videos[0]
        timestamp = int(time.time())
        output_filename = f"campaign_{campaign_id}_ad_{ad_id}_{timestamp}.mp4"

        # Handle video bytes differently for Vertex AI vs Gemini Developer API
        # - Vertex AI: video_bytes are already in the response (no download needed)
        # - Gemini Developer API: Must call client.files.download() to populate video_bytes
        is_vertex_ai = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
        print(f"[DEBUG generate_video_ad] Using Vertex AI: {is_vertex_ai}")

        if is_vertex_ai:
            # Vertex AI: video_bytes already present in response
            print(f"[DEBUG generate_video_ad] Vertex AI mode - using video_bytes from response")
            video_data = generated_video.video.video_bytes
            if not video_data:
                raise ValueError("No video_bytes in Vertex AI response")
            print(f"[DEBUG generate_video_ad] Video bytes size: {len(video_data)}")
        else:
            # Gemini Developer API: Must download first, then use .save()
            print(f"[DEBUG generate_video_ad] Gemini Developer API mode - downloading video...")
            client.files.download(file=generated_video.video)
            # For Gemini API, we need to save to temp file to get bytes
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                temp_path = tmp.name
            generated_video.video.save(temp_path)
            with open(temp_path, "rb") as f:
                video_data = f.read()
            os.unlink(temp_path)
            print(f"[DEBUG generate_video_ad] Video bytes size: {len(video_data)}")

        # Save video - handle both local and GCS storage modes
        if storage.get_storage_mode() == "gcs":
            output_path = storage.save_video(output_filename, video_data)
            print(f"[DEBUG generate_video_ad] Video uploaded to GCS: {output_path}")
        else:
            output_path = os.path.join(GENERATED_DIR, output_filename)
            print(f"[DEBUG generate_video_ad] Saving video to: {output_path}")
            with open(output_path, "wb") as f:
                f.write(video_data)
            print(f"[DEBUG generate_video_ad] Video saved successfully")

        # Save as ADK artifact if tool_context is provided
        if tool_context:
            print(f"[DEBUG generate_video_ad] Saving as ADK artifact...")
            # Use video_data we already have in memory (no need to re-read from storage)
            video_artifact = types.Part.from_bytes(data=video_data, mime_type="video/mp4")
            # save_artifact is async, await it properly
            version = await tool_context.save_artifact(filename=output_filename, artifact=video_artifact)
            print(f"[DEBUG generate_video_ad] Artifact saved, version: {version}")
        else:
            print(f"[DEBUG generate_video_ad] No tool_context, skipping artifact save")

        # Analyze the generated video to extract properties
        print(f"[DEBUG generate_video_ad] Analyzing generated video for properties...")
        video_properties = await analyze_video(output_path)
        print(f"[DEBUG generate_video_ad] Extracted properties: mood={video_properties.mood}, "
              f"energy={video_properties.energy_level}, style={video_properties.visual_style}")

        # Update database with video path and properties
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE campaign_ads
                SET video_path = ?, status = 'completed', video_properties = ?
                WHERE id = ?
            ''', (output_filename, video_properties.model_dump_json(), ad_id))

        # Auto-generate mock metrics for the new ad (90 days of data)
        # Uses in-store retail media metrics: impressions, dwell_time, circulation, revenue
        print(f"[DEBUG generate_video_ad] Generating mock metrics for ad_id={ad_id}...")
        mock_metrics = generate_mock_metrics(campaign_id, ad_id, days=90)
        with get_db_cursor() as cursor:
            for metric in mock_metrics:
                cursor.execute('''
                    INSERT INTO campaign_metrics
                    (campaign_id, ad_id, date, impressions, dwell_time, circulation, revenue)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metric["campaign_id"],
                    metric["ad_id"],
                    metric["date"],
                    metric["impressions"],
                    metric["dwell_time"],
                    metric["circulation"],
                    metric["revenue"]
                ))
        print(f"[DEBUG generate_video_ad] Inserted {len(mock_metrics)} metric records")

        return {
            "status": "success",
            "message": "Video ad generated successfully",
            "ad": {
                "id": ad_id,
                "campaign_id": campaign_id,
                "campaign_name": campaign["name"],
                "video_path": output_filename,
                "full_path": output_path,
                "prompt_used": prompt,
                "duration_seconds": duration_seconds,
                "source_image": image_row["image_path"],
                "artifact_saved": tool_context is not None,
                "metrics_generated": len(mock_metrics)
            },
            "video_properties": video_properties.model_dump()
        }

    except Exception as e:
        import traceback
        print(f"[DEBUG generate_video_ad] Exception: {str(e)}")
        print(f"[DEBUG generate_video_ad] Traceback: {traceback.format_exc()}")
        # Update ad status to failed
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE campaign_ads SET status = 'failed' WHERE id = ?
            ''', (ad_id,))

        return {
            "status": "error",
            "message": f"Video generation failed: {str(e)}",
            "ad_id": ad_id,
            "prompt_used": prompt
        }


def generate_video_variation(
    ad_id: int,
    variation_type: str = "setting"
) -> dict:
    """Generate a variation of an existing successful ad.

    Modifies the prompt based on variation_type to create an A/B testing variant.

    Args:
        ad_id: The ID of the original ad to create a variation of
        variation_type: Type of variation - one of: setting, mood, angle, style

    Returns:
        Dictionary with new video details
    """
    variation_modifiers = {
        "setting": [
            "In a luxurious urban rooftop at golden hour",
            "In an elegant minimalist studio with soft natural light",
            "On a scenic coastal backdrop with ocean breeze",
            "In a chic European café setting"
        ],
        "mood": [
            "Atmosphere: bold, confident, powerful",
            "Atmosphere: serene, peaceful, calming",
            "Atmosphere: energetic, vibrant, youthful",
            "Atmosphere: mysterious, alluring, sophisticated"
        ],
        "angle": [
            "Camera dramatically sweeps from low angle upward",
            "Camera follows in slow-motion tracking shot",
            "Camera circles in an elegant 360-degree orbit",
            "Camera captures from artistic bird's eye perspective"
        ],
        "style": [
            "Film noir style with dramatic shadows and contrast",
            "Soft focus romantic style with dreamy lens flare",
            "High contrast editorial style with sharp details",
            "Vintage film aesthetic with warm color grading"
        ]
    }

    if variation_type not in variation_modifiers:
        return {
            "status": "error",
            "message": f"Invalid variation_type. Must be one of: {', '.join(variation_modifiers.keys())}"
        }

    with get_db_cursor() as cursor:
        # Get original ad
        cursor.execute('''
            SELECT ca.*, c.name as campaign_name, ci.image_path, ci.metadata
            FROM campaign_ads ca
            JOIN campaigns c ON ca.campaign_id = c.id
            LEFT JOIN campaign_images ci ON ca.image_id = ci.id
            WHERE ca.id = ?
        ''', (ad_id,))

        original_ad = cursor.fetchone()
        if not original_ad:
            return {
                "status": "error",
                "message": f"Ad with ID {ad_id} not found"
            }

        if original_ad["status"] != "completed":
            return {
                "status": "error",
                "message": f"Original ad is not completed (status: {original_ad['status']})"
            }

    # Get a random modifier for the variation type
    import random
    modifier = random.choice(variation_modifiers[variation_type])

    # Modify the original prompt
    original_prompt = original_ad["prompt_used"]

    if variation_type == "setting":
        # Replace setting description
        parts = original_prompt.split(".")
        if len(parts) > 1:
            parts[1] = f" {modifier}"
        variation_prompt = ".".join(parts)
    elif variation_type == "mood":
        # Replace mood at the end
        if "Atmosphere:" in original_prompt:
            variation_prompt = original_prompt.rsplit("Atmosphere:", 1)[0] + modifier
        else:
            variation_prompt = original_prompt + " " + modifier
    elif variation_type == "angle":
        # Replace camera instruction
        if "Camera " in original_prompt:
            parts = original_prompt.split("Camera ")
            variation_prompt = parts[0] + modifier
            if len(parts) > 1 and "." in parts[1]:
                remaining = parts[1].split(".", 1)[1]
                variation_prompt += "." + remaining
        else:
            variation_prompt = original_prompt + " " + modifier
    else:  # style
        variation_prompt = original_prompt + " " + modifier

    # Generate the variation
    return generate_video_ad(
        campaign_id=original_ad["campaign_id"],
        image_id=original_ad["image_id"],
        custom_prompt=variation_prompt,
        duration_seconds=original_ad["duration_seconds"]
    )


async def apply_winning_formula(
    target_campaign_id: int,
    source_ad_id: int = None,
    characteristics_to_apply: list = None,
    target_image_id: int = None,
    tool_context: ToolContext = None
) -> dict:
    """Apply successful characteristics from a top-performing ad to generate new content.

    This tool bridges insights and action: after identifying what makes top performers
    successful, use this to apply those winning characteristics to other campaigns.

    Args:
        target_campaign_id: The campaign to create a new video ad for
        source_ad_id: The ad to learn from. If None, automatically uses the top performer.
        characteristics_to_apply: List of characteristics to preserve from source.
            Options: ["mood", "setting", "camera_style", "movement"]
            If None, applies all available characteristics.
        target_image_id: Specific image in target campaign to use. If None, uses first available.
        tool_context: ADK ToolContext for artifact storage

    Returns:
        Dictionary with new video details and applied characteristics

    Example:
        # After seeing insights that ad #1 has winning "dreamy, romantic" mood:
        apply_winning_formula(
            target_campaign_id=3,  # Urban Professional campaign
            source_ad_id=1,        # Top performer
            characteristics_to_apply=["mood", "setting"]
        )
    """
    print(f"[DEBUG apply_winning_formula] Starting...")
    print(f"[DEBUG apply_winning_formula] target_campaign_id={target_campaign_id}")
    print(f"[DEBUG apply_winning_formula] source_ad_id={source_ad_id}")
    print(f"[DEBUG apply_winning_formula] characteristics_to_apply={characteristics_to_apply}")

    # Extended characteristics when video_properties are available
    valid_characteristics = [
        "mood", "setting", "camera_style", "movement", "key_feature",
        # New video property characteristics
        "visual_style", "energy_level", "color_temperature", "lighting_style"
    ]

    if characteristics_to_apply:
        invalid = [c for c in characteristics_to_apply if c not in valid_characteristics]
        if invalid:
            return {
                "status": "error",
                "message": f"Invalid characteristics: {invalid}. Valid options: {valid_characteristics}"
            }

    with get_db_cursor() as cursor:
        # Step 1: Get source ad (top performer or specified) including video_properties
        if source_ad_id:
            print(f"[DEBUG apply_winning_formula] Using specified source_ad_id={source_ad_id}")
            cursor.execute('''
                SELECT ca.*, ca.video_properties, ci.metadata, ci.image_path as source_image,
                       c.name as campaign_name,
                       SUM(cm.revenue) as total_revenue
                FROM campaign_ads ca
                JOIN campaigns c ON ca.campaign_id = c.id
                LEFT JOIN campaign_images ci ON ca.image_id = ci.id
                LEFT JOIN campaign_metrics cm ON ca.id = cm.ad_id
                WHERE ca.id = ? AND ca.status = 'completed'
                GROUP BY ca.id
            ''', (source_ad_id,))
        else:
            print(f"[DEBUG apply_winning_formula] Auto-selecting top performer by revenue...")
            cursor.execute('''
                SELECT ca.*, ca.video_properties, ci.metadata, ci.image_path as source_image,
                       c.name as campaign_name,
                       SUM(cm.revenue) as total_revenue
                FROM campaign_ads ca
                JOIN campaigns c ON ca.campaign_id = c.id
                LEFT JOIN campaign_images ci ON ca.image_id = ci.id
                LEFT JOIN campaign_metrics cm ON ca.id = cm.ad_id
                WHERE ca.status = 'completed'
                GROUP BY ca.id
                ORDER BY total_revenue DESC
                LIMIT 1
            ''')

        source_ad = cursor.fetchone()
        if not source_ad:
            return {
                "status": "error",
                "message": "No completed ads found to learn from" if not source_ad_id
                          else f"Source ad {source_ad_id} not found or not completed"
            }

        print(f"[DEBUG apply_winning_formula] Source ad: id={source_ad['id']}, "
              f"campaign='{source_ad['campaign_name']}', revenue=${source_ad['total_revenue'] or 0:,.2f}")

        # Step 2: Extract winning characteristics from video_properties (preferred) or image metadata (fallback)
        source_video_props = None
        if source_ad["video_properties"]:
            try:
                source_video_props = json.loads(source_ad["video_properties"])
                print(f"[DEBUG apply_winning_formula] Using VIDEO PROPERTIES from source ad")
            except json.JSONDecodeError:
                pass

        source_metadata = json.loads(source_ad["metadata"]) if source_ad["metadata"] else {}

        # Build winning formula - prefer video_properties when available
        if source_video_props:
            winning_formula = {
                # From video_properties
                "mood": source_video_props.get("mood", "elegant"),
                "visual_style": source_video_props.get("visual_style", "cinematic"),
                "energy_level": source_video_props.get("energy_level", "moderate"),
                "color_temperature": source_video_props.get("color_temperature", "neutral"),
                "camera_style": source_video_props.get("camera_movement", "orbit"),
                "lighting_style": source_video_props.get("lighting_style", "studio"),
                "setting": source_video_props.get("setting_type", "studio"),
                # From image metadata (not in video_properties)
                "movement": source_metadata.get("movement", "moves gracefully"),
                "key_feature": source_metadata.get("key_feature", "the details"),
                "model_description": source_metadata.get("model_description", "a model"),
            }
            print(f"[DEBUG apply_winning_formula] Winning formula from VIDEO PROPERTIES:")
        else:
            # Fallback to image metadata only
            winning_formula = {
                "mood": source_metadata.get("mood", "elegant, aspirational"),
                "setting": source_metadata.get("setting_description", "beautiful setting"),
                "camera_style": source_metadata.get("camera_style", "smoothly captures"),
                "movement": source_metadata.get("movement", "moves gracefully"),
                "key_feature": source_metadata.get("key_feature", "the details"),
                "model_description": source_metadata.get("model_description", "a model"),
                # Defaults for new properties
                "visual_style": "cinematic",
                "energy_level": "moderate",
                "color_temperature": "neutral",
                "lighting_style": "studio",
            }
            print(f"[DEBUG apply_winning_formula] Winning formula from IMAGE METADATA (fallback):")

        print(f"[DEBUG apply_winning_formula] Winning formula extracted:")
        for k, v in winning_formula.items():
            print(f"[DEBUG apply_winning_formula]   - {k}: {v}")

        # Step 3: Get target campaign and image
        cursor.execute('SELECT * FROM campaigns WHERE id = ?', (target_campaign_id,))
        target_campaign = cursor.fetchone()
        if not target_campaign:
            return {
                "status": "error",
                "message": f"Target campaign {target_campaign_id} not found"
            }

        print(f"[DEBUG apply_winning_formula] Target campaign: '{target_campaign['name']}'")

        # Get target image
        if target_image_id:
            cursor.execute('''
                SELECT * FROM campaign_images
                WHERE id = ? AND campaign_id = ?
            ''', (target_image_id, target_campaign_id))
        else:
            cursor.execute('''
                SELECT * FROM campaign_images
                WHERE campaign_id = ?
                ORDER BY created_at
                LIMIT 1
            ''', (target_campaign_id,))

        target_image = cursor.fetchone()
        if not target_image:
            return {
                "status": "error",
                "message": f"No images found for target campaign {target_campaign_id}. Add a seed image first."
            }

        print(f"[DEBUG apply_winning_formula] Target image: {target_image['image_path']}")

        # Get target image metadata for clothing description
        target_metadata = json.loads(target_image["metadata"]) if target_image["metadata"] else {}

    # Step 4: Build prompt that PRESERVES winning characteristics
    # Use target image's clothing/garment but source ad's mood, setting, etc.

    # Determine which characteristics to apply - include new video properties if available
    if characteristics_to_apply:
        chars_to_use = characteristics_to_apply
    elif source_video_props:
        # When video_properties are available, apply more characteristics by default
        chars_to_use = ["mood", "visual_style", "energy_level", "color_temperature", "setting", "camera_style", "lighting_style"]
    else:
        chars_to_use = ["mood", "setting", "camera_style", "movement"]

    # Build the prompt components
    model_desc = target_metadata.get("model_description", winning_formula["model_description"])
    clothing_desc = target_metadata.get("clothing_description", "elegant clothing")
    garment_type = target_metadata.get("garment_type", "outfit")

    # Apply winning characteristics
    if "setting" in chars_to_use:
        setting_desc = winning_formula["setting"]
    else:
        setting_desc = target_metadata.get("setting_description", "In a beautiful setting")

    if "mood" in chars_to_use:
        mood = winning_formula["mood"]
    else:
        mood = target_metadata.get("mood", "elegant, aspirational")

    if "camera_style" in chars_to_use:
        camera_style = winning_formula["camera_style"]
    else:
        camera_style = target_metadata.get("camera_style", "slowly pans")

    if "movement" in chars_to_use:
        movement = winning_formula["movement"]
    else:
        movement = target_metadata.get("movement", "moves gracefully")

    if "key_feature" in chars_to_use:
        key_feature = winning_formula["key_feature"]
    else:
        key_feature = target_metadata.get("key_feature", "the details")

    # New video property characteristics
    visual_style = winning_formula.get("visual_style", "cinematic") if "visual_style" in chars_to_use else "cinematic"
    energy_level = winning_formula.get("energy_level", "moderate") if "energy_level" in chars_to_use else "moderate"
    color_temperature = winning_formula.get("color_temperature", "neutral") if "color_temperature" in chars_to_use else "neutral"
    lighting_style = winning_formula.get("lighting_style", "studio") if "lighting_style" in chars_to_use else "professional"

    # Use templated prompt builder if video properties are available
    if source_video_props:
        # Build property overrides for templated prompt
        property_overrides = {
            "mood": mood,
            "visual_style": visual_style,
            "energy_level": energy_level,
            "color_temperature": color_temperature,
            "camera_movement": camera_style,
            "lighting_style": lighting_style,
            "setting_type": setting_desc,
        }
        winning_prompt = build_templated_prompt(target_metadata, property_overrides)
    else:
        # Fallback to original prompt format
        winning_prompt = f"""A cinematic fashion video featuring {model_desc} wearing {clothing_desc}. {setting_desc}, the {garment_type} {movement}. Camera {camera_style}, capturing {key_feature}. Atmosphere: {mood}. Professional lighting, high-end fashion advertisement style."""

    print(f"[DEBUG apply_winning_formula] Generated prompt with winning formula:")
    print(f"[DEBUG apply_winning_formula] {winning_prompt[:200]}...")
    print(f"[DEBUG apply_winning_formula] Applied characteristics: {chars_to_use}")
    print(f"[DEBUG apply_winning_formula] Using video_properties format: {source_video_props is not None}")

    # Step 5: Generate the video using the winning formula
    result = await generate_video_ad(
        campaign_id=target_campaign_id,
        image_id=target_image["id"],
        custom_prompt=winning_prompt,
        duration_seconds=6,
        tool_context=tool_context
    )

    # Enhance the result with winning formula details
    if result["status"] == "success":
        result["winning_formula_applied"] = {
            "source_ad_id": source_ad["id"],
            "source_campaign": source_ad["campaign_name"],
            "source_revenue": round(source_ad["total_revenue"], 2) if source_ad["total_revenue"] else 0,
            "characteristics_applied": chars_to_use,
            "formula": {k: winning_formula[k] for k in chars_to_use if k in winning_formula}
        }
        result["message"] = f"Video generated using winning formula from top performer (Ad #{source_ad['id']})"

    return result


def list_campaign_ads(campaign_id: int) -> dict:
    """List all generated video ads for a campaign.

    Args:
        campaign_id: The ID of the campaign

    Returns:
        Dictionary with list of ads and their details
    """
    with get_db_cursor() as cursor:
        cursor.execute('SELECT id, name FROM campaigns WHERE id = ?', (campaign_id,))
        campaign = cursor.fetchone()
        if not campaign:
            return {
                "status": "error",
                "message": f"Campaign with ID {campaign_id} not found"
            }

        cursor.execute('''
            SELECT ca.*, ci.image_path as source_image
            FROM campaign_ads ca
            LEFT JOIN campaign_images ci ON ca.image_id = ci.id
            WHERE ca.campaign_id = ?
            ORDER BY ca.created_at DESC
        ''', (campaign_id,))

        ads = []
        for row in cursor.fetchall():
            video_filename = row["video_path"]
            # Use storage abstraction for path resolution and existence check
            video_path = storage.get_video_path(video_filename) if video_filename else None
            video_exists = storage.video_exists(video_filename) if video_filename else False
            # Parse video properties if available
            video_props = None
            if row["video_properties"]:
                try:
                    video_props = json.loads(row["video_properties"])
                except json.JSONDecodeError:
                    pass
            ads.append({
                "id": row["id"],
                "video_path": video_filename,
                "full_path": video_path,
                "exists": video_exists,
                "prompt_used": row["prompt_used"],
                "duration_seconds": row["duration_seconds"],
                "status": row["status"],
                "source_image": row["source_image"],
                "video_properties": video_props,
                "created_at": row["created_at"]
            })

        return {
            "status": "success",
            "campaign_id": campaign_id,
            "campaign_name": campaign["name"],
            "ad_count": len(ads),
            "ads": ads
        }


async def generate_video_with_properties(
    campaign_id: int,
    image_id: Optional[int] = None,
    mood: Optional[str] = None,
    visual_style: Optional[str] = None,
    energy_level: Optional[str] = None,
    color_temperature: Optional[str] = None,
    camera_movement: Optional[str] = None,
    lighting_style: Optional[str] = None,
    setting_type: Optional[str] = None,
    time_of_day: Optional[str] = None,
    duration_seconds: int = 6,
    tool_context: ToolContext = None
) -> dict:
    """Generate a video ad with specific property controls.

    This enables natural language variation requests like:
    "Generate a quirky, high-energy video with warm colors"

    All property parameters are optional - only specify the ones you want to control.
    Unspecified properties will use sensible defaults.

    Args:
        campaign_id: The campaign to generate for
        image_id: Optional specific image ID to use
        mood: Mood override (quirky, warm, bold, serene, mysterious, playful, sophisticated, energetic, elegant, romantic)
        visual_style: Style override (cinematic, documentary, editorial, commercial, artistic, minimalist, vintage, modern)
        energy_level: Energy override (calm, moderate, dynamic, high_energy)
        color_temperature: Color override (warm, neutral, cool)
        camera_movement: Camera override (static, pan, orbit, track, dolly, crane, handheld, slow_zoom)
        lighting_style: Lighting override (natural, studio, dramatic, soft, high_key, low_key, golden_hour, neon)
        setting_type: Setting override (outdoor, studio, urban, nature, indoor, beach, etc.)
        time_of_day: Time override (golden_hour, day, night, dawn, dusk)
        duration_seconds: Video duration (4, 6, or 8 seconds)
        tool_context: ADK ToolContext for artifact storage

    Returns:
        Dictionary with video details and extracted properties
    """
    print(f"[DEBUG generate_video_with_properties] Starting for campaign_id={campaign_id}")

    # Build property overrides from parameters
    property_overrides = {}
    if mood:
        property_overrides["mood"] = mood
    if visual_style:
        property_overrides["visual_style"] = visual_style
    if energy_level:
        property_overrides["energy_level"] = energy_level
    if color_temperature:
        property_overrides["color_temperature"] = color_temperature
    if camera_movement:
        property_overrides["camera_movement"] = camera_movement
    if lighting_style:
        property_overrides["lighting_style"] = lighting_style
    if setting_type:
        property_overrides["setting_type"] = setting_type
    if time_of_day:
        property_overrides["time_of_day"] = time_of_day

    print(f"[DEBUG generate_video_with_properties] Property overrides: {property_overrides}")

    # Get image metadata
    with get_db_cursor() as cursor:
        if image_id:
            cursor.execute('''
                SELECT metadata FROM campaign_images
                WHERE campaign_id = ? AND id = ?
            ''', (campaign_id, image_id))
        else:
            cursor.execute('''
                SELECT metadata FROM campaign_images
                WHERE campaign_id = ?
                ORDER BY created_at
                LIMIT 1
            ''', (campaign_id,))

        row = cursor.fetchone()
        if not row:
            return {
                "status": "error",
                "message": f"No images found for campaign {campaign_id}. Add a seed image first."
            }
        base_metadata = json.loads(row["metadata"]) if row and row["metadata"] else {}

    # Build templated prompt with property overrides
    prompt = build_templated_prompt(base_metadata, property_overrides)
    print(f"[DEBUG generate_video_with_properties] Generated prompt: {prompt[:200]}...")

    # Generate video with custom prompt
    result = await generate_video_ad(
        campaign_id=campaign_id,
        image_id=image_id,
        custom_prompt=prompt,
        duration_seconds=duration_seconds,
        tool_context=tool_context
    )

    # Add requested properties to result
    if result["status"] == "success":
        result["requested_properties"] = property_overrides
        result["message"] = f"Video generated with custom properties: {', '.join(property_overrides.keys()) or 'defaults'}"

    return result


async def get_video_properties(ad_id: int) -> dict:
    """Get the analyzed properties for a specific video ad.

    Args:
        ad_id: The ID of the video ad

    Returns:
        Dictionary with video properties and ad details
    """
    with get_db_cursor() as cursor:
        cursor.execute('''
            SELECT ca.*, c.name as campaign_name
            FROM campaign_ads ca
            JOIN campaigns c ON ca.campaign_id = c.id
            WHERE ca.id = ?
        ''', (ad_id,))

        ad = cursor.fetchone()
        if not ad:
            return {
                "status": "error",
                "message": f"Ad with ID {ad_id} not found"
            }

        video_props = None
        if ad["video_properties"]:
            try:
                video_props = json.loads(ad["video_properties"])
            except json.JSONDecodeError:
                pass

        # If no properties exist, try to analyze the video
        if not video_props and ad["video_path"] and ad["status"] == "completed":
            video_filename = ad["video_path"]
            # Use storage abstraction for existence check
            if storage.video_exists(video_filename):
                properties = await analyze_video(video_filename)
                video_props = properties.model_dump()
                # Save to database
                cursor.execute('''
                    UPDATE campaign_ads SET video_properties = ? WHERE id = ?
                ''', (properties.model_dump_json(), ad_id))

        return {
            "status": "success",
            "ad_id": ad_id,
            "campaign_id": ad["campaign_id"],
            "campaign_name": ad["campaign_name"],
            "video_path": ad["video_path"],
            "video_properties": video_props,
            "has_properties": video_props is not None
        }
