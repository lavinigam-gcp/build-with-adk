# ADK Deep Research Agent - Experimentation Guide

## Overview

This directory contains the **ADK Deep Research Agent** - a sophisticated multi-agent system built with Google's Agent Development Kit (ADK) for conducting comprehensive research and generating detailed, cited reports.

### Purpose
The deep research agent transforms user queries into structured research plans, executes iterative web-based research, evaluates findings quality, and synthesizes comprehensive reports with citations.

### Core Philosophy
- **Experimentation-First**: New features are isolated in experiment folders before integration
- **Iterative Improvement**: Each experiment builds knowledge for the main agent
- **Isolation**: Experiments don't affect production until proven successful
- **Documentation**: Every experiment must be documented for learning

---

## Directory Structure

```
build-with-adk/
├── adk-deep-research/           # MAIN PROJECT - Deep research agent
│   ├── CLAUDE.md                # This file - your guiding light
│   ├── .env                     # Environment variables (GCP project)
│   └── app/                     # Production research agent
│       ├── agent.py             # Core agent logic
│       ├── config.py            # Configuration
│       └── __init__.py
├── experiments/                 # EXPERIMENTS - Local only (gitignored)
│   ├── code_execution_01/       # [SUCCESS] Financial Data Visualization
│   ├── code_execution_02/       # [SUCCESS] HTML Report Generation
│   └── code_execution_03/       # [PAUSED] Native Code Execution
└── adk-equity-deep-research/    # GRADUATED - Professional equity research agent
    ├── agent.py                 # 17-agent multi-stage pipeline
    ├── config.py                # Agent configuration
    ├── manage_sandbox.py        # Sandbox lifecycle management
    ├── .docs/new_flow/          # HITL architecture implementation plan
    └── README.md                # Full documentation
```

**Note**: The `experiments/` folder is git-ignored and remains local only. Successful experiments are graduated to their own top-level projects (e.g., `adk-equity-deep-research`).

---

## Current Agent Architecture

### Agent Pipeline Overview

The main agent (`app/agent.py`) implements a sophisticated multi-phase research system:

```
User Query
    ↓
interactive_planner_agent (entry point)
    ↓
plan_generator → Generates 5-phase structured research plan
    ↓
research_pipeline (SequentialAgent)
    ├── section_planner → Creates report outline
    ├── section_researcher → Executes [RESEARCH] tasks with google_search
    ├── iterative_refinement_loop (LoopAgent, max 5 iterations)
    │   ├── research_evaluator → Grades quality (pass/fail)
    │   ├── escalation_checker → Stops loop if "pass"
    │   └── enhanced_search_executor → Runs follow-up searches if "fail"
    └── report_composer → Synthesizes final cited report
    ↓
Final Report with Citations
```

### Key Components

1. **Plan Generator** (`plan_generator`)
   - Deconstructs queries into 5-phase JSON research plans
   - Phases: Analysis → Strategy → Implementation → Deliverables → Creative Assets
   - Uses playbook system for different query types (Venture, Informational, Creative)

2. **Section Planner** (`section_planner`)
   - Converts research plan into markdown report structure
   - One-to-one mapping between plan items and report sections

3. **Section Researcher** (`section_researcher`)
   - Executes [RESEARCH] tasks using google_search tool
   - 5-8 targeted queries per research goal
   - Synthesizes findings into structured knowledge base

4. **Research Evaluator** (`research_evaluator`)
   - Quality assurance with pass/fail grading
   - Generates 5-7 follow-up queries if research is insufficient
   - Uses Feedback structured output schema

5. **Enhanced Search Executor** (`enhanced_search_executor`)
   - Executes follow-up queries from failed evaluations
   - Integrates new findings with existing research

6. **Report Composer** (`report_composer`)
   - Transforms research into polished, cited report
   - Executes [DELIVERABLE] synthesis tasks
   - Inserts citation tags for source attribution

### Callbacks

- `collect_research_sources_callback`: Extracts grounding metadata for citations
- `citation_replacement_callback`: Converts citation tags to markdown links

### Configuration

- Models: `gemini-2.5-flash` (both critic and worker)
- Max iterations: 5
- Configurable via `config.py`

---

## Experimentation Guidelines

### When to Create an Experiment

Create a new experiment folder when you want to:
- Test a new ADK feature (tools, planners, callbacks)
- Modify the agent pipeline structure
- Experiment with different prompting strategies
- Add new capabilities (memory, grounding, function calling)
- Try different model configurations
- Test alternative evaluation criteria
- Explore new research methodologies

### Experiment Naming Convention

```
experiment-XXX-short-descriptive-name
```

