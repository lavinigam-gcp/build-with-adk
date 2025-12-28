# Experiment 003: Native Code Execution Architecture

## Status: PAUSED - Partially Works

A fundamentally different architecture from `code_execution_01/02`. Instead of having the LLM generate code as text (which a callback then executes), this experiment uses ADK's native `code_executor` capability where the LLM agent has direct sandbox access and can execute code iteratively.

---

## Experiment Result Summary

### Hypothesis
Can we prevent infinite loops using **instruction design** instead of **architecture isolation**?

### Result: PARTIALLY FALSIFIED

| Query Complexity | Result | Notes |
|------------------|--------|-------|
| Simple queries | Works | "Show me Google's revenue for 5 years" |
| Medium queries | Usually works | "Compare Google and Microsoft revenue 2020-2024" |
| Complex queries | **FAILS - Infinite loops** | Multi-entity, multi-metric, layered data |

### Recommendation
**Use `code_execution_02` for production.** The callback-based architecture provides guaranteed single execution regardless of query complexity.

---

## What's Different in 003

| Aspect | code_execution_01/02 | code_execution_03 |
|--------|----------------------|-------------------|
| Code Generation | LLM outputs code as TEXT | **LLM executes code directly** |
| Execution | Callback uses Vertex AI client | **AgentEngineSandboxCodeExecutor** |
| Instruction Style | Code templates, specific syntax | **Natural language goals** |
| Loop Prevention | Callback isolation (no LLM in loop) | **Explicit STOP condition** |
| State | Code stored as `chart_code` text | **Confirmation text in `chart_creation_result`** |
| Artifact Extraction | During execution callback | **Separate post-execution callback** |
| Reliability | **100% - guaranteed single execution** | **~70% - fails on complex queries** |

---

## Issues Discovered

### Issue 1: Gemini 3 Pro Preview - Malformed Function Calls

**Problem**: Gemini 3 Pro Preview outputs Python-style code instead of proper function call JSON:
```
Malformed function call: call:default_api:execute_code{code:"""import matplotlib...
```

**Root Cause**: Known Gemini model behavior with AgentEngineSandboxCodeExecutor tool calling.

**Solution**: Switched chart_creator_agent to use `gemini-2.5-flash` instead.

### Issue 2: Print Output Override

**Problem**: STOP condition looked for `"Chart saved successfully"` but agent never sees it.

**Root Cause**: The sandbox/Gemini code execution returns:
```
Saved artifacts:
`code_execution_image_1_xxx.png`,`financial_chart.png`
```
This message REPLACES print() output. The agent never sees our print statement.

**Solution Attempted**: Changed STOP condition to look for `"Saved artifacts:"` with `"financial_chart.png"`.

**Result**: Did not fully resolve the issue.

### Issue 3: Infinite Loops on Complex Queries (UNRESOLVED)

**Problem**: For complex queries with multi-entity or multi-layer data, the agent generates the chart, sees "Saved artifacts", but then decides to "improve" the visualization and generates more code.

**Example Query That Fails**:
```
Show Apple's revenue breakdown by product category (iPhone, Mac, iPad, Services, Wearables)
from 2022 to 2025. Also add a layer of profits for each.
```

**Observed Behavior**:
- Agent creates initial chart successfully
- Sees "Saved artifacts: financial_chart.png"
- Generates new code to "improve" the grouped bar chart layout
- Repeat 10+ times until timeout or UNEXPECTED_TOOL_CALL error

**Session Evidence** (793adfc8-f47f-4a65-94bf-839cf83d84b0):
- 101 events recorded
- Multiple code execution cycles for same query
- Each cycle saved `financial_chart.png` with incrementing artifact versions

**Root Cause Analysis**:
The LLM interprets complex visualization requirements as needing iteration/refinement. Even with explicit "ONE code execution" and "Do NOT improve" instructions, the model's training to be helpful overrides the stop condition when it perceives the chart could be better.

**Why 01/02 Works**: The LLM never sees execution results. It outputs code once, callback executes, done. No opportunity to "improve".

### Issue 4: Sandbox State Persistence (FIXED)

**Problem**: Sandbox keeps files between sessions.

**Solution**: Added `before_agent_callback` to delete stale charts and post-extraction cleanup.

### Issue 5: HTML Placeholder Not Used

**Problem**: LLM wrote `<img src="financial_chart.png">` instead of `<img src="CHART_IMAGE_PLACEHOLDER">`.

**Solution**: Moved placeholder instruction to top with "CRITICAL" emphasis.

---

## Architecture

