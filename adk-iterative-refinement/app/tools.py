"""
Lifecycle tools for the ADK Agent Builder.

Four FunctionTools that manage the full agent lifecycle:
1. save_agent_code — writes tested agent code to disk
2. start_agent — launches the saved agent via adk api_server
3. talk_to_agent — sends a message to the running agent, returns its response
4. stop_agent — shuts down the running agent's api_server

These are regular FunctionTools (not code executors), so they coexist
with SkillToolset, McpToolset, and AgentTool on the same agent.
"""

import json
import os
import pathlib
import shutil
import subprocess
import time

import requests


# ── Configuration ───────────────────────────────────────────────────
CODE_DIR = pathlib.Path(__file__).parent
OUTPUT_DIR = CODE_DIR / "output"
VENV_DIR = CODE_DIR.parent / ".venv"
ADK_BIN = str(VENV_DIR / "bin" / "adk")

# Track running agent processes
_running_agents: dict[str, subprocess.Popen] = {}
_agent_ports: dict[str, int] = {}
_next_port = 9900  # Start port for spawned agents


def save_agent_code(
    agent_name: str,
    agent_py_code: str,
    requirements: str = "google-adk\npython-dotenv\n",
) -> dict:
    """Save tested ADK agent code to a directory on disk.

    Creates a complete ADK agent package at output/{agent_name}/ with all
    files needed to run with `adk web .` or `adk api_server .`.

    Args:
        agent_name: Directory name for the agent (e.g., 'joke_agent').
        agent_py_code: The complete Python code for agent.py.
        requirements: Contents of requirements.txt.

    Returns:
        Dictionary with status, file path, and list of files created.
    """
    safe_name = agent_name.lower().replace(" ", "_").replace("-", "_")
    agent_dir = OUTPUT_DIR / safe_name
    agent_dir.mkdir(parents=True, exist_ok=True)

    # Write agent.py
    (agent_dir / "agent.py").write_text(agent_py_code)

    # Write __init__.py
    (agent_dir / "__init__.py").write_text("from . import agent\n")

    # Write requirements.txt
    (agent_dir / "requirements.txt").write_text(requirements)

    # Copy .env from the builder's code/ directory
    builder_env = CODE_DIR / ".env"
    if builder_env.exists():
        shutil.copy(builder_env, agent_dir / ".env")

    files = [f.name for f in agent_dir.iterdir()]
    return {
        "status": "saved",
        "path": str(agent_dir),
        "files": sorted(files),
        "run_command": f"cd {agent_dir} && adk web .",
    }


