import type { CompetitionProfile } from "@/lib/types";

interface CompetitorCardProps {
  competition: CompetitionProfile;
}

/**
 * CompetitorCard displays competition statistics from the analysis.
 */
export function CompetitorCard({ competition }: CompetitorCardProps) {
  // Determine competition intensity
  const intensity =
    competition.total_competitors > 20
      ? "High"
      : competition.total_competitors > 10
      ? "Medium"
      : "Low";

  const intensityColor =
    intensity === "High"
      ? "text-red-600 bg-red-50"
      : intensity === "Medium"
      ? "text-yellow-600 bg-yellow-50"
      : "text-green-600 bg-green-50";

  return (
    <div className="bg-white rounded-xl shadow-sm border p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <span className="text-xl">🏪</span>
          Competition Profile
        </h3>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${intensityColor}`}>
          {intensity} Competition
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <StatBlock
          label="Total Competitors"
          value={competition.total_competitors.toString()}
          icon="📊"
        />
        <StatBlock
          label="Density/km²"
          value={competition.density_per_km2.toFixed(1)}
          icon="📍"
        />
        <StatBlock
          label="Chain Dominance"
          value={`${competition.chain_dominance_pct.toFixed(0)}%`}
          icon="🏢"
          highlight={competition.chain_dominance_pct > 50}
        />
        <StatBlock
          label="Avg Rating"
          value={`⭐ ${competition.avg_competitor_rating.toFixed(1)}`}
          icon=""
        />
        <StatBlock
          label="High Performers"
          value={competition.high_performers_count.toString()}
          icon="🏆"
          subtitle="4.5+ rating"
          highlight={competition.high_performers_count > 5}
        />
        <StatBlock
          label="Market Share"
          value={`${(100 / (competition.total_competitors + 1)).toFixed(0)}%`}
          icon="🎯"
          subtitle="Potential"
        />
      </div>
    </div>
  );
}

function StatBlock({
  label,
  value,
  icon,
  subtitle,
  highlight,
}: {
  label: string;
  value: string;
  icon?: string;
  subtitle?: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`p-3 rounded-lg text-center ${
        highlight ? "bg-amber-50 border border-amber-200" : "bg-gray-50"
      }`}
    >
      {icon && <span className="text-sm">{icon}</span>}
      <div className={`text-xl font-bold ${highlight ? "text-amber-700" : "text-blue-600"}`}>
        {value}
      </div>
      <div className="text-xs text-gray-500">{label}</div>
      {subtitle && <div className="text-xs text-gray-400 mt-0.5">{subtitle}</div>}
    </div>
  );
}
