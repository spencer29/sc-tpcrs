"""Posture collection + exposure-index computation.

Gathers a vendor's current external security posture from the shared mock
adapters (Shodan / MISP / AbuseIPDB -- the same adapters risk-service uses for
its external-posture, threat-intel, and breach-history VRS categories) and
folds them into a single 0-100 `exposure_index` (higher = worse). Because the
adapters are deterministic per vendor (SHA256-seeded), a vendor's posture is
stable across sweeps *until its inputs change* -- which is exactly what makes
drift meaningful and demoable (see collect_posture's `drift_probe`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sc_tpcrs_common.adapters import abuseipdb_adapter, misp_adapter, shodan_adapter  # noqa: F401 - register
from sc_tpcrs_common.adapters.base import seeded_random
from sc_tpcrs_common.adapters.registry import get_adapter

# Exposure-index weights (sum ~1.0). Posture is the dominant signal; IOC
# matches and abuse reports add penalty on top.
_W_POSTURE = 0.6
_W_IOC = 0.25
_W_ABUSE = 0.15

# Normalisation caps: counts at/above these map to the full penalty.
_IOC_CAP = 4
_ABUSE_CAP = 5


@dataclass(frozen=True)
class PostureReading:
    posture_score: float          # 0-100, higher = healthier (Shodan mock)
    open_services: list[str]
    ioc_match_count: int
    abuse_report_count: int
    exposure_index: float         # 0-100, higher = worse
    raw: dict[str, Any]


def compute_exposure_index(posture_score: float, ioc_match_count: int, abuse_report_count: int) -> float:
    """Fold the raw signals into a single 0-100 exposure index (higher = worse).

    - Posture contributes its inverse (100 - posture) so a healthy 90 posture
      adds little exposure.
    - IOC / abuse counts are normalised against their caps and scaled to 100.
    """
    posture_component = (100.0 - posture_score) * _W_POSTURE
    ioc_component = min(ioc_match_count / _IOC_CAP, 1.0) * 100.0 * _W_IOC
    abuse_component = min(abuse_report_count / _ABUSE_CAP, 1.0) * 100.0 * _W_ABUSE
    return round(max(0.0, min(100.0, posture_component + ioc_component + abuse_component)), 2)


async def collect_posture(vendor_id: str, *, drift_probe: int = 0) -> PostureReading:
    """Collect a vendor's current posture from the mock adapters.

    `drift_probe` lets a caller deliberately perturb the deterministic seed to
    simulate posture change over time (used by the "sweep now" demo path and
    tests). drift_probe=0 is the vendor's stable baseline; a non-zero value
    yields a different-but-still-deterministic reading, so drift alerts can be
    demonstrated on demand without waiting for real-world change.
    """
    shodan = get_adapter("shodan")
    misp = get_adapter("misp")
    abuse = get_adapter("abuseipdb")

    probe_id = vendor_id if drift_probe == 0 else f"{vendor_id}#probe{drift_probe}"

    shodan_res = await shodan.fetch(vendor_id=probe_id)
    misp_res = await misp.fetch(vendor_id=probe_id)
    abuse_res = await abuse.fetch(vendor_id=probe_id)

    posture_score = float(shodan_res.data["posture_score"])
    open_services = list(shodan_res.data.get("open_services", []))
    ioc = int(misp_res.data["ioc_match_count"])
    abuse_reports = int(abuse_res.data["report_count_24mo"])

    exposure = compute_exposure_index(posture_score, ioc, abuse_reports)

    return PostureReading(
        posture_score=posture_score,
        open_services=open_services,
        ioc_match_count=ioc,
        abuse_report_count=abuse_reports,
        exposure_index=exposure,
        raw={
            "shodan": shodan_res.data,
            "misp": misp_res.data,
            "abuseipdb": abuse_res.data,
            "drift_probe": drift_probe,
        },
    )


def rotating_probe(vendor_id: str, sweep_epoch: int) -> int:
    """Deterministic per-(vendor, epoch) drift probe in {0,1,2}.

    A sweep passes an incrementing epoch; this maps most sweeps to the stable
    baseline (0) but occasionally to a perturbed reading, so a running stack
    naturally produces the odd drift alert over time rather than being static.
    """
    rng = seeded_random("monitoring-probe", vendor_id, sweep_epoch)
    roll = rng.random()
    if roll < 0.7:
        return 0
    return rng.randint(1, 2)