def start_agent(agent_name: str) -> dict:
    """Start a saved agent by launching adk api_server as a subprocess.

    The agent runs on a dynamic port (starting from 9900). Once started,
    you can talk to it using the talk_to_agent tool.

    Args:
        agent_name: Name of the agent directory under output/.

    Returns:
        Dictionary with status, port number, and app name.
    """
    global _next_port

    safe_name = agent_name.lower().replace(" ", "_").replace("-", "_")
    agent_dir = OUTPUT_DIR / safe_name

    if not agent_dir.exists():
        return {"status": "error", "error": f"Agent not found at {agent_dir}"}

    # Stop any previously running agents (one agent at a time to avoid routing issues)
    for running_name in list(_running_agents.keys()):
        _running_agents[running_name].terminate()
        try:
            _running_agents[running_name].wait(timeout=5)
        except subprocess.TimeoutExpired:
            _running_agents[running_name].kill()
        del _running_agents[running_name]
        del _agent_ports[running_name]

    if safe_name in _running_agents:
        port = _agent_ports[safe_name]
        return {
            "status": "already_running",
            "port": port,
            "message": f"Agent already running on port {port}",
        }

    port = _next_port
    _next_port += 1

    # Start adk api_server from the OUTPUT directory (parent of agent dir)
    # IMPORTANT: adk api_server must run from the PARENT directory, not the
    # agent directory itself. Otherwise it looks for agent_name/agent_name/agent.py
    proc = subprocess.Popen(
        [ADK_BIN, "api_server", str(OUTPUT_DIR), "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    _running_agents[safe_name] = proc
    _agent_ports[safe_name] = port

    # Wait for startup (poll /list-apps)
    started = False
    for attempt in range(15):
        time.sleep(2)
        try:
            resp = requests.get(
                f"http://localhost:{port}/list-apps", timeout=3
            )
            if resp.status_code == 200:
                apps = resp.json()
                started = True
                break
        except requests.ConnectionError:
            continue

    if not started:
        proc.terminate()
        del _running_agents[safe_name]
        del _agent_ports[safe_name]
        stderr = proc.stderr.read() if proc.stderr else "unknown error"
        return {
            "status": "error",
            "error": f"api_server failed to start: {stderr[:300]}",
        }

    return {
        "status": "running",
        "port": port,
        "apps": apps,
        "message": f"Agent '{safe_name}' running on port {port}. Use talk_to_agent to interact.",
    }


def talk_to_agent(agent_name: str, message: str) -> dict:
    """Send a message to a running agent and return its response.

    This is the key tool that completes the meta-agent loop: the builder
    agent creates another agent, starts it, and then TALKS to it.

    Args:
        agent_name: Name of the running agent.
        message: The message to send to the agent.

    Returns:
        Dictionary with the agent's response text and event count.
    """
    safe_name = agent_name.lower().replace(" ", "_").replace("-", "_")

    if safe_name not in _running_agents:
        return {
            "status": "error",
            "error": f"Agent '{safe_name}' is not running. Use start_agent first.",
        }

    port = _agent_ports[safe_name]

    try:
        # Discover the actual app name (may differ from directory name)
        apps_resp = requests.get(f"http://localhost:{port}/list-apps", timeout=5)
        apps = apps_resp.json() if apps_resp.status_code == 200 else []
        app_name = apps[0] if apps else safe_name

        # Create a session
        session_resp = requests.post(
            f"http://localhost:{port}/apps/{app_name}/users/builder/sessions",
            json={},
            timeout=10,
        )
        session_id = session_resp.json().get("id")

        if not session_id:
            return {"status": "error", "error": "Failed to create session"}

        # Use POST /run endpoint — this RUNS the agent synchronously
        # (NOT PATCH, which only updates state without running the agent)
        run_resp = requests.post(
            f"http://localhost:{port}/run",
            json={
                "app_name": app_name,
                "user_id": "builder",
                "session_id": session_id,
                "new_message": {
                    "role": "user",
                    "parts": [{"text": message}],
                },
            },
            timeout=90,
        )

        if run_resp.status_code != 200:
            return {
                "status": "error",
                "error": f"HTTP {run_resp.status_code}: {run_resp.text[:200]}",
            }

        # POST /run returns the events directly
        events = run_resp.json()
        agent_responses = []
        for ev in events:
            author = ev.get("author", "")
            if author != "user":
                parts = ev.get("content", {}).get("parts", [])
                for p in parts:
                    if "text" in p and p["text"].strip():
                        agent_responses.append(p["text"])

        if agent_responses:
            return {
                "status": "success",
                "response": "\n".join(agent_responses),
                "events_count": len(events),
                "agent_name": safe_name,
                "query": message,
            }
        else:
            return {
                "status": "error",
                "error": "Agent returned no text response",
                "events_count": len(events),
            }

    except requests.Timeout:
        return {"status": "error", "error": "Request timed out (90s)"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def stop_agent(agent_name: str) -> dict:
    """Stop a running agent's api_server process.

    Args:
        agent_name: Name of the agent to stop.

    Returns:
        Dictionary with status and confirmation.
    """
    safe_name = agent_name.lower().replace(" ", "_").replace("-", "_")

    if safe_name not in _running_agents:
        return {"status": "not_running", "message": f"Agent '{safe_name}' is not running"}

    proc = _running_agents[safe_name]
    port = _agent_ports[safe_name]

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    del _running_agents[safe_name]
    del _agent_ports[safe_name]

    return {
        "status": "stopped",
        "message": f"Agent '{safe_name}' stopped (was on port {port})",
    }
