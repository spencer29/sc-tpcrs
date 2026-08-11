"""Posture collection + exposure-index math (pure/deterministic)."""

from __future__ import annotations

import uuid

import pytest

from app.services import posture


def test_exposure_index_healthy_vendor_is_low():
    # Healthy posture, no IOC/abuse -> small exposure (only 40% of the 0.6
    # posture weight * 10 gap = 6.0).
    ei = posture.compute_exposure_index(posture_score=90.0, ioc_match_count=0, abuse_report_count=0)
    assert ei == round((100.0 - 90.0) * 0.6, 2)
    assert 0.0 <= ei <= 100.0


def test_exposure_index_worst_case_clamped_to_100():
    ei = posture.compute_exposure_index(posture_score=0.0, ioc_match_count=99, abuse_report_count=99)
    # 100*0.6 + 100*0.25 + 100*0.15 = 100.0
    assert ei == 100.0


def test_exposure_index_ioc_and_abuse_add_penalty():
    base = posture.compute_exposure_index(80.0, 0, 0)
    with_ioc = posture.compute_exposure_index(80.0, 4, 0)
    with_abuse = posture.compute_exposure_index(80.0, 0, 5)
    assert with_ioc > base
    assert with_abuse > base
    # IOC weight (0.25) > abuse weight (0.15): a capped IOC adds more than a
    # capped abuse count.
    assert (with_ioc - base) > (with_abuse - base)


def test_exposure_index_counts_are_capped():
    # At/above the caps the penalty saturates.
    at_cap = posture.compute_exposure_index(80.0, posture._IOC_CAP, posture._ABUSE_CAP)
    above_cap = posture.compute_exposure_index(80.0, posture._IOC_CAP * 10, posture._ABUSE_CAP * 10)
    assert at_cap == above_cap


async def test_collect_posture_is_deterministic():
    vid = str(uuid.uuid4())
    a = await posture.collect_posture(vid)
    b = await posture.collect_posture(vid)
    assert a == b
    assert 0.0 <= a.posture_score <= 100.0
    assert 0.0 <= a.exposure_index <= 100.0
    assert isinstance(a.open_services, list)


async def test_drift_probe_changes_the_reading():
    vid = str(uuid.uuid4())
    baseline = await posture.collect_posture(vid, drift_probe=0)
    perturbed = await posture.collect_posture(vid, drift_probe=1)
    # A non-zero probe reseeds the adapters, so at least one signal differs.
    assert (
        perturbed.posture_score != baseline.posture_score
        or perturbed.open_services != baseline.open_services
        or perturbed.ioc_match_count != baseline.ioc_match_count
    )
    # ...but is still deterministic for the same probe.
    assert perturbed == await posture.collect_posture(vid, drift_probe=1)


def test_rotating_probe_mostly_stable_and_in_range():
    vid = str(uuid.uuid4())
    probes = [posture.rotating_probe(vid, epoch) for epoch in range(200)]
    assert all(p in (0, 1, 2) for p in probes)
    # ~70% should land on the stable baseline; assert a loose majority so the
    # test isn't flaky against the exact distribution.
    zero_fraction = probes.count(0) / len(probes)
    assert zero_fraction > 0.5


def test_rotating_probe_is_deterministic():
    vid = str(uuid.uuid4())
    assert posture.rotating_probe(vid, 7) == posture.rotating_probe(vid, 7)
