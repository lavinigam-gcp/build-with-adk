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
from typing import Optional

from PIL import Image as PILImage
from google import genai
from google.genai import types
from google.adk.tools import ToolContext

from ..config import SELECTED_DIR, GENERATED_DIR
from ..database.db import get_db_cursor
from ..database.mock_data import generate_mock_metrics


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

    # Ensure generated directory exists
    os.makedirs(GENERATED_DIR, exist_ok=True)
    print(f"[DEBUG generate_video_ad] GENERATED_DIR: {GENERATED_DIR}")

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

        image_path = os.path.join(SELECTED_DIR, image_row["image_path"])
        print(f"[DEBUG generate_video_ad] Full image path: {image_path}")
        if not os.path.exists(image_path):
            print(f"[DEBUG generate_video_ad] Image file not found: {image_path}")
            return {
                "status": "error",
                "message": f"Image file not found: {image_path}"
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

        # Load image using PIL and convert to bytes for Veo API
        # This follows the official Veo documentation pattern
        print(f"[DEBUG generate_video_ad] Loading image with PIL...")
        with PILImage.open(image_path) as im:
            print(f"[DEBUG generate_video_ad] Image format: {im.format}, size: {im.size}")
            image_bytes_io = io.BytesIO()
            img_format = im.format or "JPEG"
            im.save(image_bytes_io, format=img_format)
            image_bytes = image_bytes_io.getvalue()
            print(f"[DEBUG generate_video_ad] Image bytes size: {len(image_bytes)}")

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

        # Download and save the generated video
        # MUST call client.files.download() before saving per official docs
        generated_video = operation.result.generated_videos[0]
        print(f"[DEBUG generate_video_ad] Downloading video...")
        client.files.download(file=generated_video.video)
        timestamp = int(time.time())
        output_filename = f"campaign_{campaign_id}_ad_{ad_id}_{timestamp}.mp4"
        output_path = os.path.join(GENERATED_DIR, output_filename)
        print(f"[DEBUG generate_video_ad] Saving video to: {output_path}")
        generated_video.video.save(output_path)
        print(f"[DEBUG generate_video_ad] Video saved successfully")

        # Save as ADK artifact if tool_context is provided
        if tool_context:
            print(f"[DEBUG generate_video_ad] Saving as ADK artifact...")
            with open(output_path, "rb") as f:
                video_bytes = f.read()
            print(f"[DEBUG generate_video_ad] Video bytes size: {len(video_bytes)}")
            video_artifact = types.Part.from_bytes(data=video_bytes, mime_type="video/mp4")
            # save_artifact is async, await it properly
            version = await tool_context.save_artifact(filename=output_filename, artifact=video_artifact)
            print(f"[DEBUG generate_video_ad] Artifact saved, version: {version}")
        else:
            print(f"[DEBUG generate_video_ad] No tool_context, skipping artifact save")

        # Update database with video path
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE campaign_ads
                SET video_path = ?, status = 'completed'
                WHERE id = ?
            ''', (output_filename, ad_id))

        # Auto-generate mock metrics for the new ad (90 days of data)
        print(f"[DEBUG generate_video_ad] Generating mock metrics for ad_id={ad_id}...")
        mock_metrics = generate_mock_metrics(campaign_id, ad_id, days=90)
        with get_db_cursor() as cursor:
            for metric in mock_metrics:
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
            }
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

    valid_characteristics = ["mood", "setting", "camera_style", "movement", "key_feature"]

    if characteristics_to_apply:
        invalid = [c for c in characteristics_to_apply if c not in valid_characteristics]
        if invalid:
            return {
                "status": "error",
                "message": f"Invalid characteristics: {invalid}. Valid options: {valid_characteristics}"
            }

    with get_db_cursor() as cursor:
        # Step 1: Get source ad (top performer or specified)
        if source_ad_id:
            print(f"[DEBUG apply_winning_formula] Using specified source_ad_id={source_ad_id}")
            cursor.execute('''
                SELECT ca.*, ci.metadata, ci.image_path as source_image,
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
                SELECT ca.*, ci.metadata, ci.image_path as source_image,
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

        # Step 2: Extract winning characteristics from source ad metadata
        source_metadata = json.loads(source_ad["metadata"]) if source_ad["metadata"] else {}

        winning_formula = {
            "mood": source_metadata.get("mood", "elegant, aspirational"),
            "setting": source_metadata.get("setting_description", "beautiful setting"),
            "camera_style": source_metadata.get("camera_style", "smoothly captures"),
            "movement": source_metadata.get("movement", "moves gracefully"),
            "key_feature": source_metadata.get("key_feature", "the details"),
            "model_description": source_metadata.get("model_description", "a model"),
        }

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

    # Determine which characteristics to apply
    chars_to_use = characteristics_to_apply if characteristics_to_apply else ["mood", "setting", "camera_style", "movement"]

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

    # Construct the winning formula prompt
    winning_prompt = f"""A cinematic fashion video featuring {model_desc} wearing {clothing_desc}. {setting_desc}, the {garment_type} {movement}. Camera {camera_style}, capturing {key_feature}. Atmosphere: {mood}. Professional lighting, high-end fashion advertisement style."""

    print(f"[DEBUG apply_winning_formula] Generated prompt with winning formula:")
    print(f"[DEBUG apply_winning_formula] {winning_prompt[:200]}...")
    print(f"[DEBUG apply_winning_formula] Applied characteristics: {chars_to_use}")

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
            video_path = os.path.join(GENERATED_DIR, row["video_path"]) if row["video_path"] else None
            ads.append({
                "id": row["id"],
                "video_path": row["video_path"],
                "full_path": video_path,
                "exists": os.path.exists(video_path) if video_path else False,
                "prompt_used": row["prompt_used"],
                "duration_seconds": row["duration_seconds"],
                "status": row["status"],
                "source_image": row["source_image"],
                "created_at": row["created_at"]
            })

        return {
            "status": "success",
            "campaign_id": campaign_id,
            "campaign_name": campaign["name"],
            "ad_count": len(ads),
            "ads": ads
        }
