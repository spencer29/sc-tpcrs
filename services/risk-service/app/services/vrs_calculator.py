"""Composite Vendor Risk Score (VRS) computation.

VRS is defined on a 0-100 scale where **higher = greater risk**. Each
category source, however, returns a 0-100 *goodness* sub-score (100 = a
healthy/proven vendor in that dimension, 0 = a maximally risky one -- e.g.
`vulnerability_source` starts at 100 and subtracts penalties for CVEs, so a
vendor with zero known vulnerabilities scores 100). VRS is therefore the
weighted average of those goodness scores, inverted: `VRS = 100 -
weighted_goodness`. This is what makes the tier bands below internally
consistent (a Critical-risk vendor -- lots of CVEs, poor posture -- has LOW
goodness scores and therefore a HIGH VRS, correctly landing in the Critical
band).
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AnomalyFlag, RiskScoreHistory
from .anomaly.model import evaluate_anomaly
from .category_sources.breach_history_source import get_breach_history_score
from .category_sources.compliance_source import get_compliance_score
from .category_sources.external_posture_source import get_external_posture_score
from .category_sources.questionnaire_source import get_questionnaire_score
from .category_sources.threat_intel_source import get_threat_intel_score
from .category_sources.vulnerability_source import get_vulnerability_score

WEIGHTS: dict[str, float] = {
    "questionnaire_score": 0.25,
    "external_posture_score": 0.20,
    "vulnerability_score": 0.20,
    "breach_history_score": 0.15,
    "threat_intel_score": 0.15,
    "compliance_score": 0.05,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "VRS category weights must sum to 1.0"

TIER_BANDS: tuple[tuple[float, str], ...] = (
    (75.0, "Critical"),
    (55.0, "High"),
    (35.0, "Medium"),
)


def tier_for_vrs(vrs: float) -> str:
    for threshold, tier in TIER_BANDS:
        if vrs >= threshold:
            return tier
    return "Low"


def compute_vrs(scores: dict[str, float]) -> float:
    weighted_goodness = sum(scores[key] * weight for key, weight in WEIGHTS.items())
    vrs = 100.0 - weighted_goodness
    return round(min(100.0, max(0.0, vrs)), 2)


async def compute_for_vendor(
    db: AsyncSession, vendor_id: uuid.UUID | str
) -> tuple[RiskScoreHistory, AnomalyFlag | None]:
    vendor_id_str = str(vendor_id)

    scores = {
        "questionnaire_score": await get_questionnaire_score(vendor_id_str),
        "external_posture_score": await get_external_posture_score(vendor_id_str),
        "vulnerability_score": await get_vulnerability_score(db, vendor_id_str),
        "breach_history_score": await get_breach_history_score(vendor_id_str),
        "threat_intel_score": await get_threat_intel_score(vendor_id_str),
        "compliance_score": await get_compliance_score(vendor_id_str),
    }

    vrs = compute_vrs(scores)
    tier = tier_for_vrs(vrs)

    row = RiskScoreHistory(
        vendor_id=vendor_id,
        vrs_score=vrs,
        tier=tier,
        inputs_snapshot=scores,
        **scores,
    )
    db.add(row)
    await db.flush()

    anomaly = await evaluate_anomaly(db, vendor_id, row)
    return row, anomaly
