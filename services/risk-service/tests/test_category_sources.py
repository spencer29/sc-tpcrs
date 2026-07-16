from __future__ import annotations

import uuid

import respx
from httpx import Response

from app.config import settings
from app.models import VendorTechStack
from app.services.category_sources.breach_history_source import get_breach_history_score
from app.services.category_sources.compliance_source import get_compliance_score
from app.services.category_sources.external_posture_source import get_external_posture_score
from app.services.category_sources.questionnaire_source import get_questionnaire_score
from app.services.category_sources.threat_intel_source import get_threat_intel_score
from app.services.category_sources.vulnerability_source import get_vulnerability_score


async def test_questionnaire_score_defaults_to_zero_when_vendor_service_unreachable():
    score = await get_questionnaire_score(str(uuid.uuid4()))
    assert score == 0.0


@respx.mock
async def test_questionnaire_score_parses_successful_response():
    vendor_id = str(uuid.uuid4())
    respx.get(f"{settings.vendor_service_url}/vendors/{vendor_id}/questionnaire/score").mock(
        return_value=Response(200, json={"score": 82.5})
    )
    score = await get_questionnaire_score(vendor_id)
    assert score == 82.5


@respx.mock
async def test_questionnaire_score_defaults_to_zero_on_404():
    vendor_id = str(uuid.uuid4())
    respx.get(f"{settings.vendor_service_url}/vendors/{vendor_id}/questionnaire/score").mock(
        return_value=Response(404)
    )
    score = await get_questionnaire_score(vendor_id)
    assert score == 0.0


async def test_compliance_score_defaults_to_zero_when_vendor_service_unreachable():
    score = await get_compliance_score(str(uuid.uuid4()))
    assert score == 0.0


@respx.mock
async def test_compliance_score_weights_certifications():
    vendor_id = str(uuid.uuid4())
    respx.get(f"{settings.vendor_service_url}/vendors/{vendor_id}/documents").mock(
        return_value=Response(
            200,
            json=[
                {"document_type": "ISO27001_CERT"},
                {"document_type": "SOC2_REPORT"},
            ],
        )
    )
    score = await get_compliance_score(vendor_id)
    assert score == 70.0  # 40 (ISO) + 30 (SOC2)


@respx.mock
async def test_compliance_score_capped_at_100():
    vendor_id = str(uuid.uuid4())
    respx.get(f"{settings.vendor_service_url}/vendors/{vendor_id}/documents").mock(
        return_value=Response(
            200,
            json=[
                {"document_type": "ISO27001_CERT"},
                {"document_type": "SOC2_REPORT"},
                {"document_type": "PCI_DSS_AOC"},
                {"document_type": "OTHER"},
            ],
        )
    )
    score = await get_compliance_score(vendor_id)
    assert score == 100.0  # 40+30+20+10 = 100, capped


async def test_external_posture_score_is_deterministic_and_in_range():
    vendor_id = str(uuid.uuid4())
    score_a = await get_external_posture_score(vendor_id)
    score_b = await get_external_posture_score(vendor_id)
    assert score_a == score_b
    assert 0.0 <= score_a <= 100.0


async def test_breach_history_and_threat_intel_scores_in_range():
    vendor_id = str(uuid.uuid4())
    breach_score = await get_breach_history_score(vendor_id)
    threat_score = await get_threat_intel_score(vendor_id)
    assert 0.0 <= breach_score <= 100.0
    assert 0.0 <= threat_score <= 100.0


async def test_vulnerability_score_with_no_components_is_perfect(db_session):
    vendor_id = str(uuid.uuid4())
    score = await get_vulnerability_score(db_session, vendor_id)
    assert score == 100.0


async def test_vulnerability_score_with_planted_critical_kev_component(db_session):
    vendor_id = str(uuid.uuid4())
    db_session.add(
        VendorTechStack(vendor_id=vendor_id, component_name="left-pad", component_version="1.0.0", ecosystem="npm")
    )
    await db_session.flush()

    score = await get_vulnerability_score(db_session, vendor_id)
    # Planted CVE is CVSS 9.8 + KEV-listed -> penalty 60 -> 100 - 60 = 40.
    assert score == 40.0
