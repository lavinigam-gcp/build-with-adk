/**
 * Helper functions to extract meaningful summaries from agent state
 * for display in the Pipeline Timeline.
 */

import type { LocationIntelligenceReport } from "./types";

/**
 * Truncates text to a maximum length with ellipsis.
 */
export function truncateText(text: string, maxLength: number): string {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trim() + "...";
}

/**
 * Summarizes market research findings for timeline display.
 * Extracts first 1-2 sentences or key points.
 */
export function summarizeMarketResearch(findings: string | undefined, maxLength = 150): string {
  if (!findings) return "Market research in progress...";

  // Try to extract meaningful first sentence
  const sentences = findings.split(/[.!?]\s+/);
  if (sentences.length > 0) {
    const firstSentence = sentences[0].trim();
    if (firstSentence.length <= maxLength) {
      return firstSentence + (sentences[0].match(/[.!?]/) ? "" : "...");
    }
  }

  return truncateText(findings, maxLength);
}

/**
 * Summarizes competitor analysis for timeline display.
 * Uses strategic report data if available, otherwise extracts from raw analysis.
 */
export function summarizeCompetitorAnalysis(
  analysis: string | undefined,
  report?: LocationIntelligenceReport
): string {
  // If we have strategic report data, use the precise numbers
  if (report) {
    const total = report.total_competitors_found;
    const rec = report.top_recommendation;
    const highPerformers = rec.competition?.high_performers_count ?? 0;
    const avgRating = rec.competition?.avg_competitor_rating?.toFixed(1) ?? "N/A";

    return `Found ${total} competitors \u2022 ${highPerformers} high-performers \u2022 ${avgRating} avg rating`;
  }

  // Fallback: extract numbers from raw analysis if present
  if (analysis) {
    // Look for patterns like "Found X competitors"
    const competitorMatch = analysis.match(/(\d+)\s*(competitors?|businesses?|locations?)/i);
    if (competitorMatch) {
      return `Found ${competitorMatch[1]} ${competitorMatch[2].toLowerCase()}`;
    }
    return truncateText(analysis, 100);
  }

  return "Mapping competitors...";
}

/**
 * Summarizes gap analysis for timeline display.
 * Uses strategic report data if available, otherwise extracts from raw analysis.
 */
export function summarizeGapAnalysis(
  analysis: string | undefined,
  report?: LocationIntelligenceReport
): string {
  // If we have strategic report data, use zone info
  if (report) {
    const zones = report.zones_analyzed;
    const topRec = report.top_recommendation;
    const topZone = topRec.location_name;
    const score = topRec.overall_score;

    return `${zones} zones analyzed \u2022 ${topZone} ranks #1 (score: ${score})`;
  }

  // Fallback: extract from raw analysis
  if (analysis) {
    // Look for patterns like "X zones"
    const zoneMatch = analysis.match(/(\d+)\s*zones?/i);
    if (zoneMatch) {
      return `${zoneMatch[1]} zones analyzed`;
    }
    return truncateText(analysis, 100);
  }

  return "Analyzing market gaps...";
}

/**
 * Extracts top recommendation summary from strategic report.
 */
export function extractTopRecommendation(report: LocationIntelligenceReport | undefined): {
  location: string;
  score: number;
  opportunityType: string;
} | null {
  if (!report || !report.top_recommendation) return null;

  const rec = report.top_recommendation;
  return {
    location: rec.location_name,
    score: rec.overall_score,
    opportunityType: rec.opportunity_type,
  };
}

/**
 * Returns a descriptive status for strategic synthesis step.
 */
export function summarizeStrategicSynthesis(report: LocationIntelligenceReport | undefined): string {
  if (!report) return "Synthesizing strategy...";

  const rec = report.top_recommendation;
  return `Top Pick: ${rec.location_name} \u2022 "${rec.opportunity_type}" opportunity`;
}
