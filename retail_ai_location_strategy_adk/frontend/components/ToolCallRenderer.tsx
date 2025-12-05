"use client";

import { useCopilotAction } from "@copilotkit/react-core";

/**
 * Tool configuration for visual display
 */
const TOOL_CONFIG: Record<string, { icon: string; label: string }> = {
  search_places: { icon: "📍", label: "Searching Google Maps" },
  execute_python_code: { icon: "🐍", label: "Analyzing Data" },
  google_search: { icon: "🔍", label: "Researching Market" },
  generate_html_report: { icon: "📄", label: "Generating Report" },
  generate_infographic: { icon: "🎨", label: "Creating Infographic" },
};

interface ToolCallCardProps {
  name: string;
  status: "pending" | "executing" | "complete";
}

/**
 * ToolCallCard displays a single tool call with its status
 */
function ToolCallCard({ name, status }: ToolCallCardProps) {
  const config = TOOL_CONFIG[name] || { icon: "🔧", label: name };

  return (
    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border my-2">
      <span className="text-xl">{config.icon}</span>
      <span className="font-medium text-gray-700">{config.label}</span>
      {status === "executing" && (
        <span className="ml-auto flex items-center gap-2">
          <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
          <span className="text-xs text-amber-600">Running...</span>
        </span>
      )}
      {status === "complete" && (
        <span className="ml-auto text-green-500 flex items-center gap-1">
          <span>✓</span>
          <span className="text-xs text-green-600">Done</span>
        </span>
      )}
    </div>
  );
}

/**
 * Hook to render tool calls in the chat
 * Uses useCopilotAction to register render handlers for each tool
 */
export function useToolCallRenderer() {
  // Register render handlers for known tools
  // Note: useCopilotAction requires specific tool registration
  // For AG-UI agents, tool calls are displayed differently

  // For now, we'll use a simpler approach that tracks tool calls via state
  // The useCoAgentStateRender already handles state visualization
  // Tool calls from AG-UI come through as part of the SSE stream
}

/**
 * ToolCallsDisplay component for showing tool calls based on pipeline stage
 */
export function ToolCallsDisplay({ currentStage }: { currentStage?: string }) {
  // Map pipeline stages to their associated tool calls
  const stageTools: Record<string, string[]> = {
    market_research: ["google_search"],
    competitor_mapping: ["search_places"],
    gap_analysis: ["execute_python_code"],
    report_generation: ["generate_html_report"],
    infographic_generation: ["generate_infographic"],
  };

  const activeTools = currentStage ? stageTools[currentStage] || [] : [];

  if (activeTools.length === 0) return null;

  return (
    <div className="space-y-2">
      {activeTools.map((toolName) => (
        <ToolCallCard key={toolName} name={toolName} status="executing" />
      ))}
    </div>
  );
}