```
User Query: "Show me Google's revenue for the last 5 years"
                          |
+----------------------------------------------------------+
|      financial_report_pipeline (SequentialAgent)         |
+----------------------------------------------------------+
|                                                          |
|  1. DATA FETCHER AGENT                                   |
|     - google_search tool                                 |
|     - output_key: "raw_financial_data"                   |
|                                                          |
|  2. DATA EXTRACTOR AGENT                                 |
|     - Pydantic schema output                             |
|     - output_key: "structured_data"                      |
|                                                          |
|  3. CHART CREATOR AGENT (EXPERIMENTAL)                   |
|     - code_executor: AgentEngineSandboxCodeExecutor      |
|     - Model: gemini-2.5-flash (not gemini-3-pro-preview) |
|     - ISSUE: Infinite loops on complex queries           |
|     - before_callback: cleanup stale charts              |
|     - after_callback: extract chart artifact             |
|                                                          |
|  4. SUMMARY AGENT                                        |
|     - output_key: "final_summary"                        |
|                                                          |
|  5. HTML REPORT GENERATOR                                |
|     - output_key: "html_report"                          |
|     - after_callback: save HTML artifact                 |
|                                                          |
+----------------------------------------------------------+
```

---

## Quick Start (For Testing)

```bash
cd adk-deep-research
adk web code_execution_03
```

### Test Queries

**Works (Simple)**:
- "Show me Google's revenue for the last 5 years"
- "What was Tesla's stock price in 2024?"

**Usually Works (Medium)**:
- "Compare Google and Microsoft revenue for 2020-2024"
- "Show Tesla, Ford, GM profit margins 2020-2024"

**Fails - Infinite Loop (Complex)**:
- "Show Apple's revenue breakdown by product category with profit layers"
- "PE analysis quarter by quarter for top 5 S&P 500 stocks"

---

## Files

| File | Description |
|------|-------------|
| `agent.py` | 5-stage pipeline with native code execution |
| `config.py` | Configuration |
| `manage_sandbox.py` | Sandbox CLI tool |
| `requirements.txt` | Python dependencies |
| `__init__.py` | Package init |
| `README.md` | This documentation |

---

## Key Learnings

### 1. Callback Isolation is More Reliable

The 01/02 architecture where LLM outputs code as TEXT and callback executes it provides guaranteed single execution. The LLM never has the opportunity to "improve" because it never sees results.

### 2. STOP Conditions Have Limits

Even with explicit, repeated, strongly-worded STOP conditions, LLMs trained to be helpful will sometimes override them when they perceive a task could be done better. This is especially true for:
- Complex visualizations with multiple data series
- Charts that could have better layouts
- Data that "looks wrong" to the model

### 3. Sandbox Output Format Matters

When using AgentEngineSandboxCodeExecutor or Gemini's native code execution:
- print() output may be overwritten by system messages
- "Saved artifacts: filename.png" is the actual output format
- STOP conditions must match what the agent ACTUALLY sees

### 4. Model Choice Matters

- `gemini-3-pro-preview`: Malformed function calls with code_executor
- `gemini-2.5-flash`: Works but still has infinite loop issue on complex queries

---

## Potential Future Fixes (Not Yet Tested)

1. **Add output_schema to chart_creator**: Force structured output instead of freeform text/code
   ```python
   class ChartCreationResult(BaseModel):
       success: bool
       description: str
   ```

2. **Max tool calls limit**: If ADK supports limiting code execution iterations

3. **Timeout-based interruption**: Kill agent after N seconds

4. **Hybrid approach**: Use native code_executor for simple queries, fallback to 02 for complex

---

## Comparison: 02 vs 03

| Criteria | code_execution_02 | code_execution_03 |
|----------|-------------------|-------------------|
| Reliability | 100% | ~70% |
| Architecture | Callback-based | Native code_executor |
| Loop Prevention | Architectural isolation | Instruction-based |
| Self-correction | No | Yes (but causes loops) |
| Complexity | More code in callback | Less code, simpler |
| Recommended | **YES** | No (for production) |

---

## Sources

- [ADK Code Execution Documentation](https://google.github.io/adk-docs/tools/google-cloud/code-exec-agent-engine/)
- [code_execution_01](../code_execution_01/) - Original experiment (callback-based)
- [code_execution_02](../code_execution_02/) - HTML report extension (RECOMMENDED)
- [Gemini 3 Pro Preview](https://ai.google.dev/gemini-api/docs/gemini-3)

---

**Last Updated**: 2025-12-28
**Experiment Status**: PAUSED - Works for simple queries, fails on complex
**Base Experiment**: code_execution_02 (SUCCESS - RECOMMENDED)
**Hypothesis Result**: Partially falsified - instruction-based STOP conditions insufficient for complex queries
