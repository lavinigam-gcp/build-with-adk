# AG-UI Frontend for Retail AI Location Strategy

A rich, interactive frontend for the Retail AI Location Strategy ADK agent using [AG-UI Protocol](https://docs.ag-ui.com/) and [CopilotKit](https://docs.copilotkit.ai/).

## Features

- **Real-time Pipeline Timeline**: Watch the 7-stage analysis unfold with collapsible steps
- **Generative UI**: Rich visualizations appear in the chat as the agent works
- **Interactive Dashboard**: Location scores, competitor stats, market characteristics
- **Shared State**: Frontend and ADK agent share state bidirectionally via AG-UI Protocol
- **Scrollable Markdown**: Full markdown rendering with scrollable containers
- **Code Visibility**: View Python code executed during Gap Analysis in a dedicated tab

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  CopilotSidebar │ useCoAgent │ useCoAgentStateRender            │
└───────────────────────────────│─────────────────────────────────┘
                                │
                      AG-UI Protocol (SSE Events)
                                │
┌───────────────────────────────│─────────────────────────────────┐
│                    Backend (FastAPI + ADK)                       │
│               ADKAgent Middleware → root_agent                   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Google API Key (for Gemini)
- Google Maps API Key (for Places API)

### 1. Backend Setup

```bash
# From the retail_ai_location_strategy_adk directory
cd frontend/backend

# Install dependencies
pip install -r requirements.txt

# Make sure parent .env has your API keys:
# GOOGLE_API_KEY=your_key
# MAPS_API_KEY=your_maps_key

# Start the backend
python main.py
# Server runs at http://localhost:8000
```

### 2. Frontend Setup

```bash
# In a new terminal, from retail_ai_location_strategy_adk directory
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.local.example .env.local

# Start the frontend
npm run dev
# App runs at http://localhost:3000
```

### 3. Use the App

1. Open http://localhost:3000
2. The CopilotSidebar opens on the right
3. Type a location query like:
   - "I want to open a coffee shop in Indiranagar, Bangalore"
   - "Analyze Austin, Texas for a fitness studio"
4. Watch the pipeline progress and results appear in real-time!

## Project Structure

```
frontend/
├── backend/
│   ├── main.py              # FastAPI + ADKAgent wrapper
│   └── requirements.txt     # Python dependencies
│
├── app/
│   ├── layout.tsx           # CopilotKit provider
│   ├── page.tsx             # Main page with sidebar
│   └── globals.css          # Tailwind styles
│
├── components/
│   ├── PipelineTimeline.tsx     # Main dashboard with collapsible steps
│   ├── CollapsibleStep.tsx      # Individual pipeline step (expand/collapse)
│   ├── StepOutputContent.tsx    # Stage-specific output renderers
│   ├── ScrollableMarkdown.tsx   # Scrollable markdown container
│   ├── TabbedGapAnalysis.tsx    # Results + Code tabs for gap analysis
│   ├── LocationReport.tsx       # Top recommendation card
│   ├── CompetitorCard.tsx       # Competition statistics
│   ├── MarketCard.tsx           # Market characteristics
│   ├── AlternativeLocations.tsx # Alternative options
│   └── ArtifactViewer.tsx       # HTML report & infographic viewer
│
├── lib/
│   ├── types.ts             # TypeScript types (matches Pydantic)
│   ├── summaryHelpers.ts    # Summary extraction functions
│   └── parseCodeBlocks.ts   # Code block parsing utility
│
├── package.json
├── next.config.js
├── tailwind.config.js
└── tsconfig.json
```

## Environment Variables

### Backend (parent `.env`)

```bash
GOOGLE_API_KEY=your_google_api_key
MAPS_API_KEY=your_google_maps_api_key
GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

### Frontend (`.env.local`)

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## How It Works

### State Synchronization

The ADK agent's state is automatically synchronized with the frontend through AG-UI events:

| State Field | Updated By | UI Component |
|-------------|------------|--------------|
| `pipeline_stage` | before_* callbacks | PipelineTimeline |
| `stages_completed` | after_* callbacks | PipelineTimeline |
| `target_location` | IntakeAgent | Header card |
| `business_type` | IntakeAgent | Header card |
| `market_research_findings` | MarketResearchAgent | ScrollableMarkdown |
| `gap_analysis` | GapAnalysisAgent | TabbedGapAnalysis |
| `strategic_report` | StrategyAdvisorAgent | LocationReport, CompetitorCard, MarketCard |

### Generative UI

The `useCoAgentStateRender` hook renders custom UI components directly in the chat based on agent state changes:

```tsx
useCoAgentStateRender({
  name: "retail_location_strategy",
  render: ({ state }) => (
    <PipelineTimeline
      state={state}
      currentStage={state.pipeline_stage}
      completedStages={state.stages_completed}
    />
  ),
});
```

## Troubleshooting

### Backend won't start

1. Ensure you're in the correct directory: `frontend/backend`
2. Check that parent `.env` file exists with API keys
3. Verify `ag-ui-adk` is installed: `pip install ag-ui-adk`

### Frontend shows "Connection Error"

1. Ensure backend is running at http://localhost:8000
2. Check CORS settings in `backend/main.py`
3. Verify `NEXT_PUBLIC_BACKEND_URL` in `.env.local`

### State not updating

1. Check browser console for WebSocket/SSE errors
2. Verify agent name matches: `"retail_location_strategy"`
3. Ensure callbacks in `pipeline_callbacks.py` are setting state correctly

## Development

### Adding New Components

1. Add TypeScript interface to `lib/types.ts`
2. Create component in `components/`
3. Import in `app/page.tsx`
4. Add to `useCoAgentStateRender` for chat display

### Modifying Backend

The backend in `frontend/backend/main.py` wraps the existing ADK agent without modifications. To change agent behavior, modify the files in the parent directory:

- `agent.py` - Root agent definition
- `sub_agents/` - Individual sub-agents
- `callbacks/pipeline_callbacks.py` - State updates

## License

Apache 2.0 - See parent directory for full license.
