from __future__ import annotations

from app.services.cve_scanner import scan_component, severity_band, ssvc_priority
from app.services.purl_normalizer import normalise


def test_severity_bands():
    assert severity_band(9.8) == "Critical"
    assert severity_band(7.5) == "High"
    assert severity_band(5.0) == "Medium"
    assert severity_band(2.0) == "Low"
    assert severity_band(0.0) == "None"
    assert severity_band(None) == "None"


def test_ssvc_kev_automatable_high_is_act():
    p = ssvc_priority(cvss=9.8, cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", is_kev=True)
    assert p == "Act"


def test_ssvc_kev_not_automatable_is_attend():
    p = ssvc_priority(cvss=9.0, cvss_vector="CVSS:3.1/AV:L/AC:H", is_kev=True)
    assert p == "Attend"


def test_ssvc_non_kev_automatable_high_is_track_star():
    p = ssvc_priority(cvss=8.0, cvss_vector="CVSS:3.1/AV:N/AC:L", is_kev=False)
    assert p == "Track*"


def test_ssvc_non_kev_low_is_track():
    p = ssvc_priority(cvss=3.0, cvss_vector="CVSS:3.1/AV:N/AC:L", is_kev=False)
    assert p == "Track"


async def test_planted_left_pad_resolves_to_critical_kev_cve():
    # Demo Scenario 1 backbone: the planted component must deterministically
    # resolve to the CRITICAL, KEV-listed CVE-2024-99999 with SSVC 'Act'.
    comp = normalise(name="left-pad", version="1.0.0", ecosystem="npm", purl="pkg:npm/left-pad@1.0.0")
    scanned = await scan_component(comp)
    cve_ids = {v.cve_id for v in scanned.vulnerabilities}
    assert "CVE-2024-99999" in cve_ids
    planted = next(v for v in scanned.vulnerabilities if v.cve_id == "CVE-2024-99999")
    assert planted.severity == "Critical"
    assert planted.kev_flag is True
    assert planted.ssvc_priority == "Act"
