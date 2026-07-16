import type { Tier } from "../types/vendor";
import { TIER_COLOR_VAR } from "../lib/tierColors";

interface VrsGaugeProps {
  score: number;
  tier: Tier;
}

/** Single-value hero figure + horizontal fill bar. A single series never
 * needs a legend (the label names it directly) -- see dataviz skill,
 * choosing-a-form.md. Color is paired with a visible tier-name label so
 * meaning is never carried by hue alone. */
export function VrsGauge({ score, tier }: VrsGaugeProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const color = TIER_COLOR_VAR[tier];

  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
        <span style={{ fontSize: "2.5rem", fontWeight: 700, color: "hsl(var(--foreground))" }}>
          {clamped.toFixed(1)}
        </span>
        <span style={{ color: "hsl(var(--muted-foreground))", fontSize: "0.9rem" }}>/ 100 risk score</span>
      </div>
      <div
        role="img"
        aria-label={`Vendor risk score ${clamped.toFixed(1)} out of 100, tier ${tier}`}
        style={{
          marginTop: 8,
          height: 12,
          borderRadius: 6,
          background: "hsl(var(--border))",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${clamped}%`,
            height: "100%",
            background: color,
            borderRadius: 6,
            transition: "width 200ms ease",
          }}
        />
      </div>
      <div style={{ marginTop: 8 }}>
        <span className="tier-badge" style={{ backgroundColor: color }}>
          {tier} risk
        </span>
      </div>
    </div>
  );
}