Examples:
- `experiment-001-memory-bank-integration`
- `experiment-002-parallel-research-branches`
- `experiment-003-adaptive-iteration-limits`
- `experiment-004-multi-modal-outputs`

### Creating a New Experiment

1. **Create Experiment Folder**
   ```bash
   mkdir -p experiments/experiment-XXX-name/app
   ```

2. **Copy Base Agent**
   ```bash
   cp -r app/* experiments/experiment-XXX-name/app/
   ```

3. **Create README.md** (see template below)

4. **Document as You Go** in `notes.md`

5. **Test Thoroughly** before considering integration

### Experiment README Template

```markdown
# Experiment XXX: [Descriptive Title]

## Hypothesis
What are we testing? What do we expect to improve?

## Motivation
Why is this important? What problem does it solve?

## Approach
How will we implement this? What changes are needed?

## Changes Made
- List specific modifications to agent.py
- Configuration changes
- New dependencies or tools

## Test Cases
1. Test case 1: [description]
2. Test case 2: [description]

## Results
### Successful Outcomes
- What worked well?
- Metrics improved?

### Issues Encountered
- What didn't work?
- Unexpected behaviors?

### Performance Comparison
- Before: [metrics]
- After: [metrics]

## Recommendation
- [ ] Integrate into main agent
- [ ] Needs more work
- [ ] Abandon (explain why)

## Integration Notes
If recommended for integration, what specific steps are needed?
```

---

## Integration Workflow

### Step 1: Validate Experiment Success

Before integration, ensure:
- [ ] Experiment meets stated hypothesis
- [ ] No performance degradation
- [ ] Code quality is production-ready
- [ ] Documentation is complete
- [ ] Multiple test cases pass

### Step 2: Create Integration Plan

Document in experiment's README:
- Files to be modified in `app/`
- Backward compatibility considerations
- Configuration changes needed
- Migration path if any

### Step 3: Incremental Integration

- Make changes in small, testable increments
- Test after each change
- Keep experiment folder for reference
- Document integration in commit messages

### Step 4: Validation

- Run full test suite on main agent
- Compare outputs before/after integration
- Monitor for regressions

### Step 5: Document Learning

Update `docs/lessons-learned.md` with:
- What worked
- What didn't
- Key insights gained

---

## ADK-Specific Best Practices

### Agent Design Patterns

1. **Sequential vs Loop vs Conditional**
   - SequentialAgent: Fixed pipeline steps
   - LoopAgent: Iterative refinement with max iterations
   - Use escalation to break loops early

2. **State Management**
   - Use `output_key` to store agent outputs in session state
   - Access via template variables: `{{ key_name }}`
   - Callbacks can modify `callback_context.state`

3. **Tool Usage**
   - Define tools list per agent
   - Use AgentTool to wrap sub-agents
   - Consider tool-specific rate limits

4. **Structured Outputs**
   - Define Pydantic models for consistent outputs
   - Use `output_schema` parameter
   - Critical for agent-to-agent communication

5. **Callbacks**
   - `after_agent_callback`: Runs after agent completes
   - `before_agent_callback`: Pre-processing
   - Access full session context and events

### Common Pitfalls to Avoid

1. **Over-prompting**: ADK agents are stateful; don't repeat context
2. **Ignoring State**: Always check session state before creating new data
3. **Missing Escalation**: LoopAgents need explicit exit conditions
4. **Tool Overuse**: Balance tool calls with reasoning
5. **Citation Loss**: Ensure callbacks preserve grounding metadata

### Testing Strategies

1. **Unit Testing**: Test individual agents in isolation
2. **Integration Testing**: Test agent pipelines end-to-end
3. **Comparison Testing**: Run same query on old vs new versions
4. **Edge Case Testing**: Empty inputs, malformed queries, extreme lengths

---

## Current Focus Areas for Experimentation

### High Priority

1. **Memory Integration**
   - Integrate Memory Bank for multi-session learning
   - Store successful research patterns
   - Build domain knowledge over time

2. **Parallel Research Execution**
   - Research multiple plan sections concurrently
   - Reduce total research time
   - Aggregate results intelligently

3. **Adaptive Quality Control**
   - Dynamic iteration limits based on query complexity
   - Multi-dimensional evaluation metrics
   - Self-improving evaluation criteria

### Medium Priority

4. **Multi-Modal Outputs**
   - Generate images, diagrams, charts
   - Video script generation
   - Audio summary generation

5. **Enhanced Citation Systems**
   - Inline citations with confidence scores
   - Citation clustering by topic
   - Source quality assessment

6. **Specialized Research Modes**
   - Academic research mode
   - Business intelligence mode
   - Technical deep-dive mode

### Exploration

7. **Collaborative Planning**
   - Multi-turn plan refinement
   - User-in-the-loop validation
   - Alternative plan generation

