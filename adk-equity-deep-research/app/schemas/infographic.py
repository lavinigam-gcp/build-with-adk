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

"""Infographic generation schemas."""

from typing import Literal
from pydantic import BaseModel, Field


class InfographicSpec(BaseModel):
    """Specification for an infographic to generate."""

    infographic_id: int = Field(
        description="Unique identifier for this infographic (1, 2, 3)"
    )
    title: str = Field(
        description="Title of the infographic (e.g., 'Business Model Overview')"
    )
    infographic_type: Literal["business_model", "competitive_landscape", "growth_drivers"] = Field(
        description="Type of infographic to generate"
    )
    key_elements: list[str] = Field(
        description="List of key elements/data points to include in the infographic"
    )
    visual_style: str = Field(
        default="modern, professional, corporate color scheme",
        description="Visual style description for the infographic"
    )
    prompt: str = Field(
        description="Detailed prompt for image generation"
    )


class InfographicPlan(BaseModel):
    """Plan for all infographics to generate."""

    company_name: str = Field(
        description="Company name for context"
    )
    infographics: list[InfographicSpec] = Field(
        description="List of 3 infographics to generate"
    )


class InfographicResult(BaseModel):
    """Result of infographic generation."""

    infographic_id: int = Field(
        description="Infographic number (1, 2, 3)"
    )
    title: str = Field(
        description="Title of the generated infographic"
    )
    filename: str = Field(
        description="Artifact filename (e.g., 'infographic_1.png')"
    )
    base64_data: str = Field(
        description="Base64 encoded infographic image"
    )
    infographic_type: str = Field(
        description="Type of infographic"
    )
