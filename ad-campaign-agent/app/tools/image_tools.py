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

"""Image analysis and management tools using Gemini."""

import json
import os
import time
from typing import Optional

from google import genai
from google.genai import types
from google.adk.tools import ToolContext

from ..config import SELECTED_DIR
from ..database.db import get_db_cursor


def analyze_image(image_filename: str) -> dict:
    """Analyze a fashion image using Gemini to extract metadata.

    Analyzes the image to extract:
    - Model characteristics (gender, hair color, etc.)
    - Setting (outdoor, studio, urban, etc.)
    - Clothing details (color, style, pattern)
    - Mood/atmosphere

    This metadata is used for generating video prompts.

    Args:
        image_filename: Filename of image in the selected/ folder

    Returns:
        Dictionary with structured metadata for video prompt generation
    """
    image_path = os.path.join(SELECTED_DIR, image_filename)

    if not os.path.exists(image_path):
        return {
            "status": "error",
            "message": f"Image not found: {image_filename}"
        }

    try:
        client = genai.Client()

        # Read image file
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/jpeg"
        )

        prompt = """Analyze this fashion image and extract the following metadata in JSON format:

{
    "model_description": "Brief description of the model (e.g., 'a woman with blonde hair')",
    "clothing_description": "Detailed description of the main garment (e.g., 'a flowing floral wrap dress in pink and white')",
    "setting_description": "Description of the setting/background (e.g., 'In a sun-drenched meadow')",
    "garment_type": "Type of garment (e.g., 'summer dress', 'blazer', 'turtleneck')",
    "movement": "Suggested movement for video (e.g., 'billows gracefully in the breeze')",
    "camera_style": "Suggested camera movement (e.g., 'slowly pans around', 'smoothly circles')",
    "key_feature": "The standout feature to highlight (e.g., 'vibrant floral pattern')",
    "mood": "Overall mood/atmosphere (e.g., 'dreamy, romantic, aspirational')",
    "colors": ["list", "of", "main", "colors"],
    "style_tags": ["list", "of", "style", "descriptors"]
}

Respond ONLY with the JSON object, no additional text."""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[image_part, prompt]
        )

        # Parse the JSON response
        response_text = response.text.strip()
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        metadata = json.loads(response_text)

        return {
            "status": "success",
            "image_filename": image_filename,
            "metadata": metadata
        }

    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"Failed to parse Gemini response as JSON: {str(e)}",
            "raw_response": response.text if 'response' in dir() else None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to analyze image: {str(e)}"
        }


def add_seed_image(campaign_id: int, image_filename: str) -> dict:
    """Add a seed image from the selected/ folder to a campaign.

    Analyzes the image with Gemini and stores the metadata for video generation.

    Args:
        campaign_id: The ID of the campaign to add the image to
        image_filename: Filename of image in the selected/ folder

    Returns:
        Dictionary with image details and analysis metadata
    """
    image_path = os.path.join(SELECTED_DIR, image_filename)

    if not os.path.exists(image_path):
        # List available images
        available = [f for f in os.listdir(SELECTED_DIR) if f.endswith(('.jpg', '.jpeg', '.png'))]
        return {
            "status": "error",
            "message": f"Image not found: {image_filename}",
            "available_images": available
        }

    with get_db_cursor() as cursor:
        # Check if campaign exists
        cursor.execute('SELECT id, name FROM campaigns WHERE id = ?', (campaign_id,))
        campaign = cursor.fetchone()
        if not campaign:
            return {
                "status": "error",
                "message": f"Campaign with ID {campaign_id} not found"
            }

        # Check if image is already added to this campaign
        cursor.execute('''
            SELECT id FROM campaign_images
            WHERE campaign_id = ? AND image_path = ?
        ''', (campaign_id, image_filename))
        if cursor.fetchone():
            return {
                "status": "error",
                "message": f"Image '{image_filename}' is already added to this campaign"
            }

        # Analyze the image
        analysis_result = analyze_image(image_filename)
        if analysis_result["status"] == "error":
            return analysis_result

        metadata = analysis_result["metadata"]

        # Insert into database
        cursor.execute('''
            INSERT INTO campaign_images (campaign_id, image_path, image_type, metadata)
            VALUES (?, ?, 'seed', ?)
        ''', (campaign_id, image_filename, json.dumps(metadata)))

        image_id = cursor.lastrowid

        return {
            "status": "success",
            "message": f"Image added to campaign '{campaign['name']}'",
            "image": {
                "id": image_id,
                "campaign_id": campaign_id,
                "image_path": image_filename,
                "full_path": image_path,
                "metadata": metadata
            }
        }


