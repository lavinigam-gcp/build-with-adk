"use client";

import { CopilotSidebar } from "@copilotkit/react-ui";
import { useCoAgent, useCoAgentStateRender } from "@copilotkit/react-core";
import { PipelineTimeline } from "@/components/PipelineTimeline";
import { LocationReport } from "@/components/LocationReport";
import { CompetitorCard } from "@/components/CompetitorCard";
import { MarketCard } from "@/components/MarketCard";
import { AlternativeLocations } from "@/components/AlternativeLocations";
import { ArtifactViewer } from "@/components/ArtifactViewer";
import type { AgentState } from "@/lib/types";

export default function Home() {
  // Connect to agent state - this receives STATE_SNAPSHOT and STATE_DELTA events
  // The name must match the agent name in route.ts and backend app_name
  const { state } = useCoAgent<AgentState>({
    name: "retail_location_strategy",
  });

  // Render state in chat as generative UI
  // This creates rich UI components that appear inline in the chat
  // Simplified to show only current stage indicator (main dashboard shows full timeline)
  useCoAgentStateRender<AgentState>({
    name: "retail_location_strategy",
    render: ({ state }) => {
      if (!state) return null;

      // Early return during intake to avoid showing JSON output
      if (!state.pipeline_stage || state.pipeline_stage === "intake" || !state.stages_completed?.length) {
        if (state.target_location) {
          return (
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                <span className="text-blue-700 text-sm font-medium">
                  Parsing your request...
                </span>
              </div>
            </div>
          );
        }
        return null;
      }

      // Show simplified progress indicator in chat
      const stageLabels: Record<string, string> = {
        market_research: "Researching market trends...",
        competitor_mapping: "Mapping competitors...",
        gap_analysis: "Analyzing market gaps...",
        strategy_synthesis: "Synthesizing strategy...",
        report_generation: "Generating executive report...",
        infographic_generation: "Creating infographic...",
      };

      const currentLabel = stageLabels[state.pipeline_stage] || `Processing ${state.pipeline_stage}...`;
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
    <CopilotSidebar
      defaultOpen={true}
      clickOutsideToClose={false}
      labels={{
        title: "Retail Location Strategy",
        initial: `Hi! I'm your AI-powered location strategy assistant.

Tell me where you want to open your business and I'll analyze the market, map competitors, and provide strategic recommendations.

**Try these examples:**
- "I want to open a coffee shop in Indiranagar, Bangalore"
- "Analyze Austin, Texas for a fitness studio"
- "Where should I open a bakery in Dubai Marina?"`,
      }}
    >
      <main className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
        <div className="max-w-5xl mx-auto p-8">
          {/* Header */}
          <header className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Retail AI Location Strategy
            </h1>
            <p className="text-gray-600">
              Powered by Google ADK + Gemini 3 | Multi-Agent Pipeline
            </p>
          </header>

          {/* Pipeline Timeline - shown when analysis is in progress */}
          {(state?.target_location || state?.pipeline_stage) && (
            <div className="mb-8">
              <PipelineTimeline
                state={state}
                currentStage={state.pipeline_stage}
                completedStages={state.stages_completed || []}
              />
            </div>
          )}

          {/* Detailed Report Cards - shown when analysis is complete */}
          {state?.strategic_report && (
            <div className="space-y-6">
              <LocationReport report={state.strategic_report} />

              <div className="grid md:grid-cols-2 gap-6">
                <CompetitorCard
                  competition={
                    state.strategic_report.top_recommendation.competition
                  }
                />
                <MarketCard
                  market={state.strategic_report.top_recommendation.market}
                />
              </div>

              {/* Alternative Locations */}
              {state.strategic_report.alternative_locations?.length > 0 && (
                <AlternativeLocations
                  locations={state.strategic_report.alternative_locations}
                />
              )}

              {/* Key Insights */}
              <div className="bg-white rounded-xl shadow-sm border p-6">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <span className="text-xl">💡</span>
                  Key Insights
                </h3>
                <ul className="space-y-2">
                  {state.strategic_report.key_insights.map((insight, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-3 text-gray-700"
                    >
                      <span className="text-blue-500 mt-1">•</span>
                      {insight}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Artifact Viewer - HTML Report and Infographic (full-screen view) */}
              {(state.html_report_content || state.infographic_base64) && (
                <ArtifactViewer
                  htmlReport={state.html_report_content}
                  infographic={state.infographic_base64}
                />
              )}
            </div>
          )}

          {/* Welcome state - shown when no analysis is in progress */}
          {!state?.target_location && (
            <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
              <div className="text-7xl mb-6">🏪</div>
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                Find Your Perfect Location
              </h2>
              <p className="text-gray-600 max-w-lg mx-auto mb-8 text-lg">
                Tell me where you want to open your business in the chat, and
                I'll run a comprehensive analysis using live market data,
                competitor mapping, and AI-powered strategy recommendations.
              </p>

              <div className="grid md:grid-cols-3 gap-4 max-w-2xl mx-auto">
                <FeatureCard
                  icon="🔍"
                  title="Market Research"
                  description="Live web search for market trends and demographics"
                />
                <FeatureCard
                  icon="📍"
                  title="Competitor Mapping"
                  description="Google Maps API for real competitor locations"
                />
                <FeatureCard
                  icon="🧠"
                  title="AI Strategy"
                  description="Extended reasoning for strategic recommendations"
                />
              </div>
            </div>
          )}
        </div>
      </main>
    </CopilotSidebar>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <div className="p-4 bg-gray-50 rounded-lg text-left">
      <div className="text-2xl mb-2">{icon}</div>
      <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );
}
