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

"""Deploy script for Retail AI Location Strategy Agent to Vertex AI Agent Engine.

Usage:
    python deploy.py --create              # Deploy agent
    python deploy.py --list                # List deployed agents
    python deploy.py --delete --resource_id=ID  # Delete agent
"""

import argparse
import glob
import os
import sys
from pathlib import Path

# Add parent directory to path to import agent
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_project_config():
    """Get Google Cloud project configuration from environment."""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project:
        # Try to get from gcloud config
        import subprocess
        try:
            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True,
                text=True,
                check=True
            )
            project = result.stdout.strip()
        except Exception:
            pass

    if not project:
        print("Error: GOOGLE_CLOUD_PROJECT not set.")
        print("Set it with: export GOOGLE_CLOUD_PROJECT=your-project-id")
        print("Or run: gcloud config set project your-project-id")
        sys.exit(1)

    return project, location


def create_staging_bucket(project: str, location: str) -> str:
    """Create a staging bucket for deployment if it doesn't exist."""
    from google.cloud import storage

    bucket_name = f"{project}-adk-staging"
    client = storage.Client(project=project)

    try:
        bucket = client.get_bucket(bucket_name)
        print(f"Using existing staging bucket: gs://{bucket_name}")
    except Exception:
        print(f"Creating staging bucket: gs://{bucket_name}")
        bucket = client.create_bucket(bucket_name, location=location)

    return f"gs://{bucket_name}"


def find_wheel_file() -> str:
    """Find the wheel file in the deployment directory."""
    wheel_files = glob.glob("*.whl")
    if not wheel_files:
        print("Error: No wheel file found in deployment directory.")
        print("Run 'uv build --wheel --out-dir deployment' first.")
        sys.exit(1)
    return wheel_files[0]


def deploy_agent(project: str, location: str):
    """Deploy agent to Vertex AI Agent Engine."""
    import vertexai
    from vertexai import agent_engines

    print(f"Deploying to project: {project}, location: {location}")

    # Initialize Vertex AI
    vertexai.init(project=project, location=location)

    # Create staging bucket
    staging_bucket = create_staging_bucket(project, location)

    # Find wheel file
    wheel_file = find_wheel_file()
    print(f"Using wheel file: {wheel_file}")

    # Import the agent
    from retail_ai_location_strategy_adk.agent import root_agent

    # Define requirements
    requirements = [
        wheel_file,
        "google-cloud-aiplatform[adk,agent_engines]>=1.79.0",
        "cloudpickle>=3.0.0",
        "googlemaps>=4.10.0",
        "pydantic>=2.10.0",
    ]

    print("Creating agent engine...")
    agent_engine = agent_engines.create(
        agent=root_agent,
        requirements=requirements,
        display_name="retail-location-strategy-agent",
        description="Multi-agent AI pipeline for retail site selection",
        staging_bucket=staging_bucket,
    )

    resource_id = agent_engine.resource_name
    print(f"\nDeployment successful!")
    print(f"Resource ID: {resource_id}")

    # Save to .env file
    env_file = Path(__file__).parent.parent / ".env"
    with open(env_file, "a") as f:
        f.write(f"\n# Deployed Agent Engine ID\nAGENT_ENGINE_ID={resource_id}\n")
    print(f"Resource ID saved to {env_file}")

    return resource_id


def list_agents(project: str, location: str):
    """List deployed agents."""
    import vertexai
    from vertexai import agent_engines

    vertexai.init(project=project, location=location)

    print(f"Listing agents in project: {project}, location: {location}\n")

    agents = agent_engines.list()
    for agent in agents:
        print(f"Name: {agent.display_name}")
        print(f"Resource: {agent.resource_name}")
        print(f"Created: {agent.create_time}")
        print("-" * 50)


def delete_agent(resource_id: str, project: str, location: str):
    """Delete a deployed agent."""
    import vertexai
    from vertexai import agent_engines

    vertexai.init(project=project, location=location)

    print(f"Deleting agent: {resource_id}")

    agent = agent_engines.get(resource_id)
    agent.delete()

    print("Agent deleted successfully.")


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Retail AI Location Strategy Agent to Vertex AI Agent Engine"
    )
    parser.add_argument("--create", action="store_true", help="Create/deploy the agent")
    parser.add_argument("--list", action="store_true", help="List deployed agents")
    parser.add_argument("--delete", action="store_true", help="Delete an agent")
    parser.add_argument("--resource_id", type=str, help="Resource ID for deletion")

    args = parser.parse_args()

    if not any([args.create, args.list, args.delete]):
        parser.print_help()
        sys.exit(1)

    project, location = get_project_config()

    if args.create:
        deploy_agent(project, location)
    elif args.list:
        list_agents(project, location)
    elif args.delete:
        if not args.resource_id:
            print("Error: --resource_id required for deletion")
            sys.exit(1)
        delete_agent(args.resource_id, project, location)


if __name__ == "__main__":
    main()
