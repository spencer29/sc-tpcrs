from __future__ import annotations

from sc_tpcrs_common.redis_cache import TTL_DASHBOARD_SUMMARY, RedisCache, cached
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import RiskScoreHistory

TIER_ORDER = ("Critical", "High", "Medium", "Low")
VRS_BUCKETS = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]
TOP_RISK_LIMIT = 10


async def _latest_score_per_vendor(db: AsyncSession) -> list[RiskScoreHistory]:
    stmt = select(RiskScoreHistory).order_by(RiskScoreHistory.vendor_id, RiskScoreHistory.computed_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    latest: dict[str, RiskScoreHistory] = {}
    for row in rows:
        key = str(row.vendor_id)
        if key not in latest:
            latest[key] = row
    return list(latest.values())


def _row_to_dict(row: RiskScoreHistory) -> dict:
    return {
        "vendor_id": str(row.vendor_id),
        "vrs_score": float(row.vrs_score),
        "questionnaire_score": float(row.questionnaire_score),
        "external_posture_score": float(row.external_posture_score),
        "vulnerability_score": float(row.vulnerability_score),
        "breach_history_score": float(row.breach_history_score),
        "threat_intel_score": float(row.threat_intel_score),
        "compliance_score": float(row.compliance_score),
        "tier": row.tier,
        "computed_at": row.computed_at.isoformat() if row.computed_at else None,
    }


class DashboardService:
    def __init__(self, cache: RedisCache) -> None:
        self.cache = cache

    @cached("cache", key_fn=lambda db: "dashboard:summary", ttl_seconds=TTL_DASHBOARD_SUMMARY)
    async def get_summary(self, db: AsyncSession) -> dict:
        latest = await _latest_score_per_vendor(db)

        tier_breakdown = {tier: 0 for tier in TIER_ORDER}
        vrs_distribution = {f"{lo}-{hi}": 0 for lo, hi in VRS_BUCKETS}
        for row in latest:
            tier_breakdown[row.tier] = tier_breakdown.get(row.tier, 0) + 1
            vrs = float(row.vrs_score)
            for lo, hi in VRS_BUCKETS:
                if lo <= vrs < hi:
                    vrs_distribution[f"{lo}-{hi}"] += 1
                    break

        top_risk = sorted(latest, key=lambda r: float(r.vrs_score), reverse=True)[:TOP_RISK_LIMIT]

        return {
            "tier_breakdown": tier_breakdown,
            "vrs_distribution": vrs_distribution,
            "top_risk_vendors": [_row_to_dict(r) for r in top_risk],
        }
