import type { Tier } from "../types/vendor";
import { TIER_COLOR_VAR } from "../lib/tierColors";

export function VendorTierBadge({ tier }: { tier: Tier }) {
  return (
    <span className="tier-badge" style={{ backgroundColor: TIER_COLOR_VAR[tier] }}>
      {tier}
    </span>
  );
}
