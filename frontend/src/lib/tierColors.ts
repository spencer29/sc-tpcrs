import type { Tier } from "../types/vendor";

// Risk tier is a status encoding (state of risk), not an arbitrary
// category, so it maps onto the dataviz skill's fixed status palette
// rather than the categorical one: Low->good, Medium->warning,
// High->serious, Critical->critical. These are the skill's validated
// default hex steps -- see frontend/src/styles/theme.css.
export const TIER_COLOR_VAR: Record<Tier, string> = {
  Low: "var(--status-good)",
  Medium: "var(--status-warning)",
  High: "var(--status-serious)",
  Critical: "var(--status-critical)",
};

export const TIER_ORDER: Tier[] = ["Critical", "High", "Medium", "Low"];
