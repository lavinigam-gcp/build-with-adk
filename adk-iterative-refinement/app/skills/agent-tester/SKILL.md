---
name: agent-tester
description: Tests generated ADK agent code through a save-first validation pipeline. Saves code to disk FIRST, then tests the saved code via start_agent and talk_to_agent. Drives the iterative refinement loop.
---

# Agent Tester

Test generated ADK agent code through a save-first validation pipeline. The critical principle: test what you ship, not what you generated.

## CRITICAL: Save-First Testing

NEVER test code in memory via the code executor and then save separately. JSON serialization can corrupt code (escaped quotes). Always:
1. Save the code to disk via save_agent_code FIRST
2. Test the SAVED code using start_agent and talk_to_agent (NOT code executor for file checks)
3. If tests fail, fix the code, re-save, and retest

## Why NOT code executor for file validation

The UnsafeLocalCodeExecutor runs in a different working directory (/home/user) than where save_agent_code writes files. This means code executor CANNOT reliably read or validate saved files. Instead, use the FunctionTools (start_agent, talk_to_agent) which operate on the real filesystem.

## Step 1: Save the Code

Before any testing, save the generated code to disk:

Call save_agent_code(agent_name="my_agent", agent_py_code=the_code)

This creates output/my_agent/ with agent.py, __init__.py, requirements.txt, and .env.

## Step 2: Validate the Code (via code executor)

Use the code executor ONLY for in-memory validation of the code STRING (not the saved file). Check:

1. The code string contains `from google.adk` (correct ADK import)
2. The code string does NOT contain `from google.generativeai` (wrong import)
3. The code string contains `root_agent` variable definition
4. The agent name in the code is a valid Python identifier (no hyphens)
5. The code string contains `model="gemini-2.5-flash"` as a string literal
6. The code string contains `load_dotenv` for environment loading
7. Tool functions have docstrings

If any check fails, this is a CODE BUG. Fix the code, re-save, retest. This is where the Ralph Loop catches real issues.

## Step 3: End-to-End Test (start_agent + talk_to_agent)

This is the REAL test. It uses FunctionTools that operate on the actual filesystem:

1. Call start_agent(agent_name) to launch the saved agent as api_server
2. Call talk_to_agent(agent_name, test_message) with a relevant test query
3. Check that the response contains meaningful text (not an error)

If start_agent fails: the saved code has a syntax error or import issue. Check the error message, fix the code, re-save, restart.

If talk_to_agent fails or returns an error: the agent runs but the tool has a bug. Check the error, fix the tool function, re-save, restart.

If talk_to_agent returns success: the agent is working. Present the code to the user.

## Refinement Protocol (The Ralph Loop)

The Ralph Loop is: generate, save, test, fix, re-save, retest.

When a test fails:

1. Read the EXACT error message
2. Identify whether it is a CODE BUG or an INFRASTRUCTURE ISSUE:
   - CODE BUG: wrong imports, syntax error, missing root_agent, invalid agent name, tool function bug
   - INFRASTRUCTURE: exec CWD mismatch, port conflicts, server startup timing
3. For CODE BUGS: fix the code, call save_agent_code again, re-run the failed test
4. For INFRASTRUCTURE: try once more. If it fails again, report to user and proceed.
5. Maximum 3 iterations for code bugs.

The value of the Ralph Loop is catching code bugs that the LLM did not notice:
- Using google.generativeai instead of google.adk (the LLM pre-training override)
- Agent name with hyphens (joke-agent instead of joke_agent)
- Missing docstrings on tool functions
- Wrong model string (importing model objects instead of using string)

## Pass Criteria

ALL of the following must be true:
- Step 2: Code string passes all 7 checks
- Step 3: start_agent succeeds AND talk_to_agent returns a meaningful response

Only after both steps pass, present the final code to the user with instructions.

## Test Query Selection

Choose a test query that exercises the agent's primary tool:
- Joke agent: "Tell me a programming joke"
- Unit converter: "Convert 100 celsius to fahrenheit"
- Greeting agent: "Say hello in spanish"
- Dice roller: "Roll a 6-sided die"
- Quote agent: "Give me a motivational quote"