8. **Knowledge Graph Construction**
   - Build entity relationships during research
   - Visualize research connections
   - Enable graph-based querying

---

## Success Metrics

### Quality Metrics
- Citation accuracy and relevance
- Report comprehensiveness (evaluated by critic)
- User satisfaction (if available)
- Source diversity and credibility

### Performance Metrics
- Total execution time
- Number of search queries needed
- Iteration count before "pass" grade
- Token usage per research task

### Reliability Metrics
- Success rate (completed vs failed runs)
- Error frequency and types
- Graceful degradation under constraints

---

## Versioning and Changelog

### Main Agent Versions

Track major changes to `app/` agent:

**v1.0** (Current - 2025-01-XX)
- 5-phase JSON research planning
- Iterative refinement with quality evaluation
- Citation system with markdown links
- Playbook-based creative asset generation

### Experiment Log

| Exp # | Name | Status | Outcome |
|-------|------|--------|---------|
| 001 | Financial Data Visualization (code_execution_01) | SUCCESS | Multi-agent pipeline combining Google Search + Code Execution to generate financial charts |
| 002 | HTML Report Generation (code_execution_02) | **SUCCESS - RECOMMENDED** | Extended 01 with 5th agent for self-contained HTML report with embedded chart. Callback-based execution provides 100% reliability. |
| 003 | Native Code Execution (code_execution_03) | **PAUSED** | Native AgentEngineSandboxCodeExecutor works for simple queries but causes infinite loops on complex queries. Instruction-based STOP conditions insufficient. Gemini 3 Pro has malformed function call issues. Use 02 instead. |
| 004 | Comprehensive Equity Research | **GRADUATED → adk-equity-deep-research** | 17-agent multi-stage equity research pipeline. Professional-grade reports with 5-10 charts, AI-generated infographics (2-5), and comprehensive analysis. Query classification, ParallelAgent data fetching, LoopAgent chart generation, custom ChartProgressChecker. Ready for HITL planning enhancement (see `.docs/new_flow/`). |

---

## Questions & Decision Log

### Open Questions
- What is the optimal max_iterations value?
- Should we use different models for different phases?
- How to handle rate limits on google_search?
- What's the best way to handle very long research plans?

### Decisions Made
- Use gemini-2.5-flash for all agents (cost/quality balance)
- 5 max iterations for quality loop (diminishing returns after)
- JSON-based plan structure for machine readability
- Separate RESEARCH and DELIVERABLE task types

---

## Resources

### ADK Documentation
- [ADK Official Docs](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview)
- [Agent Patterns](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/patterns)
- [Memory Bank Guide](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/memory-bank/overview)

### Internal Resources
- Main agent: `app/agent.py`
- Configuration: `app/config.py`
- Example queries: (to be created)

### External References
- Pydantic Models: For structured outputs
- Google Search Tool: ADK built-in
- Grounding Metadata: Citation extraction

---

## Contributing

### Before Starting an Experiment
1. Read this guide thoroughly
2. Review current agent architecture
3. Check existing experiments for similar work
4. Document your hypothesis clearly

### During Experimentation
1. Keep detailed notes in `notes.md`
2. Commit frequently with clear messages
3. Test incrementally
4. Document unexpected findings

### After Experimentation
1. Complete README.md with full results
2. Make integration recommendation
3. Share learnings with team
4. Update this guide if needed

---

## Notes

- **Do Not Modify**: `retail-ai-location-strategy/` - completely separate project
- **Main Agent**: Only modify `app/` after successful experiment validation
- **Experiments**: Feel free to break things - that's the point
- **Documentation**: Future you will thank present you

---

## Completed Experiments Summary

### Experiment 001: Financial Data Visualization (`code_execution_01/`)

**Status**: SUCCESS

**What it does**: A 4-stage SequentialAgent pipeline that:
1. Fetches real-time financial data via Google Search
2. Extracts structured data points using Pydantic schemas
3. Generates matplotlib charts using AgentEngineSandbox code execution
4. Creates a summary with key insights

**Key Learnings**:
- Sandbox only has matplotlib, numpy, pandas (no seaborn)
- Pre-creating sandboxes significantly improves performance
- `output_key` parameter is essential for agent-to-agent data flow
- Pydantic schemas ensure reliable structured outputs

**Example Query**: "Help me do PE analysis of quarter by quarter in last 5 years for top 5 stocks of S&P"

**Run it**:
```bash
cd adk-deep-research
export GOOGLE_CLOUD_PROJECT=your-project-id
adk web code_execution_01
```

---

**Last Updated**: 2025-12-21
**Agent Version**: v1.0
**Next Review**: After first 3 experiments completed
