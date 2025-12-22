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

"""Deploy Ad Campaign Agent to Agent Engine using Python SDK (Inline Deployment).

This script uses "inline deployment" to set location='global',
which is required for Gemini 3 models (gemini-3-flash-preview, etc.).

The Python SDK allows vertexai.init(location='global') which bypasses
the CLI limitation where --region=global throws errors.

Usage:
    python scripts/deploy_ae_inline.py                  # Deploy with global region
    python scripts/deploy_ae_inline.py --trace          # Deploy with Cloud Trace
    python scripts/deploy_ae_inline.py --dry-run        # Show config without deploying
    python scripts/deploy_ae_inline.py --region=us-central1  # Override region if needed

Environment Variables:
    GOOGLE_CLOUD_PROJECT  - GCP project ID (default: kaggle-on-gcp)
    GCS_BUCKET            - GCS bucket name (default: kaggle-on-gcp-ad-campaign-assets)

See: https://google.github.io/adk-docs/deploy/agent-engine/
"""

import argparse
import os
import sys

# Check Python version - Agent Engine only supports 3.9-3.13
SUPPORTED_VERSIONS = ('3.9', '3.10', '3.11', '3.12', '3.13')
current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
if current_version not in SUPPORTED_VERSIONS:
    print(f"\033[0;31m✗ Python {current_version} is not supported by Agent Engine.\033[0m")
    print(f"  Supported versions: {', '.join(SUPPORTED_VERSIONS)}")
    print(f"\n  To fix this, run with a compatible Python version:")
    print(f"    python3.12 scripts/deploy_ae_inline.py")
    print(f"    # or")
    print(f"    pyenv local 3.12")
    print(f"    python scripts/deploy_ae_inline.py")
    sys.exit(1)

# Add project root to path for app imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)

# Colors for terminal output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color


def print_header(text: str):
    """Print a styled header."""
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}{text}{NC}")
    print(f"{BLUE}{'=' * 60}{NC}")


def print_success(text: str):
    """Print success message."""
    print(f"{GREEN}✓ {text}{NC}")


def print_info(text: str):
    """Print info message."""
    print(f"{CYAN}  {text}{NC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{YELLOW}⚠ {text}{NC}")


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Ad Campaign Agent to Agent Engine using Python SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                          # Deploy to us-central1 (default)
    %(prog)s --trace                  # Deploy with Cloud Trace enabled
    %(prog)s --dry-run                # Preview configuration
        """
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show configuration without deploying"
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable Cloud Trace for observability"
    )
    parser.add_argument(
        "--project",
        default=os.getenv("GOOGLE_CLOUD_PROJECT", "kaggle-on-gcp"),
        help="GCP project ID (default: GOOGLE_CLOUD_PROJECT env or kaggle-on-gcp)"
    )
    parser.add_argument(
        "--bucket",
        default=os.getenv("GCS_BUCKET", "kaggle-on-gcp-ad-campaign-assets"),
        help="GCS bucket name (default: GCS_BUCKET env or kaggle-on-gcp-ad-campaign-assets)"
    )
    parser.add_argument(
        "--region",
        default="us-central1",
        help="Deployment region (default: us-central1, the only supported Agent Engine region)"
    )
    parser.add_argument(
        "--display-name",
        default="Ad Campaign Agent",
        help="Display name in Agent Engine console"
    )
    args = parser.parse_args()

    # Import here to avoid slow startup for --help
    import vertexai
    from vertexai import agent_engines

    print_header("Agent Engine Deployment (Python SDK)")

    print()
    print("Configuration:")
    print_info(f"Project:        {args.project}")
    print_info(f"Region:         {args.region}")
    print_info(f"Staging Bucket: gs://{args.bucket}")
    print_info(f"Display Name:   {args.display_name}")
    print_info(f"Cloud Trace:    {args.trace}")
    print_info(f"Method:         Python SDK (inline deployment)")
    print()

    if args.region != "us-central1":
        print_warning(f"Warning: Agent Engine currently only supports us-central1")
        print_warning(f"Using {args.region} may fail")
    else:
        print_success("Using us-central1 (Agent Engine supported region)")

    # Initialize Vertex AI
    print(f"\nInitializing Vertex AI...")
    vertexai.init(
        project=args.project,
        location=args.region,
        staging_bucket=f"gs://{args.bucket}"
    )
    print_success("Vertex AI initialized")

    if args.dry_run:
        print(f"\n{YELLOW}[DRY RUN]{NC} Configuration validated. Would deploy with settings above.")
        print("\nTo deploy for real, run without --dry-run:")
        print(f"  python {sys.argv[0]}")
        return 0

    # Import root_agent from app
    print("\nImporting agent from app.agent...")
    try:
        from app.agent import root_agent
        print_success(f"Agent imported: {root_agent.name}")
    except ImportError as e:
        print(f"{RED}✗ Failed to import agent: {e}{NC}")
        print("Make sure you're running from the project root directory.")
        return 1

    # Wrap in AdkApp
    print("\nCreating AdkApp wrapper...")
    app = agent_engines.AdkApp(
        agent=root_agent,
        enable_tracing=args.trace,
    )
    print_success("AdkApp created")

    # Deploy
    print_header("Deploying to Agent Engine")
    print()
    print("This typically takes 5-10 minutes...")
    print("(Container is built and deployed automatically)")
    print()

    try:
        requirements = [
            "google-cloud-aiplatform[adk,agent_engines]>=1.79.0",
            "google-adk>=1.21.0",
            "google-cloud-storage>=2.19.0",
            "google-genai>=1.55.0",
            "googlemaps>=4.10.0",
            "Pillow>=10.2.0",
            "pydantic>=2.11.7",
        ]

        # Use standard module-level agent_engines.create()
        # extra_packages bundles the local app/ directory so remote has access to app.tools, etc.
        remote_app = agent_engines.create(
            agent_engine=app,
            requirements=requirements,
            extra_packages=["./app"],  # Bundle local app package for remote access
            display_name=args.display_name,
            description="Fashion retail ad campaign management with Veo 3.1 video generation",
        )
    except Exception as e:
        print(f"\n{RED}✗ Deployment failed: {e}{NC}")
        return 1

    print_header("DEPLOYMENT COMPLETE!")

    print()
    print_success(f"Resource Name: {remote_app.resource_name}")
    print()
    print(f"{GREEN}Query API Endpoint:{NC}")
    print(f"  https://{args.region}-aiplatform.googleapis.com/v1/{remote_app.resource_name}:query")
    print()
    print(f"{GREEN}Stream Query API Endpoint:{NC}")
    print(f"  https://{args.region}-aiplatform.googleapis.com/v1/{remote_app.resource_name}:streamQuery")
    print()

    # Extract resource ID for convenience
    resource_id = remote_app.resource_name.split("/")[-1]

    print(f"{GREEN}Python Usage:{NC}")
    print(f"""
    from vertexai import agent_engines
    import vertexai

    vertexai.init(project="{args.project}", location="{args.region}")
    agent = agent_engines.get("{remote_app.resource_name}")
    response = agent.query(input="List all campaigns")
    print(response)
    """)

    print(f"{GREEN}Useful Commands:{NC}")
    print(f"  # List deployed agents")
    print(f"  gcloud ai reasoning-engines list --project={args.project} --region={args.region}")
    print()
    print(f"  # Delete this agent")
    print(f"  gcloud ai reasoning-engines delete {resource_id} --project={args.project} --region={args.region}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
