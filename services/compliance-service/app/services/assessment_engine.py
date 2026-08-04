"""Compliance assessment + gap-analysis engine.

Given a vendor and a framework (or the whole library), this evaluates every
in-scope control and produces:

  * a per-control result (met / partial / gap / not_applicable),
  * a weighted compliance score and an overall status,
  * a gap analysis rolled up by domain, and
  * the data a regulator-ready report is rendered from.

Deviation (documented in the README): in this pass, control evidence is
generated deterministically from the vendor id rather than collected from a
real evidence store or questionnaire. The generator is seeded via SHA256
(`sc_tpcrs_common.adapters.base.seeded_random`, the same mechanism the mock
external adapters use), so a given vendor always yields the same assessment --
reproducible for demos and tests. A compliance manager can override any
control's status via the API to record a real evidence review on top of the
baseline; the interface (`run_assessment(..., overrides=...)`) is unchanged
whether the status comes from the generator or a human, so wiring a real
evidence source later is a localised change.
"""

from __future__ import annotations

from dataclasses import dataclass

from sc_tpcrs_common.adapters.base import seeded_random

from ..control_library import (
    ALL_FRAMEWORKS,
    ControlSpec,
    all_controls,
    controls_for_framework,
)

# Status constants.
MET = "met"
PARTIAL = "partial"
GAP = "gap"
NOT_APPLICABLE = "not_applicable"

# A control counts as a *critical* gap when a materially-weighted control
# (weight >= 4 on the 1-5 scale) is failing outright.
CRITICAL_GAP_WEIGHT = 4

# Overall-status thresholds on the 0-100 weighted score.
COMPLIANT_THRESHOLD = 85.0
PARTIAL_THRESHOLD = 60.0


@dataclass
class EvaluatedControl:
    spec: ControlSpec
    status: str
    is_critical_gap: bool
    evidence: str
    remediation: str


def resolve_scope(framework: str) -> tuple[ControlSpec, ...]:
    """Controls in scope for an assessment. 'ALL' -> the whole library."""
    if framework == "ALL":
        return all_controls()
    if framework not in ALL_FRAMEWORKS:
        raise ValueError(f"unknown framework: {framework!r}")
    return controls_for_framework(framework)


def _generate_status(vendor_id: str, spec: ControlSpec) -> str:
    """Deterministic per (vendor, control) status draw.

    Higher-weight (more material) controls are made slightly more likely to
    surface as gaps so that assessments have realistic, actionable critical
    findings rather than an even wash."""
    rng = seeded_random("compliance-status", vendor_id, spec.control_id)
    roll = rng.random()

    # Weight nudges the gap/partial mass up a little for material controls.
    gap_bias = (spec.weight - 3) * 0.02  # weight 5 -> +0.04, weight 1 -> -0.04
    p_met = 0.60 - gap_bias
    p_partial = 0.22
    p_gap = 0.13 + gap_bias
    # remainder (~0.05) -> not_applicable

    if roll < p_met:
        return MET
    if roll < p_met + p_partial:
        return PARTIAL
    if roll < p_met + p_partial + p_gap:
        return GAP
    return NOT_APPLICABLE


def _evidence_for(status: str, spec: ControlSpec) -> tuple[str, str]:
    """(evidence, remediation) narrative for a control result."""
    if status == MET:
        return (
            f"Evidence reviewed: control satisfied for {spec.reference}.",
            "",
        )
    if status == PARTIAL:
        return (
            f"Partial evidence for {spec.reference}: control implemented but "
            f"gaps in coverage/consistency remain.",
            f"Strengthen and fully operationalise '{spec.title}' to close residual gaps.",
        )
    if status == GAP:
        return (
            f"No adequate evidence for {spec.reference}: control not "
            f"demonstrably implemented.",
            f"Implement '{spec.title}' and provide evidence; "
            + ("PRIORITY -- material control." if spec.weight >= CRITICAL_GAP_WEIGHT else "schedule remediation."),
        )
    return (f"{spec.reference} assessed not applicable to this vendor's scope.", "")


