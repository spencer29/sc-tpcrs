import type { Tier } from "../types/vendor";

// Risk tier is a status encoding (state of risk). Colors are hsl(var(--x))
// pulled from the same 4-step chart-1..4 ramp (green/amber/orange/red) as
// proposal-web-app--sqmuelchunech.replit.app's compiled CSS -- see
// theme.css's --tier-* tokens.
export const TIER_COLOR_VAR: Record<Tier, string> = {
  Low: "hsl(var(--tier-low))",
  Medium: "hsl(var(--tier-medium))",
  High: "hsl(var(--tier-high))",
  Critical: "hsl(var(--tier-critical))",
};

export const TIER_ORDER: Tier[] = ["Critical", "High", "Medium", "Low"];
