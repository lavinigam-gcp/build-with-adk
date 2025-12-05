import type { ReportDisplayProps } from "@/lib/types";

/**
 * LocationReport component displays the top recommendation from the
 * LocationIntelligenceReport with score, strengths, concerns, and next steps.
 */
export function LocationReport({ report }: ReportDisplayProps) {
  const rec = report.top_recommendation;
  const scoreColor =
    rec.overall_score >= 75
      ? "text-green-600"
      : rec.overall_score >= 50
      ? "text-yellow-600"
      : "text-red-600";

  const scoreBg =
    rec.overall_score >= 75
      ? "from-green-500 to-emerald-600"
      : rec.overall_score >= 50
      ? "from-yellow-500 to-orange-600"
      : "from-red-500 to-rose-600";

  return (
    <div className="bg-white rounded-xl shadow-lg border-l-4 border-green-500 overflow-hidden">
      {/* Header with score */}
      <div className="p-6 bg-gradient-to-r from-gray-50 to-white border-b">
        <div className="flex justify-between items-start">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">📍</span>
              <h2 className="text-2xl font-bold text-gray-900">
                {rec.location_name}
              </h2>
            </div>
            <p className="text-gray-600">{rec.area}</p>
          </div>

          {/* Score badge */}
          <div className="text-center">
            <div
              className={`w-20 h-20 rounded-2xl bg-gradient-to-br ${scoreBg} flex flex-col items-center justify-center text-white shadow-lg`}
            >
              <div className="text-3xl font-bold">{rec.overall_score}</div>
              <div className="text-xs opacity-80">/100</div>
            </div>
          </div>
        </div>

        {/* Opportunity type badge */}
        <div className="mt-4">
          <span className="inline-flex items-center px-3 py-1.5 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
            {rec.opportunity_type}
          </span>
        </div>
      </div>

      {/* Strengths and Concerns */}
      <div className="p-6">
        <div className="grid md:grid-cols-2 gap-6">
          {/* Strengths */}
          <div>
            <h4 className="font-semibold text-green-700 mb-3 flex items-center gap-2">
              <span className="text-lg">💪</span>
              Strengths
            </h4>
            <div className="space-y-3">
              {rec.strengths.map((s, i) => (
                <div
                  key={i}
                  className="p-3 bg-green-50 rounded-lg border border-green-100"
                >
                  <div className="font-medium text-green-800 flex items-center gap-2">
                    <span>✅</span>
                    {s.factor}
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{s.description}</p>
                  {s.evidence_from_analysis && (
                    <p className="text-xs text-gray-500 mt-2 italic">
                      Evidence: {s.evidence_from_analysis}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Concerns */}
          <div>
            <h4 className="font-semibold text-orange-700 mb-3 flex items-center gap-2">
              <span className="text-lg">⚠️</span>
              Concerns & Mitigations
            </h4>
            <div className="space-y-3">
              {rec.concerns.map((c, i) => (
                <div
                  key={i}
                  className="p-3 bg-orange-50 rounded-lg border border-orange-100"
                >
                  <div className="font-medium text-orange-800 flex items-center gap-2">
                    <span>⚠️</span>
                    {c.risk}
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{c.description}</p>
                  <div className="mt-2 p-2 bg-white rounded border border-orange-100">
                    <p className="text-xs text-gray-700">
                      <span className="font-medium">Mitigation:</span>{" "}
                      {c.mitigation_strategy}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Additional info */}
        <div className="mt-6 grid md:grid-cols-2 gap-4">
          <InfoCard
            icon="👥"
            label="Target Segment"
            value={rec.best_customer_segment}
          />
          <InfoCard
            icon="🚶"
            label="Foot Traffic"
            value={rec.estimated_foot_traffic}
          />
        </div>

        {/* Next Steps */}
        {rec.next_steps && rec.next_steps.length > 0 && (
          <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
            <h4 className="font-semibold text-blue-800 mb-3 flex items-center gap-2">
              <span>🎯</span>
              Recommended Next Steps
            </h4>
            <ol className="space-y-2">
              {rec.next_steps.map((step, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3 text-gray-700"
                >
                  <span className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center text-sm font-medium text-blue-700 flex-shrink-0">
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}

function InfoCard({
  icon,
  label,
  value,
}: {
  icon: string;
  label: string;
  value: string;
}) {
  return (
    <div className="p-3 bg-gray-50 rounded-lg border">
      <div className="flex items-center gap-2 text-gray-600 text-sm mb-1">
        <span>{icon}</span>
        {label}
      </div>
      <p className="font-medium text-gray-900">{value}</p>
    </div>
  );
}
