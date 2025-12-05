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

"""Test script for deployed Retail AI Location Strategy Agent.

Usage:
    python test_deployment.py --resource_id=RESOURCE_ID --user_id=test_user
"""

import argparse
import os
import sys


def test_agent(resource_id: str, user_id: str, message: str):
    """Test the deployed agent with a sample query."""
    import vertexai
    from vertexai import agent_engines

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project:
        print("Error: GOOGLE_CLOUD_PROJECT not set")
        sys.exit(1)

    print(f"Connecting to project: {project}, location: {location}")
    print(f"Agent: {resource_id}")
    print(f"User: {user_id}")
    print(f"Message: {message}\n")

    vertexai.init(project=project, location=location)

    # Get the agent
    agent_engine = agent_engines.get(resource_id)

    # Create a session
    session = agent_engine.create_session(user_id=user_id)
    print(f"Session created: {session['id']}\n")

    # Stream the response
    print("Agent Response:")
    print("-" * 50)

    for event in agent_engine.stream_query(
        user_id=user_id,
        session_id=session["id"],
        message=message,
    ):
        if "content" in event and "parts" in event["content"]:
            for part in event["content"]["parts"]:
                if "text" in part:
                    print(part["text"], end="", flush=True)

    print("\n" + "-" * 50)
    print("Test completed successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="Test deployed Retail AI Location Strategy Agent"
    )
    parser.add_argument(
        "--resource_id",
        type=str,
        required=True,
        help="Resource ID of the deployed agent"
    )
    parser.add_argument(
        "--user_id",
        type=str,
        default="test_user",
        help="User ID for the session"
    )
    parser.add_argument(
        "--message",
        type=str,
        default="I want to open a coffee shop in Indiranagar, Bangalore",
        help="Message to send to the agent"
    )

    args = parser.parse_args()

    test_agent(args.resource_id, args.user_id, args.message)


if __name__ == "__main__":
    main()
