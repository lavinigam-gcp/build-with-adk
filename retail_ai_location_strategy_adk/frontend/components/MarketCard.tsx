import type { MarketCharacteristics } from "@/lib/types";

interface MarketCardProps {
  market: MarketCharacteristics;
}

/**
 * MarketCard displays market characteristics from the analysis.
 */
export function MarketCard({ market }: MarketCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-5">
      <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <span className="text-xl">📈</span>
        Market Characteristics
      </h3>

      <div className="space-y-3">
        <MarketRow
          label="Population Density"
          value={market.population_density}
        />
        <MarketRow
          label="Income Level"
          value={market.income_level}
        />
        <MarketRow
          label="Rental Cost"
          value={market.rental_cost_tier}
        />
        <MarketRow
          label="Foot Traffic"
          value={market.foot_traffic_pattern}
          isText
        />
        <MarketRow
          label="Infrastructure"
          value={market.infrastructure_access}
          isText
        />
      </div>
    </div>
  );
}

function MarketRow({
  label,
  value,
  isText = false,
}: {
  label: string;
  value: string;
  isText?: boolean;
}) {
  // Determine color based on value for standard High/Medium/Low values
  const getValueStyle = (val: string) => {
    const normalized = val.toLowerCase();
    if (normalized === "high" || normalized.includes("high")) {
      return "bg-green-100 text-green-800";
    }
    if (normalized === "medium" || normalized.includes("medium") || normalized.includes("moderate")) {
      return "bg-yellow-100 text-yellow-800";
    }
    if (normalized === "low" || normalized.includes("low")) {
      return "bg-gray-100 text-gray-800";
    }
    // For non-standard values, use neutral styling
    return "bg-blue-50 text-blue-800";
  };

  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-100 last:border-0">
      <span className="text-gray-600 text-sm">{label}</span>
      {isText ? (
        <span className="text-sm text-gray-800 text-right max-w-[60%]">
          {value}
        </span>
      ) : (
        <span
          className={`px-3 py-1 rounded-full text-sm font-medium ${getValueStyle(
            value
          )}`}
        >
          {value}
        </span>
      )}
    </div>
  );
}
