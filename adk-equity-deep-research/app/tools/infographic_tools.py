# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Infographic generation tools using Gemini image generation models."""

import asyncio
import base64
import os
from datetime import datetime

from google import genai
from google.genai import types as genai_types
from google.adk.tools import ToolContext

from app.config import IMAGE_MODEL


async def generate_infographic(
    prompt: str,
    infographic_id: int,
    title: str,
    tool_context: ToolContext
) -> dict:
    """Generate an infographic image using Gemini 3 Pro Image model.

    Args:
        prompt: Detailed prompt for the infographic
        infographic_id: ID number for this infographic (1, 2, or 3)
        title: Title of the infographic
        tool_context: ADK tool context for state and artifact access

    Returns:
        dict with success status and infographic details
    """
    print(f"Generating infographic {infographic_id}: {title}")

    try:
        # Initialize Vertex AI client
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location
        )

        # Generate infographic with Gemini 3 Pro Image model
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=genai_types.ImageConfig(
                    aspect_ratio="1:1",        # Square format for professional reports
                    image_size="2K"             # High quality for presentations
                ),
            ),
        )

        # Extract image from response
        image_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                image_bytes = part.inline_data.data
                break

        if not image_bytes:
            print(f"Warning: No image generated for infographic {infographic_id}")
            return {
                "success": False,
                "error": "No image generated",
                "infographic_id": infographic_id
            }

        # Save as artifact
        filename = f"infographic_{infographic_id}.png"
        image_artifact = genai_types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/png"
        )
        version = await tool_context.save_artifact(
            filename=filename,
            artifact=image_artifact
        )
        print(f"Saved infographic artifact '{filename}' as version {version}")

        # Store base64 for HTML embedding
        infographic_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Store in state
        state = tool_context.state
        infographics_generated = state.get("infographics_generated", [])
        infographic_result = {
            "infographic_id": infographic_id,
            "title": title,
            "filename": filename,
            "base64_data": infographic_base64,
            "infographic_type": "generated"
        }
        infographics_generated.append(infographic_result)
        state["infographics_generated"] = infographics_generated

        print(f"Infographic {infographic_id} ({title}) generated successfully")

        return {
            "success": True,
            "infographic_id": infographic_id,
            "title": title,
            "filename": filename,
            "message": f"Infographic '{title}' generated and saved as {filename}"
        }

    except Exception as e:
        error_msg = f"Error generating infographic {infographic_id}: {str(e)}"
        print(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "infographic_id": infographic_id
        }