def list_campaign_images(campaign_id: int) -> dict:
    """List all images for a campaign with their metadata.

    Args:
        campaign_id: The ID of the campaign

    Returns:
        Dictionary with list of images and their analysis metadata
    """
    with get_db_cursor() as cursor:
        # Check if campaign exists
        cursor.execute('SELECT id, name FROM campaigns WHERE id = ?', (campaign_id,))
        campaign = cursor.fetchone()
        if not campaign:
            return {
                "status": "error",
                "message": f"Campaign with ID {campaign_id} not found"
            }

        # Get images
        cursor.execute('''
            SELECT id, image_path, image_type, metadata, created_at
            FROM campaign_images
            WHERE campaign_id = ?
            ORDER BY created_at
        ''', (campaign_id,))

        images = []
        for row in cursor.fetchall():
            image_path = os.path.join(SELECTED_DIR, row["image_path"])
            images.append({
                "id": row["id"],
                "image_path": row["image_path"],
                "full_path": image_path,
                "exists": os.path.exists(image_path),
                "image_type": row["image_type"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                "created_at": row["created_at"]
            })

        return {
            "status": "success",
            "campaign_id": campaign_id,
            "campaign_name": campaign["name"],
            "image_count": len(images),
            "images": images
        }


def list_available_images() -> dict:
    """List all available seed images in the selected/ folder.

    Returns:
        Dictionary with list of available image filenames
    """
    if not os.path.exists(SELECTED_DIR):
        return {
            "status": "error",
            "message": f"Selected images folder not found: {SELECTED_DIR}"
        }

    images = []
    for filename in os.listdir(SELECTED_DIR):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            filepath = os.path.join(SELECTED_DIR, filename)
            images.append({
                "filename": filename,
                "full_path": filepath,
                "size_bytes": os.path.getsize(filepath)
            })

    return {
        "status": "success",
        "folder": SELECTED_DIR,
        "image_count": len(images),
        "images": images
    }


async def generate_seed_image(
    campaign_id: int,
    prompt: str,
    aspect_ratio: str = "16:9",
    tool_context: ToolContext = None
) -> dict:
    """Generate a seed image using Gemini 3 Pro Image (Nano Banana).

    Creates a fashion image based on the prompt and adds it to the campaign.
    Uses the Gemini 3 Pro Image model for high-quality image generation.

    Args:
        campaign_id: Campaign to add the generated image to
        prompt: Description of the fashion image to generate
        aspect_ratio: Image aspect ratio (16:9, 9:16, or 1:1)
        tool_context: Optional ADK ToolContext for artifact storage

    Returns:
        Dictionary with image path, metadata, and generation details
    """
    print(f"[DEBUG generate_seed_image] Starting for campaign_id={campaign_id}")
    print(f"[DEBUG generate_seed_image] Prompt: {prompt[:100]}...")
    print(f"[DEBUG generate_seed_image] Aspect ratio: {aspect_ratio}")

    # Ensure selected directory exists
    os.makedirs(SELECTED_DIR, exist_ok=True)
    print(f"[DEBUG generate_seed_image] SELECTED_DIR: {SELECTED_DIR}")

    # Validate campaign exists
    with get_db_cursor() as cursor:
        cursor.execute('SELECT id, name FROM campaigns WHERE id = ?', (campaign_id,))
        campaign = cursor.fetchone()
        if not campaign:
            print(f"[DEBUG generate_seed_image] Campaign {campaign_id} not found")
            return {
                "status": "error",
                "message": f"Campaign with ID {campaign_id} not found"
            }
        print(f"[DEBUG generate_seed_image] Found campaign: {campaign['name']}")

    try:
        print("[DEBUG generate_seed_image] Initializing genai client...")
        client = genai.Client()

        # Generate image using Gemini 3 Pro Image (Nano Banana pattern)
        print("[DEBUG generate_seed_image] Calling generate_content with gemini-3-pro-image-preview...")
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                )
            )
        )
        print(f"[DEBUG generate_seed_image] Response received, parts count: {len(response.parts) if response.parts else 0}")

        # Extract image from response parts
        generated_image = None
        for i, part in enumerate(response.parts):
            print(f"[DEBUG generate_seed_image] Part {i}: has inline_data={hasattr(part, 'inline_data') and part.inline_data is not None}")
            if part.inline_data:
                generated_image = part.as_image()
                print(f"[DEBUG generate_seed_image] Extracted image from part {i}")
                break

        if generated_image is None:
            print("[DEBUG generate_seed_image] No image found in response parts")
            return {
                "status": "error",
                "message": "No image was generated. Try a different prompt."
            }

        # Save image locally
        timestamp = int(time.time())
        filename = f"generated_seed_{campaign_id}_{timestamp}.png"
        filepath = os.path.join(SELECTED_DIR, filename)
        print(f"[DEBUG generate_seed_image] Saving image to: {filepath}")
        generated_image.save(filepath)
        print(f"[DEBUG generate_seed_image] Image saved successfully")

        # Save as ADK artifact if tool_context is provided
        if tool_context:
            print("[DEBUG generate_seed_image] Saving as ADK artifact...")
            with open(filepath, "rb") as f:
                image_bytes = f.read()
            print(f"[DEBUG generate_seed_image] Image bytes size: {len(image_bytes)}")
            image_artifact = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
            # save_artifact is async, await it properly
            version = await tool_context.save_artifact(filename=filename, artifact=image_artifact)
            print(f"[DEBUG generate_seed_image] Artifact saved, version: {version}")
        else:
            print("[DEBUG generate_seed_image] No tool_context, skipping artifact save")

        # Analyze the generated image to get metadata
        print("[DEBUG generate_seed_image] Analyzing generated image...")
        analysis_result = analyze_image(filename)
        metadata = analysis_result.get("metadata", {}) if analysis_result["status"] == "success" else {}
        print(f"[DEBUG generate_seed_image] Analysis status: {analysis_result['status']}")

        # Add to database (use 'seed' type - valid values are 'seed' or 'reference')
        print(f"[DEBUG generate_seed_image] Inserting into database: campaign_id={campaign_id}, filename={filename}, image_type='seed'")
        with get_db_cursor() as cursor:
            cursor.execute('''
                INSERT INTO campaign_images (campaign_id, image_path, image_type, metadata)
                VALUES (?, ?, 'seed', ?)
            ''', (campaign_id, filename, json.dumps(metadata)))
            image_id = cursor.lastrowid
        print(f"[DEBUG generate_seed_image] Database insert successful, image_id={image_id}")

        return {
            "status": "success",
            "message": f"Seed image generated and added to campaign '{campaign['name']}'",
            "image": {
                "id": image_id,
                "campaign_id": campaign_id,
                "image_path": filename,
                "full_path": filepath,
                "prompt_used": prompt,
                "aspect_ratio": aspect_ratio,
                "metadata": metadata,
                "artifact_saved": tool_context is not None
            }
        }

    except Exception as e:
        import traceback
        print(f"[DEBUG generate_seed_image] Exception: {str(e)}")
        print(f"[DEBUG generate_seed_image] Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Failed to generate image: {str(e)}"
        }
