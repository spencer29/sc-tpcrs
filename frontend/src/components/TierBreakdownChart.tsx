import type { Tier } from "../types/vendor";
import { TIER_COLOR_VAR, TIER_ORDER } from "../lib/tierColors";

interface TierBreakdownChartProps {
  breakdown: Record<string, number>;
}

/** 4 status-colored categories, direct-labeled -- no separate legend box
 * needed per the dataviz skill (<=4 series may be direct-labeled instead of
 * a legend). Horizontal bars, thin marks, rounded data-ends. */
export function TierBreakdownChart({ breakdown }: TierBreakdownChartProps) {
  const total = Object.values(breakdown).reduce((sum, n) => sum + n, 0) || 1;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {TIER_ORDER.map((tier: Tier) => {
        const count = breakdown[tier] ?? 0;
        const pct = (count / total) * 100;
        return (
          <div key={tier}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "0.85rem",
                marginBottom: 4,
                color: "var(--text-secondary)",
              }}
            >
              <span>{tier}</span>
              <span>{count}</span>
            </div>
            <div style={{ height: 8, borderRadius: 4, background: "var(--gridline)", overflow: "hidden" }}>
              <div
                style={{
                  width: `${pct}%`,
                  minWidth: count > 0 ? 4 : 0,
                  height: "100%",
                  background: TIER_COLOR_VAR[tier],
                  borderRadius: 4,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
