import type { TimelineStepConfig } from "@/lib/types";

/**
 * Timeline step configurations matching the pipeline stages.
 * This is the single source of truth for pipeline steps.
 */
export const TIMELINE_STEPS: TimelineStepConfig[] = [
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
    tool: { icon: "🔍", name: "google_search" },
  },
  {
    id: "competitor_mapping",
    label: "Competitor Analysis",
    stageKey: "competitor_mapping",
    tool: { icon: "📍", name: "search_places" },
  },
  {
    id: "gap_analysis",
    label: "Gap Analysis",
    stageKey: "gap_analysis",
    tool: { icon: "🐍", name: "python_code" },
  },
  {
    id: "strategy_synthesis",
    label: "Strategic Synthesis",
    stageKey: "strategy_synthesis",
    tool: { icon: "🧠", name: "deep_thinking" },
  },
  {
    id: "report_generation",
    label: "Executive Report",
    stageKey: "report_generation",
    tool: { icon: "📄", name: "html_report" },
  },
  {
    id: "infographic_generation",
    label: "Visual Infographic",
    stageKey: "infographic_generation",
    tool: { icon: "🎨", name: "image_gen" },
  },
  {
    id: "audio_overview_generation",
    label: "Audio Overview",
    stageKey: "audio_overview_generation",
    tool: { icon: "🎵", name: "audio_gen" },
  },
];
