"use client";

import { useState, useMemo, useCallback } from "react";
import type { AgentState, TimelineStepConfig, CollapsedSteps } from "@/lib/types";
import { CollapsibleStep } from "./CollapsibleStep";
import { StepOutputContent } from "./StepOutputContent";

/**
 * Timeline step configurations matching the pipeline stages.
 */
const TIMELINE_STEPS: TimelineStepConfig[] = [
  {
    id: "intake",
    label: "Request Parsed",
    stageKey: "intake",
    tool: null,
  },
  {
    id: "market_research",
    label: "Market Research",
    stageKey: "market_research",
    tool: { icon: "\uD83D\uDD0D", name: "google_search" },
  },
  {
    id: "competitor_mapping",
    label: "Competitor Analysis",
    stageKey: "competitor_mapping",
    tool: { icon: "\uD83D\uDCCD", name: "search_places" },
  },
  {
    id: "gap_analysis",
    label: "Gap Analysis",
    stageKey: "gap_analysis",
    tool: { icon: "\uD83D\uDC0D", name: "python_code" },
  },
  {
    id: "strategy_synthesis",
    label: "Strategic Synthesis",
    stageKey: "strategy_synthesis",
    tool: { icon: "\uD83E\uDDE0", name: "deep_thinking" },
  },
  {
    id: "report_generation",
    label: "Executive Report",
    stageKey: "report_generation",
    tool: { icon: "\uD83D\uDCC4", name: "html_report" },
  },
  {
    id: "infographic_generation",
    label: "Visual Infographic",
    stageKey: "infographic_generation",
    tool: { icon: "\uD83C\uDFA8", name: "image_gen" },
  },
];

interface PipelineTimelineProps {
  state: AgentState;
  currentStage?: string;
  completedStages: string[];
}

/**
 * PipelineTimeline - Main dashboard component showing the pipeline journey.
 *
 * Features:
 * - Header card with business info and score
 * - Collapsible steps for each pipeline stage
 * - Real-time progress tracking
 * - Tool badges and output summaries
 */
export function PipelineTimeline({
  state,
  currentStage,
  completedStages,
}: PipelineTimelineProps) {
  // Track collapsed state for each step (default: all expanded)
  const [collapsed, setCollapsed] = useState<CollapsedSteps>({});

  // Toggle collapse state for a step
  const toggleStep = useCallback((stepId: string) => {
    setCollapsed((prev) => ({
      ...prev,
      [stepId]: !prev[stepId],
    }));
  }, []);

  // Determine status for each step
  const getStepStatus = useCallback(
    (step: TimelineStepConfig): "pending" | "in_progress" | "complete" => {
      if (completedStages.includes(step.stageKey)) {
        return "complete";
      }
      if (currentStage === step.stageKey || currentStage === step.id) {
        return "in_progress";
      }
      return "pending";
    },
    [completedStages, currentStage]
  );

  // Calculate progress
  const completedCount = completedStages.length;
  const progressPercent = Math.round((completedCount / TIMELINE_STEPS.length) * 100);

  // Get score from strategic report if available
  const score = state.strategic_report?.top_recommendation?.overall_score;
  const scoreColor = score
    ? score >= 75
      ? "from-green-500 to-emerald-600"
      : score >= 50
      ? "from-yellow-500 to-orange-600"
      : "from-red-500 to-rose-600"
    : "from-blue-500 to-indigo-600";

  // Check if intake step should show (when target_location is set)
  const showIntake = Boolean(state.target_location);

  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
      {/* Header Card - Business Info */}
      <div className="p-6 bg-gradient-to-r from-gray-50 to-white border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div
              className={`h-14 w-14 bg-gradient-to-br ${scoreColor} rounded-xl flex items-center justify-center shadow-lg`}
            >
              {score ? (
                <span className="text-white font-bold text-xl">{score}</span>
              ) : (
                <span className="text-2xl">\uD83D\uDCCD</span>
              )}
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 capitalize">
                {state.business_type || "Business"}
              </h2>
              <p className="text-gray-600">{state.target_location || "Location"}</p>
            </div>
          </div>

          {/* Progress indicator */}
          <div className="text-right">
            <div className="text-sm text-gray-500 mb-1">
              {completedCount}/{TIMELINE_STEPS.length} complete
            </div>
            <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Timeline Steps */}
      <div className="p-4 space-y-3">
        {TIMELINE_STEPS.map((step, index) => {
          const status = getStepStatus(step);

          // For intake, show when target_location is set
          // For other steps, show based on current progress
          const shouldShow =
            step.id === "intake"
              ? showIntake
              : completedStages.includes(step.stageKey) ||
                currentStage === step.stageKey ||
                currentStage === step.id ||
                // Show next pending step
                (status === "pending" &&
                  index > 0 &&
                  (completedStages.includes(TIMELINE_STEPS[index - 1].stageKey) ||
                   currentStage === TIMELINE_STEPS[index - 1].stageKey));

          if (!shouldShow) return null;

          // Intake is "complete" if target_location is set
          const actualStatus =
            step.id === "intake" && showIntake
              ? "complete"
              : status;

          // Always expand current step, use collapsed state for completed
          const isExpanded =
            actualStatus === "in_progress" || !collapsed[step.id];

          return (
            <CollapsibleStep
              key={step.id}
              step={step}
              stepNumber={index + 1}
              status={actualStatus}
              isExpanded={isExpanded}
              onToggle={() => toggleStep(step.id)}
            >
              <StepOutputContent stepId={step.id} state={state} />
            </CollapsibleStep>
          );
        })}
      </div>

      {/* All Complete indicator */}
      {completedCount === TIMELINE_STEPS.length && (
        <div className="p-4 bg-green-50 border-t border-green-100">
          <div className="flex items-center justify-center gap-2 text-green-700">
            <span className="text-xl">\u2705</span>
            <span className="font-medium">Analysis Complete</span>
          </div>
        </div>
      )}
    </div>
  );
}
