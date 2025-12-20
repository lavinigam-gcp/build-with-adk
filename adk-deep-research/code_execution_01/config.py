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

"""Configuration for the Financial Data Visualization Agent."""

import os
from dataclasses import dataclass


@dataclass
class AgentConfiguration:
    """Configuration for agent models and parameters.

    Attributes:
        model: Model for all agents in the pipeline.
        use_agent_engine_sandbox: Whether to use Agent Engine Sandbox (cloud)
            instead of local Vertex AI code execution.
        sandbox_resource_name: Resource name for Agent Engine Sandbox (if using).
        agent_engine_resource_name: Agent Engine resource name for sandbox creation.
    """

    # Model configuration
    model: str = "gemini-2.5-flash"

    # Code execution configuration
    use_agent_engine_sandbox: bool = False
    sandbox_resource_name: str | None = None
    agent_engine_resource_name: str | None = None

    # Chart configuration
    chart_dpi: int = 150
    chart_figsize: tuple[int, int] = (12, 6)
    chart_style: str = "ggplot"  # Use matplotlib built-in style (seaborn not available)

    def __post_init__(self):
        """Load configuration from environment variables if available."""
        self.model = os.getenv("AGENT_MODEL", self.model)
        self.use_agent_engine_sandbox = os.getenv(
            "USE_AGENT_ENGINE_SANDBOX", "false"
        ).lower() == "true"
        self.sandbox_resource_name = os.getenv("SANDBOX_RESOURCE_NAME")
        self.agent_engine_resource_name = os.getenv("AGENT_ENGINE_RESOURCE_NAME")


config = AgentConfiguration()
