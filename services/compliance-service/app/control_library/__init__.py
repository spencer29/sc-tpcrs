"""SC-TPCRS compliance control library.

The blueprint's Module 5 calls for a control library of roughly 312 controls
spanning the frameworks a Nigerian fintech's third parties are typically held
to. This package is that library, authored against the *real* published
control sets:

  * ISO/IEC 27001:2022 Annex A  -- all 93 controls, real reference IDs/titles.
  * PCI DSS v4.0                -- 12 principal requirements + their defined
                                   sub-requirements.
  * SOC 2 (2017 TSC, rev. 2022) -- Common Criteria CC1-CC9 plus the
                                   Availability / Confidentiality / Processing
                                   Integrity / Privacy categories.
  * NDPR 2019 / NDPA 2023       -- Nigeria Data Protection Regulation & Act.
  * CBN Risk-Based Cybersecurity Framework (banks, OFIs & PSPs).

Each framework module exposes a ``CONTROLS`` list of :class:`ControlSpec`.
The library is data, not behaviour: the assessment/gap-analysis engine
(``app/services``) reads it, so swapping in a richer control set later is a
localised change with no engine impact.

Deviation (documented in the README): control *text* is captured at
title/objective granularity rather than reproducing each standard's full
normative prose (which is copyrighted). That is sufficient for gap analysis,
scoring, and regulator-ready reporting; the reference IDs let an auditor map
every gap back to the source clause.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache


@dataclass(frozen=True)
class ControlSpec:
    """A single, framework-scoped control.

    ``control_id`` is globally unique across the library (framework prefix +
    native reference). ``reference`` is the native clause id an auditor knows
    it by. ``weight`` (1-5) drives the weighted compliance score -- higher =
    more material to third-party cyber risk.
    """

    control_id: str
    framework: str
    reference: str
    domain: str
    title: str
    objective: str
    weight: int = 3
    tags: tuple[str, ...] = field(default_factory=tuple)


# Canonical framework labels (used as API filter values and report headings).
FRAMEWORK_ISO_27001 = "ISO 27001:2022"
FRAMEWORK_PCI_DSS = "PCI DSS v4.0"
FRAMEWORK_SOC2 = "SOC 2"
FRAMEWORK_NDPR = "NDPR/NDPA"
FRAMEWORK_CBN = "CBN Cybersecurity Framework"

ALL_FRAMEWORKS = (
    FRAMEWORK_ISO_27001,
    FRAMEWORK_PCI_DSS,
    FRAMEWORK_SOC2,
    FRAMEWORK_NDPR,
    FRAMEWORK_CBN,
)


@lru_cache(maxsize=1)
def all_controls() -> tuple[ControlSpec, ...]:
    """The full, immutable control library, assembled once."""
    from . import cbn, iso27001, ndpr, pci_dss, soc2

    controls: list[ControlSpec] = []
    for module in (iso27001, pci_dss, soc2, ndpr, cbn):
        controls.extend(module.CONTROLS)

    seen: set[str] = set()
    for c in controls:
        if c.control_id in seen:
            raise ValueError(f"duplicate control_id in library: {c.control_id}")
        seen.add(c.control_id)
    return tuple(controls)


@lru_cache(maxsize=1)
def controls_by_id() -> dict[str, ControlSpec]:
    return {c.control_id: c for c in all_controls()}


def controls_for_framework(framework: str) -> tuple[ControlSpec, ...]:
    return tuple(c for c in all_controls() if c.framework == framework)


def framework_control_counts() -> dict[str, int]:
    counts: dict[str, int] = {fw: 0 for fw in ALL_FRAMEWORKS}
    for c in all_controls():
        counts[c.framework] = counts.get(c.framework, 0) + 1
    return counts


def library_size() -> int:
    return len(all_controls())
