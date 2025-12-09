# Bonus: AG-UI Interactive Dashboard

By the end of this bonus part, you'll have a rich interactive frontend for your agent with real-time pipeline visualization.

**What You'll Build**: A Next.js dashboard that shows live agent progress, competitor data, and strategic recommendations as they're generated.

---

## Beyond ADK Web

ADK Web at `localhost:8501` is great for development, but for stakeholder demos and richer interaction, you might want:

- **Real-time progress visualization**: Watch each pipeline stage complete
- **Generative UI**: Rich cards and charts that appear inline in chat
- **Interactive dashboards**: Location scores, competitor stats, market cards
- **Bidirectional state sync**: Frontend and agent share state automatically

The [AG-UI Protocol](https://docs.ag-ui.com/) with [CopilotKit](https://docs.copilotkit.ai/) provides exactly this.

---

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

**Key concept**: The frontend connects to a thin FastAPI layer that wraps your existing ADK agent. The agent code stays unchanged.

---

## Quick Start

The project includes Makefile targets for easy setup:

```bash
# First time: Install dependencies
make ag-ui-install

# Start both servers
make ag-ui
```

This runs:
- **Backend** at `http://localhost:8000` - FastAPI server with AG-UI middleware
- **Frontend** at `http://localhost:3000` - Next.js dashboard

---

## The Backend Wrapper

The backend is minimal - it wraps your existing agent without modifications:

```python
# app/frontend/backend/main.py
from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint
from app.agent import root_agent  # Your existing agent!

# Wrap the existing ADK agent with AG-UI middleware
adk_agent = ADKAgent(
    adk_agent=root_agent,
    app_name="retail_location_strategy",
    user_id="demo_user",
    execution_timeout_seconds=1800,  # 30 min for full pipeline
    tool_timeout_seconds=600,  # 10 min for individual tools
)

app = FastAPI(
    title="Retail Location Strategy API",
    description="AG-UI compatible API for the Retail AI Location Strategy agent",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add AG-UI endpoint - handles all protocol communication
add_adk_fastapi_endpoint(app, adk_agent, path="/")
```

**Key points:**
- `from app.agent import root_agent` - Uses your exact same agent
- `ADKAgent` wraps it with AG-UI protocol support
- No agent code modifications needed

---

## The Frontend Page

The main page connects to the agent and renders state:

```tsx
// app/frontend/app/page.tsx
"use client";

import { CopilotSidebar } from "@copilotkit/react-ui";
import { useCoAgent, useCoAgentStateRender } from "@copilotkit/react-core";
import { PipelineTimeline } from "@/components/PipelineTimeline";
import { LocationReport } from "@/components/LocationReport";
import { CompetitorCard } from "@/components/CompetitorCard";
import { MarketCard } from "@/components/MarketCard";
import type { AgentState } from "@/lib/types";

export default function Home() {
  // Connect to agent state - receives STATE_SNAPSHOT and STATE_DELTA events
  const { state } = useCoAgent<AgentState>({
    name: "retail_location_strategy",  // Must match backend app_name
  });

  // Render state in chat as generative UI
  useCoAgentStateRender<AgentState>({
    name: "retail_location_strategy",
    render: ({ state }) => {
      if (!state) return null;

      const stageLabels: Record<string, string> = {
        market_research: "Researching market trends...",
        competitor_mapping: "Mapping competitors...",
        gap_analysis: "Analyzing market gaps...",
        strategy_synthesis: "Synthesizing strategy...",
        report_generation: "Generating executive report...",
      };

      const currentLabel = stageLabels[state.pipeline_stage] || "Processing...";
      const completedCount = state.stages_completed?.length || 0;

      return (
        <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
              <span className="text-gray-700 text-sm">{currentLabel}</span>
            </div>
            <span className="text-xs text-gray-500">
              {completedCount}/7 complete
            </span>
          </div>
        </div>
      );
    },
  });

  return (
    <CopilotSidebar defaultOpen={true} clickOutsideToClose={false}>
      <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
        {/* Pipeline Timeline - shown when analysis is in progress */}
        {state?.target_location && (
          <PipelineTimeline
            state={state}
            currentStage={state.pipeline_stage}
            completedStages={state.stages_completed || []}
          />
        )}

        {/* Detailed Report Cards - shown when complete */}
        {state?.strategic_report && (
          <div className="space-y-6">
            <LocationReport report={state.strategic_report} />
            <div className="grid md:grid-cols-2 gap-6">
              <CompetitorCard competition={state.strategic_report.top_recommendation.competition} />
              <MarketCard market={state.strategic_report.top_recommendation.market} />
            </div>
          </div>
        )}
      </main>
    </CopilotSidebar>
  );
}
```

**Key hooks:**
- `useCoAgent` - Connects to agent state, receives updates via SSE
- `useCoAgentStateRender` - Renders custom UI inline in the chat sidebar

---

## State Synchronization

The AG-UI frontend reads state that your callbacks set throughout the pipeline. This is the connection between the agent you built in Parts 2-7 and the dashboard you're adding now.

**How the callbacks from earlier parts drive the frontend:**

| State Field | Set By (From Series) | Callback Function | UI Component |
|-------------|----------------------|-------------------|--------------|
| `pipeline_stage` | All before_* callbacks | `before_market_research`, `before_gap_analysis`, etc. | PipelineTimeline |
| `stages_completed` | All after_* callbacks | `after_market_research`, `after_gap_analysis`, etc. | PipelineTimeline |
| `target_location` | Part 2: IntakeAgent | `after_intake` | Header card |
| `business_type` | Part 2: IntakeAgent | `after_intake` | Header card |
| `market_research_findings` | Part 3: MarketResearchAgent | Agent's `output_key` | ScrollableMarkdown |
| `competitor_analysis` | Part 4: CompetitorMappingAgent | Agent's `output_key` | CompetitorCard |
| `gap_analysis` | Part 5: GapAnalysisAgent | Agent's `output_key` | TabbedGapAnalysis |
| `strategic_report` | Part 6: StrategyAdvisorAgent | Agent's `output_key` | LocationReport |

**This is the payoff of the callback pattern**: Every `before_agent_callback` sets `pipeline_stage` so the timeline knows what's currently running. Every `after_agent_callback` appends to `stages_completed` so the timeline knows what's done. The `output_key` on each agent automatically populates state fields that the frontend reads.

```python
# Example from app/callbacks/pipeline_callbacks.py (Part 3)
def before_market_research(callback_context: CallbackContext):
    callback_context.state["pipeline_stage"] = "market_research"  # ← Frontend reads this
    callback_context.state["current_date"] = datetime.now().strftime("%Y-%m-%d")
    return None

def after_market_research(callback_context: CallbackContext):
    stages = callback_context.state.get("stages_completed", [])
    stages.append("market_research")  # ← Frontend reads this
    callback_context.state["stages_completed"] = stages
    return None
```

Your callbacks in `app/callbacks/pipeline_callbacks.py` already set these state values—the frontend just reads them!

---

## Project Structure

```
app/frontend/
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
│   ├── PipelineTimeline.tsx     # Collapsible steps with progress
│   ├── CollapsibleStep.tsx      # Individual pipeline step
│   ├── StepOutputContent.tsx    # Stage-specific renderers
│   ├── ScrollableMarkdown.tsx   # Scrollable markdown container
│   ├── TabbedGapAnalysis.tsx    # Results + Code tabs
│   ├── LocationReport.tsx       # Top recommendation card
│   ├── CompetitorCard.tsx       # Competition statistics
│   ├── MarketCard.tsx           # Market characteristics
│   ├── AlternativeLocations.tsx # Alternative options
│   └── ArtifactViewer.tsx       # HTML report & infographic
│
├── lib/
│   ├── types.ts             # TypeScript types (matches Pydantic)
│   └── summaryHelpers.ts    # Summary extraction functions
│
├── package.json
└── tailwind.config.js
```

---

## Frontend Components

### PipelineTimeline

Shows the 7-stage pipeline with collapsible steps:

```tsx
// app/frontend/components/PipelineTimeline.tsx
const stages = [
  { id: "intake", label: "Request Parsing", icon: "📝" },
  { id: "market_research", label: "Market Research", icon: "🔍" },
  { id: "competitor_mapping", label: "Competitor Mapping", icon: "📍" },
  { id: "gap_analysis", label: "Gap Analysis", icon: "📊" },
  { id: "strategy_synthesis", label: "Strategy Synthesis", icon: "🧠" },
  { id: "report_generation", label: "Report Generation", icon: "📄" },
  { id: "infographic_generation", label: "Infographic", icon: "🎨" },
];
```

### LocationReport

Displays the top recommendation from `strategic_report`:

```tsx
// app/frontend/components/LocationReport.tsx
export function LocationReport({ report }: { report: LocationIntelligenceReport }) {
  const rec = report.top_recommendation;

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{rec.location_name}</h2>
          <p className="text-gray-600">{rec.area}</p>
        </div>
        <div className="text-3xl font-bold text-green-600">
          {rec.overall_score}/100
        </div>
      </div>
      {/* Strengths, Concerns, Next Steps... */}
    </div>
  );
}
```

---

## Manual Setup

If you prefer manual setup:

### Backend

```bash
cd app/frontend/backend
pip install -r requirements.txt
python main.py
# Server runs at http://localhost:8000
```

### Frontend

```bash
cd app/frontend
npm install
cp .env.local.example .env.local
npm run dev
# App runs at http://localhost:3000
```

---

## Environment Variables

### Backend (`app/.env`)

```bash
GOOGLE_API_KEY=your_google_api_key
MAPS_API_KEY=your_google_maps_api_key
GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

### Frontend (`app/frontend/.env.local`)

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

---

## Demo Walkthrough

1. **Open http://localhost:3000**
   - The CopilotSidebar opens on the right
   - Main dashboard area shows welcome state

2. **Type a query in the chat**
   - "I want to open a coffee shop in Indiranagar, Bangalore"

3. **Watch the pipeline unfold**
   - Progress indicator appears in chat
   - Pipeline Timeline shows each stage completing
   - Collapsible steps reveal stage outputs

4. **View the results**
   - LocationReport card with score and recommendation
   - CompetitorCard with competition stats
   - MarketCard with market characteristics
   - Key Insights list
   - ArtifactViewer for HTML report and infographic

---

## Troubleshooting

### Backend won't start

1. Ensure you're in the correct directory: `app/frontend/backend`
2. Check that `app/.env` file exists with API keys
3. Verify `ag-ui-adk` is installed: `pip install ag-ui-adk`

### Frontend shows "Connection Error"

1. Ensure backend is running at http://localhost:8000
2. Check CORS settings in `backend/main.py`
3. Verify `NEXT_PUBLIC_BACKEND_URL` in `.env.local`

### State not updating

1. Check browser console for WebSocket/SSE errors
2. Verify agent name matches: `"retail_location_strategy"`
3. Ensure callbacks in `pipeline_callbacks.py` are setting state correctly

---

## Adding New Components

To add a new UI component that responds to agent state:

1. **Add TypeScript interface** to `lib/types.ts`
2. **Create component** in `components/`
3. **Import in `app/page.tsx`**
4. **Add to `useCoAgentStateRender`** for chat display

---

## What You've Built

In this bonus part, you:

1. Set up AG-UI Protocol with CopilotKit
2. Created a FastAPI backend that wraps your ADK agent
3. Built a Next.js dashboard with real-time state sync
4. Displayed pipeline progress with collapsible steps
5. Rendered rich cards for recommendations and insights

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `make ag-ui-install` | Install backend + frontend dependencies |
| `make ag-ui` | Start both servers (8000 + 3000) |

| Hook | Purpose |
|------|---------|
| `useCoAgent` | Connect to agent state |
| `useCoAgentStateRender` | Render custom UI in chat |

---

**Code files referenced in this part:**
- [`app/frontend/README.md`](../app/frontend/README.md) - Full documentation
- [`app/frontend/backend/main.py`](../app/frontend/backend/main.py) - FastAPI wrapper
- [`app/frontend/app/page.tsx`](../app/frontend/app/page.tsx) - Main page
- [`app/frontend/components/`](../app/frontend/components/) - UI components

**External Documentation:**
- [AG-UI Protocol](https://docs.ag-ui.com/)
- [CopilotKit](https://docs.copilotkit.ai/)

---

<details>
<summary>Image Prompt for This Part</summary>

```json
{
  "image_type": "ui_mockup",
  "style": {
    "design": "modern web application mockup",
    "color_scheme": "Google Cloud colors (blue #4285F4, red #EA4335, yellow #FBBC05, green #34A853) with white background",
    "layout": "dashboard with sidebar",
    "aesthetic": "React/Next.js modern UI"
  },
  "dimensions": {"aspect_ratio": "16:10", "recommended_width": 1200},
  "title": {"text": "Bonus: AG-UI Interactive Dashboard", "position": "top center"},
  "sections": [
    {
      "id": "sidebar",
      "position": "right",
      "width": "300px",
      "color": "#4285F4",
      "components": [
        {"name": "CopilotSidebar", "content": ["User message", "Agent response", "Progress indicator"]}
      ]
    },
    {
      "id": "header",
      "position": "top-left",
      "components": [
        {"name": "Title", "text": "Retail AI Location Strategy"},
        {"name": "Subtitle", "text": "Powered by Google ADK + Gemini"}
      ]
    },
    {
      "id": "timeline",
      "position": "main area top",
      "color": "#E8F5E9",
      "components": [
        {"name": "PipelineTimeline", "stages": ["Intake ✓", "Research ✓", "Mapping ✓", "Analysis...", "Strategy", "Report", "Infographic"]}
      ]
    },
    {
      "id": "cards",
      "position": "main area bottom",
      "layout": "grid 2x2",
      "components": [
        {"name": "LocationReport", "content": ["Defence Colony", "Score: 78/100", "Opportunity: Residential Premium"]},
        {"name": "CompetitorCard", "content": ["15 competitors", "Avg rating: 4.3", "Chain: 45%"]},
        {"name": "MarketCard", "content": ["Population: High", "Income: High", "Traffic: Moderate"]},
        {"name": "KeyInsights", "content": ["Insight 1", "Insight 2", "Insight 3"]}
      ]
    }
  ],
  "connections": [
    {"from": "sidebar", "to": "timeline", "label": "State Sync", "style": "bidirectional"}
  ],
  "annotation": {"text": "AG-UI Protocol: Real-time state synchronization", "position": "bottom"}
}
```

</details>
