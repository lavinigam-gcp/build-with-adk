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

"""Gemini image generation tool for creating infographics.

Uses Google AI Studio (API key) for authentication.
Uses gemini-3-pro-image-preview model for image generation.
Requires GOOGLE_API_KEY environment variable to be set.

Saves the generated infographic directly as an artifact using tool_context.save_artifact()
so it's accessible in adk web UI.
"""

import base64
import logging
from google.adk.tools import ToolContext
from google.genai import types
from google.genai.errors import ServerError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import IMAGE_MODEL

logger = logging.getLogger("LocationStrategyPipeline")


async def generate_infographic(data_summary: str, tool_context: ToolContext) -> dict:
    """Generate an infographic image using Gemini's image generation capabilities.

    This tool creates a professional infographic visualizing the location
    intelligence report data using Gemini 3 Pro Image model via AI Studio.

    The generated image is automatically saved as an artifact named "infographic.png"
    which can be viewed in the adk web UI.

    Args:
        data_summary: A concise summary of the location intelligence report
                     suitable for visualization. Should include:
                     - Top location name and score
                     - Key metrics (competitors, market size)
                     - Main insights (3-5 bullet points)
        tool_context: ADK ToolContext for saving artifacts and accessing state.

    Returns:
        dict: A dictionary containing:
            - status: "success" or "error"
            - message: Status message
            - artifact_saved: True if artifact was saved successfully
            - error_message: Error details (if failed)
    """
    try:
        from google import genai

        # Initialize Gemini client using AI Studio (not Vertex AI)
        # This uses GOOGLE_API_KEY from environment automatically
        client = genai.Client()

        # Create the prompt for infographic generation
        prompt = f"""Generate a professional business infographic for a location intelligence report.

DATA TO VISUALIZE:
{data_summary}

DESIGN REQUIREMENTS:
- Professional, clean business style
- Use a blue and green color palette
- Include clear visual hierarchy
- Show key metrics prominently
- Include icons or simple graphics for each section
- Make it suitable for executive presentations
- 16:9 aspect ratio for presentations

Create an infographic that a business executive would use in a board presentation.
"""

        # Retry wrapper for handling model overload errors
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=2, min=2, max=30),
            retry=retry_if_exception_type(ServerError),
            before_sleep=lambda retry_state: logger.warning(
                f"Gemini API error, retrying in {retry_state.next_action.sleep} seconds... "
                f"(attempt {retry_state.attempt_number}/3)"
            ),
        )
        def generate_with_retry():
            return client.models.generate_content(
                model=IMAGE_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio="16:9",
                    ),
                ),
            )

        # Generate the image using Gemini 3 Pro Image model
        response = generate_with_retry()

        # Check for successful generation
        if response.candidates and len(response.candidates) > 0:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/png"

                    # Save the image directly as an artifact using tool_context
                    # This is the recommended ADK pattern for saving binary artifacts
                    # Note: save_artifact is async, so we must await it
                    try:
                        image_artifact = types.Part.from_bytes(
                            data=image_bytes,
                            mime_type=mime_type
                        )
                        artifact_filename = "infographic.png"
                        version = await tool_context.save_artifact(
                            filename=artifact_filename,
                            artifact=image_artifact
                        )
                        logger.info(f"Saved infographic artifact: {artifact_filename} (version {version})")

                        # Also store base64 in state for AG-UI frontend display
                        b64_image = base64.b64encode(image_bytes).decode('utf-8')
                        tool_context.state["infographic_base64"] = f"data:{mime_type};base64,{b64_image}"

                        return {
                            "status": "success",
                            "message": f"Infographic generated and saved as artifact '{artifact_filename}'",
                            "artifact_saved": True,
                            "artifact_filename": artifact_filename,
                            "artifact_version": version,
                            "mime_type": mime_type,
                        }
                    except Exception as save_error:
                        logger.warning(f"Failed to save artifact: {save_error}")
                        # Still return success with base64 data as fallback
                        return {
                            "status": "success",
                            "message": "Infographic generated but artifact save failed",
                            "artifact_saved": False,
                            "image_data": base64.b64encode(image_bytes).decode("utf-8"),
                            "mime_type": mime_type,
                            "save_error": str(save_error),
                        }

        # No image found in response
        return {
            "status": "error",
            "error_message": "No image was generated in the response. The model may have returned text only.",
        }

    except Exception as e:
        logger.error(f"Failed to generate infographic: {e}")
        return {
            "status": "error",
            "error_message": f"Failed to generate infographic: {str(e)}",
        }
