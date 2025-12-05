"use client";

import { memo } from "react";
import type { TimelineStepConfig } from "@/lib/types";

interface CollapsibleStepProps {
  step: TimelineStepConfig;
  stepNumber: number;
  status: "pending" | "in_progress" | "complete";
  children: React.ReactNode;
  isExpanded: boolean;
  onToggle: () => void;
}

/**
 * CollapsibleStep renders a single step in the pipeline timeline.
 * Features:
 * - Visual states: pending (gray), in-progress (amber pulse), complete (green)
 * - Tool badge display on the right
 * - Expand/collapse toggle button
 * - Smooth CSS transition animation
 */
export const CollapsibleStep = memo(function CollapsibleStep({
  step,
  stepNumber,
  status,
  children,
  isExpanded,
  onToggle,
}: CollapsibleStepProps) {
  // Determine visual styling based on status
  const getStatusStyles = () => {
    switch (status) {
      case "complete":
        return {
          container: "bg-green-50 border-green-200",
          badge: "bg-green-500 text-white",
          badgeContent: "\u2713",
          icon: "\u2705",
          textColor: "text-green-700",
        };
      case "in_progress":
        return {
          container: "bg-amber-50 border-amber-200",
          badge: "bg-amber-500 text-white",
          badgeContent: stepNumber.toString(),
          icon: "\u23F3",
          textColor: "text-amber-700",
        };
      default:
        return {
          container: "bg-gray-50 border-gray-100",
          badge: "bg-gray-200 text-gray-500",
          badgeContent: stepNumber.toString(),
          icon: "\u25CB",
          textColor: "text-gray-500",
        };
    }
  };

  const styles = getStatusStyles();
  const canToggle = status === "complete";

  return (
    <div
      className={`rounded-lg border transition-all duration-300 ${styles.container}`}
    >
      {/* Step Header */}
      <div
        className={`flex items-center gap-3 p-4 ${
          canToggle ? "cursor-pointer select-none" : ""
        }`}
        onClick={canToggle ? onToggle : undefined}
      >
        {/* Step number badge */}
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0 ${styles.badge}`}
        >
          {styles.badgeContent}
        </div>

        {/* Status icon + Step label */}
        <span className="text-xl flex-shrink-0">{styles.icon}</span>
        <span className={`font-medium flex-1 ${styles.textColor}`}>
          {step.label}
        </span>

        {/* Tool badge (right side) */}
        {step.tool && (
          <span className="px-2 py-1 bg-gray-100 text-gray-500 text-xs font-mono rounded flex items-center gap-1">
            <span>{step.tool.icon}</span>
            <span>{step.tool.name}</span>
          </span>
        )}

        {/* Status indicator */}
        {status === "in_progress" && (
          <span className="text-xs text-amber-600 font-medium flex items-center gap-1">
            <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
            In Progress
          </span>
        )}

        {/* Expand/Collapse toggle for completed steps */}
        {canToggle && (
          <button
            className="p-1 hover:bg-gray-200 rounded transition-colors"
            aria-label={isExpanded ? "Collapse" : "Expand"}
          >
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform duration-200 ${
                isExpanded ? "rotate-180" : ""
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
        )}
      </div>

      {/* Collapsible Content */}
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          isExpanded && status !== "pending"
            ? "max-h-[32rem] opacity-100"
            : "max-h-0 opacity-0"
        }`}
      >
        <div className="px-4 pb-4 ml-11">
          <div className="border-l-2 border-gray-200 pl-4">{children}</div>
        </div>
      </div>
    </div>
  );
});
