from __future__ import annotations

import uuid

from app.control_library import ControlSpec
from app.services import assessment_engine as engine


def _spec(cid: str, weight: int) -> ControlSpec:
    return ControlSpec(
        control_id=cid,
        framework="ISO 27001:2022",
        reference=cid,
        domain="Test",
        title=f"control {cid}",
        objective="obj",
        weight=weight,
    )


def test_score_is_weighted_and_excludes_not_applicable():
    results = [
        engine.EvaluatedControl(_spec("A", 5), engine.MET, False, "", ""),
        engine.EvaluatedControl(_spec("B", 1), engine.GAP, False, "", ""),
        engine.EvaluatedControl(_spec("C", 4), engine.PARTIAL, False, "", ""),
        engine.EvaluatedControl(_spec("D", 3), engine.NOT_APPLICABLE, False, "", ""),
    ]
    # earned = 1.0*5 + 0*1 + 0.5*4 = 7 ; possible = 5+1+4 = 10 (D excluded)
    assert engine.compliance_score(results) == 70.0


def test_all_not_applicable_scores_100():
    results = [engine.EvaluatedControl(_spec("A", 5), engine.NOT_APPLICABLE, False, "", "")]
    assert engine.compliance_score(results) == 100.0


def test_status_thresholds():
    assert engine.status_from_score(90) == "Compliant"
    assert engine.status_from_score(85) == "Compliant"
    assert engine.status_from_score(84.9) == "Partially Compliant"
    assert engine.status_from_score(60) == "Partially Compliant"
    assert engine.status_from_score(59.9) == "Non-Compliant"


def test_evaluation_is_deterministic_for_a_vendor():
    vid = str(uuid.uuid4())
    first = engine.evaluate_controls(vid, "ISO 27001:2022")
    second = engine.evaluate_controls(vid, "ISO 27001:2022")
    assert [(r.spec.control_id, r.status) for r in first] == [
        (r.spec.control_id, r.status) for r in second
    ]


def test_different_vendors_get_different_assessments():
    a = engine.evaluate_controls(str(uuid.uuid4()), "ISO 27001:2022")
    b = engine.evaluate_controls(str(uuid.uuid4()), "ISO 27001:2022")
    assert [r.status for r in a] != [r.status for r in b]


def test_critical_gap_only_flags_material_controls():
    for r in engine.evaluate_controls(str(uuid.uuid4()), "ALL"):
        if r.is_critical_gap:
            assert r.status == engine.GAP
            assert r.spec.weight >= engine.CRITICAL_GAP_WEIGHT


def test_overrides_take_precedence():
    vid = str(uuid.uuid4())
    baseline = engine.evaluate_controls(vid, "ISO 27001:2022")
    target = baseline[0].spec.control_id
    overridden = engine.evaluate_controls(
        vid,
        "ISO 27001:2022",
        overrides={target: {"status": engine.MET, "evidence": "manual review", "remediation": ""}},
    )
    hit = next(r for r in overridden if r.spec.control_id == target)
    assert hit.status == engine.MET
    assert hit.evidence == "manual review"


def test_gap_ranking_puts_critical_first():
    results = engine.evaluate_controls(str(uuid.uuid4()), "ALL")
    ranked = engine.rank_gaps(results)
    # Once we hit the first non-critical gap, no critical gap may follow.
    seen_non_critical = False
    for r in ranked:
        if not r.is_critical_gap:
            seen_non_critical = True
        elif seen_non_critical:
            raise AssertionError("critical gap ranked after a non-critical one")


def test_resolve_scope_rejects_unknown_framework():
    import pytest

    with pytest.raises(ValueError):
        engine.resolve_scope("NIST CSF")


def test_domain_breakdown_covers_all_controls():
    results = engine.evaluate_controls(str(uuid.uuid4()), "PCI DSS v4.0")
    rows = engine.domain_breakdown(results)
    assert sum(row["total"] for row in rows) == len(results)
