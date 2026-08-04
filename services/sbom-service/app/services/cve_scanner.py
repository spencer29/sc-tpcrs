"""CVE cross-referencing + SSVC prioritisation (Module 3, pipeline stage ii).

Reuses the shared mock NVD + CISA KEV adapters (exactly as risk-service's
vulnerability category does) so the planted left-pad@1.0.0 -> CVE-2024-99999
KEV finding fires reliably for Demo Scenario 1. Each NVD CVE for a component is
enriched with its KEV status and assigned an SSVC deployer-tree priority.

SSVC (Stakeholder-Specific Vulnerability Categorization) is CISA's replacement
for "patch by CVSS number". We implement the simplified deployer decision tree:

    Exploitation  | Automatable | Impact        -> Priority
    -------------------------------------------------------
    active (KEV)   |     yes     |  high          -> Act
    active (KEV)   |     yes     |  low           -> Attend
    active (KEV)   |     no      |  any           -> Attend
    none           |     yes     |  high          -> Track*
    none           |     *       |  *             -> Track

'high impact' is approximated by CVSS >= 7.0; 'automatable' by a network
attack vector with low complexity (mock vectors carry AV:N/AC:L). This is a
faithful, documented simplification of the full tree.
"""

from __future__ import annotations

from dataclasses import dataclass

from sc_tpcrs_common.adapters import kev_adapter, nvd_adapter  # noqa: F401 - register adapters
from sc_tpcrs_common.adapters.registry import get_adapter

from .parsers import NormalisedComponent


@dataclass
class ScannedVulnerability:
    cve_id: str
    description: str | None
    cvss_score: float | None
    cvss_vector: str | None
    severity: str
    kev_flag: bool
    known_ransomware: bool
    ssvc_priority: str


@dataclass
class ScannedComponent:
    component: NormalisedComponent
    vulnerabilities: list[ScannedVulnerability]


def severity_band(cvss: float | None) -> str:
    if cvss is None:
        return "None"
    if cvss >= 9.0:
        return "Critical"
    if cvss >= 7.0:
        return "High"
    if cvss >= 4.0:
        return "Medium"
    if cvss > 0.0:
        return "Low"
    return "None"


def _automatable(cvss_vector: str | None) -> bool:
    if not cvss_vector:
        return False
    return "AV:N" in cvss_vector and "AC:L" in cvss_vector


def ssvc_priority(*, cvss: float | None, cvss_vector: str | None, is_kev: bool) -> str:
    high_impact = (cvss or 0.0) >= 7.0
    automatable = _automatable(cvss_vector)
    if is_kev:  # KEV listing == active exploitation
        if automatable and high_impact:
            return "Act"
        return "Attend"
    if automatable and high_impact:
        return "Track*"
    return "Track"


async def scan_component(component: NormalisedComponent) -> ScannedComponent:
    nvd = get_adapter("nvd")
    kev = get_adapter("kev")

    nvd_result = await nvd.fetch(
        component_name=component.name,
        version=component.version,
        ecosystem=component.ecosystem,
    )

    vulns: list[ScannedVulnerability] = []
    for cve in nvd_result.data:
        kev_result = await kev.fetch(
            cve_id=cve["cve_id"],
            component_name=component.name,
            version=component.version,
        )
        is_kev = kev_result.data is not None
        known_ransomware = bool(is_kev and kev_result.data.get("known_ransomware_use"))
        cvss = float(cve["cvss_score"]) if cve.get("cvss_score") is not None else None
        vector = cve.get("cvss_vector")
        vulns.append(
            ScannedVulnerability(
                cve_id=cve["cve_id"],
                description=cve.get("description"),
                cvss_score=cvss,
                cvss_vector=vector,
                severity=severity_band(cvss),
                kev_flag=is_kev,
                known_ransomware=known_ransomware,
                ssvc_priority=ssvc_priority(cvss=cvss, cvss_vector=vector, is_kev=is_kev),
            )
        )

    return ScannedComponent(component=component, vulnerabilities=vulns)


async def scan_components(components: list[NormalisedComponent]) -> list[ScannedComponent]:
    """Sequential cross-reference. The mock adapters are pure-CPU and
    deterministic, so a 1,000-component SBOM completes well within the <5s SLA
    without needing the added complexity of bounded concurrency here."""
    return [await scan_component(c) for c in components]
