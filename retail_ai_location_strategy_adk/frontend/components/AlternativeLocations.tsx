import type { AlternativeLocation } from "@/lib/types";

interface AlternativeLocationsProps {
  locations: AlternativeLocation[];
}

/**
 * AlternativeLocations displays the alternative location options
 * from the analysis report.
 */
export function AlternativeLocations({ locations }: AlternativeLocationsProps) {
  if (!locations || locations.length === 0) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border p-5">
      <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <span className="text-xl">🗺️</span>
        Alternative Locations
      </h3>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {locations.map((loc, i) => (
          <div
            key={i}
            className="p-4 bg-gray-50 rounded-lg border hover:border-blue-200 hover:shadow-sm transition-all"
          >
            {/* Header */}
            <div className="flex justify-between items-start mb-3">
              <div>
                <h4 className="font-medium text-gray-900">{loc.location_name}</h4>
                <p className="text-sm text-gray-500">{loc.area}</p>
              </div>
              <div
                className={`w-12 h-12 rounded-lg flex flex-col items-center justify-center text-white ${
                  loc.overall_score >= 75
                    ? "bg-green-500"
                    : loc.overall_score >= 50
                    ? "bg-yellow-500"
                    : "bg-gray-400"
                }`}
              >
                <span className="font-bold">{loc.overall_score}</span>
                <span className="text-xs opacity-80">/100</span>
              </div>
            </div>

            {/* Type badge */}
            <span className="inline-block px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium mb-3">
              {loc.opportunity_type}
            </span>

            {/* Strength */}
            <div className="mb-2">
              <div className="text-xs text-gray-500 mb-1">Key Strength</div>
              <div className="text-sm text-green-700 flex items-start gap-1">
                <span>✅</span>
                {loc.key_strength}
              </div>
            </div>

            {/* Concern */}
            <div className="mb-3">
              <div className="text-xs text-gray-500 mb-1">Key Concern</div>
              <div className="text-sm text-orange-700 flex items-start gap-1">
                <span>⚠️</span>
                {loc.key_concern}
              </div>
            </div>

            {/* Why not top */}
            <div className="pt-3 border-t border-gray-200">
              <div className="text-xs text-gray-500 italic">
                {loc.why_not_top}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
