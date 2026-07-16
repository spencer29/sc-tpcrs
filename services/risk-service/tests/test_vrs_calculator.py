from __future__ import annotations

from app.services.vrs_calculator import WEIGHTS, compute_vrs, tier_for_vrs


def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_perfect_vendor_scores_zero_vrs():
    scores = {key: 100.0 for key in WEIGHTS}
    assert compute_vrs(scores) == 0.0


def test_worst_vendor_scores_hundred_vrs():
    scores = {key: 0.0 for key in WEIGHTS}
    assert compute_vrs(scores) == 100.0


def test_known_weighted_mix():
    # 0.25*80 + 0.20*60 + 0.20*40 + 0.15*100 + 0.15*100 + 0.05*0
    # = 20 + 12 + 8 + 15 + 15 + 0 = 70 (goodness) -> VRS = 100 - 70 = 30
    scores = {
        "questionnaire_score": 80.0,
        "external_posture_score": 60.0,
        "vulnerability_score": 40.0,
        "breach_history_score": 100.0,
        "threat_intel_score": 100.0,
        "compliance_score": 0.0,
    }
    assert compute_vrs(scores) == 30.0


def test_vrs_is_clamped_to_0_100_range():
    # Weights already guarantee this mathematically for in-range inputs, but
    # assert the clamp explicitly in case a category source ever returns an
    # out-of-range value due to a bug.
    scores = {key: 100.0 for key in WEIGHTS}
    scores["questionnaire_score"] = 1000.0  # pathological input
    assert 0.0 <= compute_vrs(scores) <= 100.0


def test_tier_bands():
    assert tier_for_vrs(100.0) == "Critical"
    assert tier_for_vrs(75.0) == "Critical"
    assert tier_for_vrs(74.99) == "High"
    assert tier_for_vrs(55.0) == "High"
    assert tier_for_vrs(54.99) == "Medium"
    assert tier_for_vrs(35.0) == "Medium"
    assert tier_for_vrs(34.99) == "Low"
    assert tier_for_vrs(0.0) == "Low"
