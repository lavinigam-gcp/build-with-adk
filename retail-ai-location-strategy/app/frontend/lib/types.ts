/**
 * TypeScript types matching Pydantic schemas in schemas/report_schema.py
 *
 * These types mirror the exact structure of the Python Pydantic models
 * to ensure type safety when consuming agent state in the frontend.
 */

// =============================================================================
// Report Schema Types (from schemas/report_schema.py)
// =============================================================================

/**
 * Detailed strength with evidence.
 * Matches: StrengthAnalysis Pydantic model
 */
export interface StrengthAnalysis {
  factor: string;
  description: string;
  evidence_from_analysis: string;
}

/**
 * Detailed concern with mitigation strategy.
 * Matches: ConcernAnalysis Pydantic model
 */
export interface ConcernAnalysis {
  risk: string;
  description: string;
  mitigation_strategy: string;
}

/**
 * Competition characteristics in the zone.
 * Matches: CompetitionProfile Pydantic model
 */
export interface CompetitionProfile {
  total_competitors: number;
  density_per_km2: number;
  chain_dominance_pct: number;
  avg_competitor_rating: number;
  high_performers_count: number;
}

/**
 * Market fundamentals for the zone.
 * Matches: MarketCharacteristics Pydantic model
 */
export interface MarketCharacteristics {
  population_density: string; // "Low" | "Medium" | "High"
  income_level: string; // "Low" | "Medium" | "High"
  infrastructure_access: string;
  foot_traffic_pattern: string;
  rental_cost_tier: string; // "Low" | "Medium" | "High"
}

/**
 * Complete recommendation for a specific location.
 * Matches: LocationRecommendation Pydantic model
 */
export interface LocationRecommendation {
  location_name: string;
  area: string;
  overall_score: number; // 0-100
  opportunity_type: string;
  strengths: StrengthAnalysis[];
  concerns: ConcernAnalysis[];
  competition: CompetitionProfile;
  market: MarketCharacteristics;
  best_customer_segment: string;
  estimated_foot_traffic: string;
  next_steps: string[];
}

/**
 * Brief summary of alternative location.
 * Matches: AlternativeLocation Pydantic model
 */
export interface AlternativeLocation {
  location_name: string;
  area: string;
  overall_score: number; // 0-100
  opportunity_type: string;
  key_strength: string;
  key_concern: string;
  why_not_top: string;
}

/**
 * Complete location intelligence analysis report.
 * Matches: LocationIntelligenceReport Pydantic model
 */
export interface LocationIntelligenceReport {
  target_location: string;
  business_type: string;
  analysis_date: string;
  market_validation: string;
  total_competitors_found: number;
  zones_analyzed: number;
  top_recommendation: LocationRecommendation;
  alternative_locations: AlternativeLocation[];
  key_insights: string[];
  methodology_summary: string;
}

// =============================================================================
// Agent State Type (from callbacks/pipeline_callbacks.py)
// =============================================================================

/**
 * Pipeline stage identifiers matching callbacks.
 */
export type PipelineStage =
  | "intake"
  | "market_research"
  | "competitor_mapping"
  | "gap_analysis"
  | "strategy_synthesis"
  | "report_generation"
  | "infographic_generation";

/**
 * Complete agent state type for useCoAgent hook.
 * These fields are set by the existing callbacks in pipeline_callbacks.py
 */
export interface AgentState {
  // Pipeline tracking (set by before_*/after_* callbacks)
  pipeline_stage: PipelineStage | string;
  stages_completed: string[];
  pipeline_start_time?: string;

  // User request (set by IntakeAgent via after_intake callback)
  target_location: string;
  business_type: string;
  additional_context?: string;

  // Intermediate analysis results
  market_research_findings?: string;
  competitor_analysis?: string;
  gap_analysis?: string;
  gap_analysis_code?: string; // Extracted Python code from gap analysis

  // Final strategic report (set by StrategyAdvisorAgent)
  strategic_report?: LocationIntelligenceReport;

  // Artifact content (set by tools for AG-UI frontend display)
  html_report_content?: string;
  infographic_base64?: string;
  audio_overview_base64?: string;

  // Metadata
  current_date?: string;
}

// =============================================================================
// UI Helper Types
// =============================================================================

/**
 * Stage display configuration for PipelineProgress component.
 */
export interface StageConfig {
  id: string;
  label: string;
  icon: string;
}

/**
 * Props for components that display report data.
 */
export interface ReportDisplayProps {
  report: LocationIntelligenceReport;
}

/**
 * Props for pipeline progress visualization.
 */
export interface PipelineProgressProps {
  currentStage: string;
  completedStages: string[];
}

// =============================================================================
// Timeline Component Types
// =============================================================================

/**
 * Configuration for a single timeline step.
 */
export interface TimelineStepConfig {
  id: string;
  label: string;
  stageKey: string; // Key to check in stages_completed
  tool: { icon: string; name: string } | null;
}

/**
 * Track which steps are collapsed (step id -> collapsed state).
 */
export type CollapsedSteps = Record<string, boolean>;

/**
 * Props for the main PipelineTimeline component.
 */
export interface PipelineTimelineProps {
  state: AgentState;
  currentStage?: string;
  completedStages: string[];
}

/**
 * Props for individual CollapsibleStep component.
 */
export interface CollapsibleStepProps {
  step: TimelineStepConfig;
  stepNumber: number;
  status: "pending" | "in_progress" | "complete";
  output: React.ReactNode | null;
  isExpanded: boolean;
  onToggle: () => void;
}
