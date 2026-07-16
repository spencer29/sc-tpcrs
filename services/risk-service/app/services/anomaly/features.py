from __future__ import annotations

TIER_ORDINAL: dict[str, int] = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}

FEATURE_NAMES: list[str] = [
    "questionnaire_score",
    "external_posture_score",
    "vulnerability_score",
    "breach_history_score",
    "threat_intel_score",
    "compliance_score",
    "vrs_score",
    "tier_ordinal",
    "vrs_delta_vs_previous",
]


def build_feature_vector(
    *,
    questionnaire_score: float,
    external_posture_score: float,
    vulnerability_score: float,
    breach_history_score: float,
    threat_intel_score: float,
    compliance_score: float,
    vrs_score: float,
    tier: str,
    vrs_delta_vs_previous: float,
) -> list[float]:
    return [
        questionnaire_score,
        external_posture_score,
        vulnerability_score,
        breach_history_score,
        threat_intel_score,
        compliance_score,
        vrs_score,
        float(TIER_ORDINAL[tier]),
        vrs_delta_vs_previous,
    ]
