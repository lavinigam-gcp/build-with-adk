# Sandbox Setup Guide

This guide helps you configure the Agent Engine Sandbox required for chart generation.

## Prerequisites

- Google Cloud project with Vertex AI enabled
- `gcloud` CLI authenticated
- Python environment with dependencies installed

## Quick Setup

### Step 1: Set Google Cloud Project

```bash
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
```

### Step 2: Create or List Sandboxes

**Create a new sandbox:**
```bash
python manage_sandbox.py create --name "equity_research_sandbox"
```

This will output:
```
Creating new Agent Engine...
Created Agent Engine: projects/.../agentEngines/...

Creating sandbox 'equity_research_sandbox'...
Sandbox created successfully!
  Resource name: projects/.../sandboxes/...

To use this sandbox, set the environment variable:
  export SANDBOX_RESOURCE_NAME="projects/.../sandboxes/..."
```

**Or list existing sandboxes:**
```bash
# First, set the agent engine if you have one
export AGENT_ENGINE_RESOURCE_NAME=projects/.../agentEngines/...

python manage_sandbox.py list
```

### Step 3: Configure .env

Create a `.env` file in the project root:

```bash
# .env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=1

# From manage_sandbox.py output
AGENT_ENGINE_RESOURCE_NAME=projects/.../agentEngines/...
SANDBOX_RESOURCE_NAME=projects/.../sandboxes/...
```

### Step 4: Test the Sandbox

```bash
python manage_sandbox.py test
```

Expected output:
```
Testing sandbox: projects/.../sandboxes/...
Python version: 3.x.x
  matplotlib: x.x.x
  numpy: x.x.x
  pandas: x.x.x
Sandbox is working correctly!
```

### Step 5: Run the Agent

```bash
adk web app
```

Query: "Analyze Apple stock focusing on financial performance"

---

## manage_sandbox.py Commands

| Command | Description |
|---------|-------------|
| `python manage_sandbox.py create --name "NAME"` | Create new sandbox |
| `python manage_sandbox.py list` | List all sandboxes |
| `python manage_sandbox.py get --sandbox-id "ID"` | Get sandbox details |
| `python manage_sandbox.py test` | Test current sandbox |
| `python manage_sandbox.py delete --sandbox-id "ID"` | Delete a sandbox |

---

## Troubleshooting

### Error: "SANDBOX_RESOURCE_NAME environment variable not set"

The sandbox hasn't been configured. Run:
```bash
python manage_sandbox.py create --name "equity_sandbox"
```
Then add the output to your `.env` file.

### Error: "AGENT_ENGINE_RESOURCE_NAME not set" (when listing)

You need to create an agent engine first:
```bash
python manage_sandbox.py create --name "equity_sandbox"
```
This auto-creates an agent engine if one doesn't exist.

### Sandbox expired or in error state

Create a new sandbox:
```bash
python manage_sandbox.py create --name "equity_sandbox_v2"
```
Update `SANDBOX_RESOURCE_NAME` in `.env` with the new resource name.

### Charts not generating but no errors

Check sandbox is ACTIVE:
```bash
python manage_sandbox.py get --sandbox-id "$SANDBOX_RESOURCE_NAME"
```

---

## Example .env File

```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=kaggle-on-gcp
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=1

# Agent Engine & Sandbox (from manage_sandbox.py)
AGENT_ENGINE_RESOURCE_NAME=projects/474775107710/locations/us-central1/reasoningEngines/xxx
SANDBOX_RESOURCE_NAME=projects/474775107710/locations/us-central1/reasoningEngines/xxx/sandboxEnvironments/yyy

# Optional
LOG_LEVEL=INFO
```