def evaluate_controls(
    vendor_id: str,
    framework: str,
    overrides: dict[str, dict] | None = None,
) -> list[EvaluatedControl]:
    overrides = overrides or {}
    results: list[EvaluatedControl] = []
    for spec in resolve_scope(framework):
        override = overrides.get(spec.control_id)
        if override is not None:
            status = override["status"]
            evidence = override.get("evidence") or _evidence_for(status, spec)[0]
            remediation = override.get("remediation") or _evidence_for(status, spec)[1]
        else:
            status = _generate_status(vendor_id, spec)
            evidence, remediation = _evidence_for(status, spec)

        is_critical_gap = status == GAP and spec.weight >= CRITICAL_GAP_WEIGHT
        results.append(
            EvaluatedControl(
                spec=spec,
                status=status,
                is_critical_gap=is_critical_gap,
                evidence=evidence,
                remediation=remediation,
            )
        )
    return results


# --- Scoring ---
_STATUS_CREDIT = {MET: 1.0, PARTIAL: 0.5, GAP: 0.0}


def compliance_score(results: list[EvaluatedControl]) -> float:
    """Weighted 0-100 score. not_applicable controls are excluded from the
    denominator (you don't get penalised for a control that doesn't apply)."""
    applicable = [r for r in results if r.status != NOT_APPLICABLE]
    if not applicable:
        return 100.0
    earned = sum(_STATUS_CREDIT[r.status] * r.spec.weight for r in applicable)
    possible = sum(r.spec.weight for r in applicable)
    return round(100.0 * earned / possible, 2)


def status_from_score(score: float) -> str:
    if score >= COMPLIANT_THRESHOLD:
        return "Compliant"
    if score >= PARTIAL_THRESHOLD:
        return "Partially Compliant"
    return "Non-Compliant"


def framework_score_breakdown(results: list[EvaluatedControl]) -> dict[str, float]:
    """Per-framework weighted score (for an 'ALL' assessment roll-up)."""
    by_fw: dict[str, list[EvaluatedControl]] = {}
    for r in results:
        by_fw.setdefault(r.spec.framework, []).append(r)
    return {fw: compliance_score(rs) for fw, rs in by_fw.items()}


def domain_breakdown(results: list[EvaluatedControl]) -> list[dict]:
    """Gap analysis rolled up by (framework, domain)."""
    buckets: dict[tuple[str, str], list[EvaluatedControl]] = {}
    for r in results:
        buckets.setdefault((r.spec.framework, r.spec.domain), []).append(r)

    rows: list[dict] = []
    for (framework, domain), rs in buckets.items():
        counts = {MET: 0, PARTIAL: 0, GAP: 0, NOT_APPLICABLE: 0}
        for r in rs:
            counts[r.status] += 1
        rows.append(
            {
                "framework": framework,
                "domain": domain,
                "total": len(rs),
                "met": counts[MET],
                "partial": counts[PARTIAL],
                "gap": counts[GAP],
                "not_applicable": counts[NOT_APPLICABLE],
                "score": compliance_score(rs),
            }
        )
    # Worst-scoring domains first -- that's where remediation attention goes.
    rows.sort(key=lambda x: (x["score"], -x["gap"]))
    return rows


def rank_gaps(results: list[EvaluatedControl]) -> list[EvaluatedControl]:
    """Failing/weak controls, critical gaps first, then by descending weight."""
    gaps = [r for r in results if r.status in (GAP, PARTIAL)]
    gaps.sort(key=lambda r: (not r.is_critical_gap, r.status != GAP, -r.spec.weight))
    return gaps


def summarise(results: list[EvaluatedControl]) -> dict:
    counts = {MET: 0, PARTIAL: 0, GAP: 0, NOT_APPLICABLE: 0}
    for r in results:
        counts[r.status] += 1
    critical = sum(1 for r in results if r.is_critical_gap)
    return {
        "total_controls": len(results),
        "compliant_count": counts[MET],
        "partial_count": counts[PARTIAL],
        "gap_count": counts[GAP],
        "not_applicable_count": counts[NOT_APPLICABLE],
        "critical_gap_count": critical,
    }
