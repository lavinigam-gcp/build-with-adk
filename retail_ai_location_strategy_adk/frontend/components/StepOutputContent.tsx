"use client";

import type { AgentState } from "@/lib/types";
import {
  summarizeCompetitorAnalysis,
} from "@/lib/summaryHelpers";
import { ScrollableMarkdown } from "./ScrollableMarkdown";
import { TabbedGapAnalysis } from "./TabbedGapAnalysis";

interface StepOutputContentProps {
  stepId: string;
  state: AgentState;
}

/**
 * Renders the appropriate output content for each pipeline step.
 * This component handles the different output types per stage.
 */
export function StepOutputContent({ stepId, state }: StepOutputContentProps) {
  switch (stepId) {
    case "intake":
      return (
        <p className="text-gray-600 text-sm">
          Analyzing <span className="font-medium text-gray-900">{state.business_type}</span> locations in{" "}
          <span className="font-medium text-gray-900">{state.target_location}</span>
          {state.additional_context && (
            <span className="text-gray-500 ml-1">({state.additional_context})</span>
          )}
        </p>
      );

    case "market_research":
      return (
        <ScrollableMarkdown
          content={state.market_research_findings || ""}
          maxHeight="12rem"
        />
      );

    case "competitor_mapping":
      // Show summary stats at top, then full content if available
      const summary = summarizeCompetitorAnalysis(state.competitor_analysis, state.strategic_report);
      return (
        <div className="space-y-2">
          <p className="text-gray-700 text-sm font-medium">{summary}</p>
          {state.competitor_analysis && (
            <ScrollableMarkdown
              content={state.competitor_analysis}
              maxHeight="12rem"
            />
          )}
        </div>
      );

    case "gap_analysis":
      return <TabbedGapAnalysis content={state.gap_analysis || ""} />;

    case "strategy_synthesis":
      if (!state.strategic_report) {
        return <p className="text-gray-500 text-sm italic">Synthesizing strategy...</p>;
      }
      const rec = state.strategic_report.top_recommendation;
      return (
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-gray-900">{rec.location_name}</span>
            <span className={`px-2 py-0.5 rounded text-sm font-medium ${
              rec.overall_score >= 75 ? "bg-green-100 text-green-800" :
              rec.overall_score >= 50 ? "bg-yellow-100 text-yellow-800" :
              "bg-red-100 text-red-800"
            }`}>
              Score: {rec.overall_score}
            </span>
          </div>
          <p className="text-sm text-blue-700">
            "{rec.opportunity_type}" opportunity
          </p>
        </div>
      );

    case "report_generation":
      if (!state.html_report_content) {
        return <p className="text-gray-500 text-sm italic">Generating report...</p>;
      }
      return (
        <div className="flex items-center gap-3">
          <span className="text-sm text-green-700">7-slide McKinsey-style presentation ready</span>
          <div className="flex gap-2">
            <button
              onClick={() => {
                const blob = new Blob([state.html_report_content!], { type: "text/html" });
                const url = URL.createObjectURL(blob);
                window.open(url, "_blank");
              }}
              className="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
            >
              View Report
            </button>
            <button
              onClick={() => {
                const blob = new Blob([state.html_report_content!], { type: "text/html" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "executive_report.html";
                a.click();
                URL.revokeObjectURL(url);
              }}
              className="px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
            >
              Download HTML
            </button>
          </div>
        </div>
      );

    case "infographic_generation":
      if (!state.infographic_base64) {
        return <p className="text-gray-500 text-sm italic">Creating infographic...</p>;
      }
      return (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-sm text-green-700">Executive infographic generated</span>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  const win = window.open("", "_blank");
                  if (win) {
                    win.document.write(`<img src="${state.infographic_base64}" style="max-width:100%;"/>`);
                  }
                }}
                className="px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              >
                View Image
              </button>
              <a
                href={state.infographic_base64}
                download="infographic.png"
                className="px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
              >
                Download PNG
              </a>
            </div>
          </div>
          {/* Small thumbnail preview */}
          <img
            src={state.infographic_base64}
            alt="Infographic preview"
            className="w-32 h-auto rounded shadow-sm border"
          />
        </div>
      );

    default:
      return null;
  }
}
