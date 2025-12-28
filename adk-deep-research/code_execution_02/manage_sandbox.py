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

"""
Sandbox Management Script for Financial Data Visualization Agent
================================================================

This script provides utilities to manage Agent Engine Sandboxes:
- Create a new sandbox (pre-create before running adk web)
- List existing sandboxes
- Delete sandboxes
- Get sandbox details

Usage:
    python manage_sandbox.py create --name "financial_viz_sandbox"
    python manage_sandbox.py list
    python manage_sandbox.py delete --sandbox-id "projects/.../sandboxes/..."
    python manage_sandbox.py get --sandbox-id "projects/.../sandboxes/..."

After creating a sandbox, set the environment variable:
    export SANDBOX_RESOURCE_NAME="projects/.../sandboxes/..."

Then run the agent:
    adk web code_execution_01
"""

import argparse
import os
import sys

import vertexai
from vertexai import types


def get_client():
    """Initialize and return Vertex AI client."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project_id:
        print("Error: GOOGLE_CLOUD_PROJECT environment variable not set")
        sys.exit(1)

    vertexai.init(project=project_id, location=location)
    return vertexai.Client(project=project_id, location=location)


def get_or_create_agent_engine(client):
    """Get existing agent engine or create a new one."""
    agent_engine_name = os.environ.get("AGENT_ENGINE_RESOURCE_NAME")

    if agent_engine_name:
        print(f"Using existing Agent Engine: {agent_engine_name}")
        return agent_engine_name

    # Create a new Agent Engine
    print("Creating new Agent Engine...")
    agent_engine = client.agent_engines.create()
    agent_engine_name = agent_engine.api_resource.name
    print(f"Created Agent Engine: {agent_engine_name}")
    print(f"\nSet this environment variable to reuse:")
    print(f'  export AGENT_ENGINE_RESOURCE_NAME="{agent_engine_name}"')

    return agent_engine_name


def create_sandbox(
    client,
    agent_engine_name: str,
    display_name: str = "financial_viz_sandbox",
    language: str = "LANGUAGE_PYTHON",
    machine_config: str = "MACHINE_CONFIG_VCPU4_RAM4GIB",
):
    """Create a new sandbox with specified configuration."""
    print(f"\nCreating sandbox '{display_name}'...")
    print(f"  Language: {language}")
    print(f"  Machine config: {machine_config}")

    sandbox_operation = client.agent_engines.sandboxes.create(
        name=agent_engine_name,
        config=types.CreateAgentEngineSandboxConfig(display_name=display_name),
        spec={
            "code_execution_environment": {
                "code_language": language,
                "machine_config": machine_config,
            }
        },
    )

    sandbox_resource_name = sandbox_operation.response.name
    sandbox_state = sandbox_operation.response.state

    print(f"\nSandbox created successfully!")
    print(f"  Resource name: {sandbox_resource_name}")
    print(f"  State: {sandbox_state}")
    print(f"\nTo use this sandbox, set the environment variable:")
    print(f'  export SANDBOX_RESOURCE_NAME="{sandbox_resource_name}"')
    print(f"\nOr add to your .env file:")
    print(f'  SANDBOX_RESOURCE_NAME="{sandbox_resource_name}"')

    return sandbox_resource_name


def list_sandboxes(client, agent_engine_name: str):
    """List all sandboxes in the agent engine."""
    print(f"\nListing sandboxes for Agent Engine: {agent_engine_name}")

    sandboxes = client.agent_engines.sandboxes.list(name=agent_engine_name)

    if not sandboxes:
        print("No sandboxes found.")
        return

    print(f"\nFound {len(sandboxes)} sandbox(es):\n")
    print("-" * 80)

    for i, sandbox in enumerate(sandboxes, 1):
        print(f"\n[{i}] {sandbox.display_name}")
        print(f"    Resource name: {sandbox.name}")
        print(f"    State: {sandbox.state}")
        print(f"    Created: {sandbox.create_time}")
        if hasattr(sandbox, "expire_time") and sandbox.expire_time:
            print(f"    Expires: {sandbox.expire_time}")

    print("\n" + "-" * 80)


def get_sandbox(client, sandbox_name: str):
    """Get details of a specific sandbox."""
    print(f"\nGetting sandbox details: {sandbox_name}")

    try:
        sandbox = client.agent_engines.sandboxes.get(name=sandbox_name)

        print(f"\nSandbox Details:")
        print(f"  Display name: {sandbox.display_name}")
        print(f"  Resource name: {sandbox.name}")
        print(f"  State: {sandbox.state}")
        print(f"  Created: {sandbox.create_time}")
        if hasattr(sandbox, "expire_time") and sandbox.expire_time:
            print(f"  Expires: {sandbox.expire_time}")
        print(f"  Spec: {sandbox.spec}")

        return sandbox
    except Exception as e:
        print(f"Error getting sandbox: {e}")
        return None


def delete_sandbox(client, sandbox_name: str):
    """Delete a specific sandbox."""
    print(f"\nDeleting sandbox: {sandbox_name}")

    try:
        delete_operation = client.agent_engines.sandboxes.delete(name=sandbox_name)

        if delete_operation.done:
            print("Sandbox deleted successfully!")
        else:
            print("Deletion in progress...")

        return True
    except Exception as e:
        print(f"Error deleting sandbox: {e}")
        return False


def test_sandbox(client, sandbox_name: str):
    """Test the sandbox by executing simple code."""
    print(f"\nTesting sandbox: {sandbox_name}")

    test_code = """
