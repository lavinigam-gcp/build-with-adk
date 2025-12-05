import type { PipelineProgressProps, StageConfig } from "@/lib/types";

/**
 * Stage configuration matching the pipeline stages in callbacks/pipeline_callbacks.py
 */
const STAGES: StageConfig[] = [
  { id: "intake", label: "Parsing Request", icon: "📝" },
  { id: "market_research", label: "Market Research", icon: "🔍" },
  { id: "competitor_mapping", label: "Competitor Mapping", icon: "📍" },
  { id: "gap_analysis", label: "Gap Analysis", icon: "📊" },
  { id: "strategy_synthesis", label: "Strategy Synthesis", icon: "🧠" },
  { id: "report_generation", label: "Report Generation", icon: "📄" },
  { id: "infographic_generation", label: "Infographic", icon: "🎨" },
];

/**
 * PipelineProgress component displays the current state of the 7-stage
 * analysis pipeline with visual indicators for completed, current, and pending stages.
 */
export function PipelineProgress({
  currentStage,
  completedStages,
}: PipelineProgressProps) {
  const completedCount = completedStages?.length || 0;
  const progressPercent = Math.round((completedCount / STAGES.length) * 100);

  return (
    <div className="bg-white rounded-xl shadow-sm border p-5">
      {/* Header with progress */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <span className="text-lg">⚡</span>
          Pipeline Progress
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">
            {completedCount}/{STAGES.length} complete
          </span>
          <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Stage list */}
      <div className="space-y-2">
        {STAGES.map((stage, index) => {
          const isComplete = completedStages?.includes(stage.id);
          const isCurrent = currentStage === stage.id && !isComplete;  // Prioritize complete over current
          const isPending = !isComplete && !isCurrent;

          return (
            <div
              key={stage.id}
              className={`flex items-center gap-3 p-3 rounded-lg transition-all duration-300 ${
                isComplete
                  ? "bg-green-50 border border-green-200"
                  : isCurrent
                  ? "bg-amber-50 border border-amber-200"
                  : "bg-gray-50 border border-gray-100"
              }`}
            >
              {/* Stage number/icon */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  isComplete
                    ? "bg-green-500 text-white"
                    : isCurrent
                    ? "bg-amber-500 text-white"
                    : "bg-gray-200 text-gray-500"
                }`}
              >
                {isComplete ? "✓" : index + 1}
              </div>

              {/* Stage icon and label */}
              <span className="text-xl">{isComplete ? "✅" : isCurrent ? "⏳" : stage.icon}</span>
              <span
                className={`font-medium flex-1 ${
                  isComplete
                    ? "text-green-700"
                    : isCurrent
                    ? "text-amber-700"
                    : "text-gray-500"
                }`}
              >
                {stage.label}
              </span>

              {/* Status indicator */}
              {isCurrent && (
                <span className="text-xs text-amber-600 font-medium flex items-center gap-1">
                  <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
                  In Progress
                </span>
              )}
              {isComplete && (
                <span className="text-xs text-green-600 font-medium">Done</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