async def generate_all_infographics(
    infographic_plan: dict,  # JSON serialized InfographicPlan
    tool_context: ToolContext
) -> dict:
    """Generate ALL infographics from plan in parallel using asyncio.gather().

    This is the batch tool that handles 2-5 infographics dynamically based on plan.

    Args:
        infographic_plan: Complete infographic plan with 2-5 infographic specs
        tool_context: ADK tool context for state and artifact access

    Returns:
        dict with success status and list of generated infographics
    """
    print("\n" + "="*80)
    print("BATCH INFOGRAPHIC GENERATION - START")
    print("="*80)

    print(f"🔧 Tool Context - State access available: {hasattr(tool_context, 'state')}")

    # Extract infographics list from plan
    infographics_specs = infographic_plan.get("infographics", [])
    total_count = len(infographics_specs)

    print(f"📊 Plan contains {total_count} infographics to generate")
    print(f"📋 Infographic IDs: {[spec['infographic_id'] for spec in infographics_specs]}")
    print(f"📋 Titles: {[spec['title'] for spec in infographics_specs]}")

    if total_count == 0:
        print("⚠️  WARNING: No infographics in plan, skipping generation")
        return {
            "success": False,
            "error": "No infographics in plan",
            "total_requested": 0,
            "successfully_generated": 0,
            "results": []
        }

    # Initialize Vertex AI client (shared across all generations)
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    print(f"🔧 Initializing Vertex AI client (project={project_id}, location={location})")

    client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location
    )

    async def generate_single(infographic_spec: dict, index: int) -> dict:
        """Generate one infographic asynchronously with detailed logging."""
        infographic_id = infographic_spec.get("infographic_id")
        title = infographic_spec.get("title", f"Infographic {infographic_id}")
        prompt = infographic_spec.get("prompt", "")
        infographic_type = infographic_spec.get("infographic_type", "unknown")

        print(f"\n🎨 [{index+1}/{total_count}] Starting generation for infographic #{infographic_id}")
        print(f"   Title: {title}")
        print(f"   Type: {infographic_type}")
        print(f"   Prompt length: {len(prompt)} chars")

        try:
            # Generate with Gemini 3 Pro Image
            print(f"   ⏳ Calling Gemini 3 Pro Image API...")
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=genai_types.ImageConfig(
                        aspect_ratio="1:1",
                        image_size="2K"
                    ),
                ),
            )

            print(f"   ✓ API response received for infographic #{infographic_id}")

            # Extract image bytes
            image_bytes = None
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    image_bytes = part.inline_data.data
                    print(f"   ✓ Image data extracted ({len(image_bytes)} bytes)")
                    break

            if not image_bytes:
                print(f"   ✗ ERROR: No image data in API response for infographic #{infographic_id}")
                return {
                    "success": False,
                    "error": "No image generated in API response",
                    "infographic_id": infographic_id
                }

            # Save as artifact
            filename = f"infographic_{infographic_id}.png"
            image_artifact = genai_types.Part.from_bytes(
                data=image_bytes,
                mime_type="image/png"
            )
            version = await tool_context.save_artifact(
                filename=filename,
                artifact=image_artifact
            )
            print(f"   ✓ Saved artifact '{filename}' (version {version})")

            # Encode as base64 for HTML embedding
            infographic_base64 = base64.b64encode(image_bytes).decode('utf-8')

            result = {
                "success": True,
                "infographic_id": infographic_id,
                "title": title,
                "filename": filename,
                "base64_data": infographic_base64,
                "infographic_type": infographic_type
            }

            print(f"   ✅ Infographic #{infographic_id} completed successfully!")
            return result

        except Exception as e:
            error_msg = str(e)
            print(f"   ✗ ERROR generating infographic #{infographic_id}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "infographic_id": infographic_id
            }

    # Generate all infographics in parallel using asyncio.gather
    print(f"\n🚀 Launching {total_count} parallel image generations...")
    print(f"⏱️  Start time: {datetime.now().strftime('%H:%M:%S')}")

    tasks = [
        generate_single(spec, idx)
        for idx, spec in enumerate(infographics_specs)
    ]

    results = await asyncio.gather(*tasks)

    print(f"⏱️  End time: {datetime.now().strftime('%H:%M:%S')}")

    # Filter successful results
    successful_results = [r for r in results if r.get("success")]
    failed_results = [r for r in results if not r.get("success")]

    success_count = len(successful_results)
    failure_count = len(failed_results)

    print(f"\n📈 GENERATION SUMMARY:")
    print(f"   ✅ Successful: {success_count}/{total_count}")
    print(f"   ✗ Failed: {failure_count}/{total_count}")

    if failed_results:
        print(f"\n⚠️  Failed infographics:")
        for failed in failed_results:
            print(f"   - Infographic #{failed.get('infographic_id')}: {failed.get('error')}")

    # Save all successful results to state
    tool_context.state["infographics_generated"] = successful_results
    print(f"\n💾 Saved {success_count} infographics to state['infographics_generated']")

    print("="*80)
    print("BATCH INFOGRAPHIC GENERATION - COMPLETE")
    print("="*80 + "\n")

    # Create lightweight summary for tool response (NO base64 data)
    # Base64 is already saved in state["infographics_generated"] for callback/HTML use
    summary_results = [
        {
            "infographic_id": r.get("infographic_id"),
            "title": r.get("title"),
            "infographic_type": r.get("infographic_type"),
            "filename": r.get("filename"),
            # Explicitly NOT including base64_data to keep conversation history clean
        }
        for r in successful_results
    ]

    print(f"📤 Tool response size: ~{len(str(summary_results))} chars (metadata only, no base64)")

    return {
        "success": success_count > 0,
        "total_requested": total_count,
        "successfully_generated": success_count,
        "failed": failure_count,
        "summary": summary_results,  # Only metadata, not full results
        "message": f"Generated {success_count}/{total_count} infographics successfully. Full data saved to state."
    }