import sys
print("Python version:", sys.version)
print("\\nPre-imported libraries test:")

# Test matplotlib
import matplotlib
print(f"  matplotlib: {matplotlib.__version__}")

# Test numpy
import numpy as np
print(f"  numpy: {np.__version__}")

# Test pandas
import pandas as pd
print(f"  pandas: {pd.__version__}")

# Test seaborn (needs explicit import)
try:
    import seaborn as sns
    print(f"  seaborn: {sns.__version__}")
except ImportError:
    print("  seaborn: NOT AVAILABLE (needs explicit import in code)")

print("\\nSandbox is working correctly!")
"""

    try:
        import json

        response = client.agent_engines.sandboxes.execute_code(
            name=sandbox_name, input_data={"code": test_code}
        )

        print("\nExecution result:")
        for output in response.outputs:
            if output.mime_type == "application/json" and output.metadata is None:
                result = json.loads(output.data.decode("utf-8"))
                if result.get("msg_out"):
                    print(result.get("msg_out"))
                if result.get("msg_err"):
                    print(f"Error: {result.get('msg_err')}")

        return True
    except Exception as e:
        print(f"Error testing sandbox: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Manage Agent Engine Sandboxes for code execution"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new sandbox")
    create_parser.add_argument(
        "--name",
        default="financial_viz_sandbox",
        help="Display name for the sandbox",
    )
    create_parser.add_argument(
        "--language",
        default="LANGUAGE_PYTHON",
        choices=["LANGUAGE_PYTHON", "LANGUAGE_JAVASCRIPT", "LANGUAGE_UNSPECIFIED"],
        help="Programming language runtime",
    )
    create_parser.add_argument(
        "--machine",
        default="MACHINE_CONFIG_VCPU4_RAM4GIB",
        choices=["MACHINE_CONFIG_VCPU4_RAM4GIB", "MACHINE_CONFIG_UNSPECIFIED"],
        help="Machine configuration",
    )

    # List command
    subparsers.add_parser("list", help="List all sandboxes")

    # Get command
    get_parser = subparsers.add_parser("get", help="Get sandbox details")
    get_parser.add_argument(
        "--sandbox-id",
        required=True,
        help="Sandbox resource name",
    )

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a sandbox")
    delete_parser.add_argument(
        "--sandbox-id",
        required=True,
        help="Sandbox resource name to delete",
    )

    # Test command
    test_parser = subparsers.add_parser("test", help="Test a sandbox")
    test_parser.add_argument(
        "--sandbox-id",
        help="Sandbox resource name (uses SANDBOX_RESOURCE_NAME env var if not provided)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize client
    client = get_client()

    if args.command == "create":
        agent_engine_name = get_or_create_agent_engine(client)
        create_sandbox(
            client,
            agent_engine_name,
            display_name=args.name,
            language=args.language,
            machine_config=args.machine,
        )

    elif args.command == "list":
        agent_engine_name = os.environ.get("AGENT_ENGINE_RESOURCE_NAME")
        if not agent_engine_name:
            print("Error: AGENT_ENGINE_RESOURCE_NAME environment variable not set")
            print("Run 'python manage_sandbox.py create' first to create an agent engine")
            sys.exit(1)
        list_sandboxes(client, agent_engine_name)

    elif args.command == "get":
        get_sandbox(client, args.sandbox_id)

    elif args.command == "delete":
        delete_sandbox(client, args.sandbox_id)

    elif args.command == "test":
        sandbox_id = args.sandbox_id or os.environ.get("SANDBOX_RESOURCE_NAME")
        if not sandbox_id:
            print("Error: No sandbox ID provided and SANDBOX_RESOURCE_NAME not set")
            sys.exit(1)
        test_sandbox(client, sandbox_id)


if __name__ == "__main__":
    main()
