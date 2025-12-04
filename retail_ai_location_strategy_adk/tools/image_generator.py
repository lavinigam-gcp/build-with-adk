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

Uses Google AI Studio (API key) for authentication instead of Vertex AI.
Requires GOOGLE_API_KEY environment variable to be set.
"""

import base64
from google.adk.tools import ToolContext


def generate_infographic(data_summary: str, tool_context: ToolContext) -> dict:
    """Generate an infographic image using Gemini's image generation capabilities.

    This tool creates a professional infographic visualizing the location
    intelligence report data using Gemini's multimodal generation via AI Studio.

    Args:
        data_summary: A concise summary of the location intelligence report
                     suitable for visualization. Should include:
                     - Top location name and score
                     - Key metrics (competitors, market size)
                     - Main insights (3-5 bullet points)

    Returns:
        dict: A dictionary containing:
            - status: "success" or "error"
            - message: Status message
            - image_data: Base64 encoded image data (if successful)
            - mime_type: MIME type of the image (if successful)
            - error_message: Error details (if failed)
    """
    try:
        from google import genai
        from google.genai import types

        # Initialize Gemini client using AI Studio (not Vertex AI)
        # This uses GOOGLE_API_KEY from environment automatically
        client = genai.Client(vertexai=False)

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

        # Generate the image
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(aspect_ratio="16:9"),
            ),
        )

        # Check for successful generation
        if response.candidates and response.candidates[0].finish_reason.name == "STOP":
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type

                    return {
                        "status": "success",
                        "message": "Infographic generated successfully",
                        "image_data": base64.b64encode(image_bytes).decode("utf-8"),
                        "mime_type": mime_type,
                    }

        # No image found in response
        return {
            "status": "error",
            "error_message": "No image was generated in the response. The model may have returned text only.",
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to generate infographic: {str(e)}",
        }
