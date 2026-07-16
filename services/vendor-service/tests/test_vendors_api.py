from __future__ import annotations

from .conftest import auth_headers

VENDOR_PAYLOAD = {
    "name": "Acme Payment Rails",
    "legal_entity_name": "Acme Payment Rails Ltd",
    "country": "NG",
    "industry": "Payment_Gateway",
    "contact_name": "Jane Doe",
    "contact_email": "jane@acme.example",
    "data_access_scope": "Critical",
    "service_criticality": "High",
    "integration_depth": "Medium",
}


async def test_create_vendor_computes_tier(client):
    resp = await client.post("/vendors", json=VENDOR_PAYLOAD, headers=auth_headers())
    assert resp.status_code == 201
    body = resp.json()
    assert body["overall_tier"] == "Critical"  # max(Critical, High, Medium)
    assert body["onboarding_state"] == "INITIATED"


async def test_create_vendor_requires_permitted_role(client):
    resp = await client.post("/vendors", json=VENDOR_PAYLOAD, headers=auth_headers(role="viewer_that_doesnt_exist"))
    assert resp.status_code == 403


async def test_create_vendor_requires_auth(client):
    resp = await client.post("/vendors", json=VENDOR_PAYLOAD)
    assert resp.status_code == 401


async def test_list_and_get_vendor(client):
    create_resp = await client.post("/vendors", json=VENDOR_PAYLOAD, headers=auth_headers())
    vendor_id = create_resp.json()["id"]

    list_resp = await client.get("/vendors", headers=auth_headers(role="analyst"))
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    get_resp = await client.get(f"/vendors/{vendor_id}", headers=auth_headers(role="analyst"))
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == vendor_id


async def test_update_vendor_recomputes_tier(client):
    create_resp = await client.post("/vendors", json=VENDOR_PAYLOAD, headers=auth_headers())
    vendor_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/vendors/{vendor_id}",
        json={"data_access_scope": "Low", "service_criticality": "Low", "integration_depth": "Low"},
        headers=auth_headers(),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["overall_tier"] == "Low"


async def test_transition_follows_state_machine(client):
    create_resp = await client.post("/vendors", json=VENDOR_PAYLOAD, headers=auth_headers())
    vendor_id = create_resp.json()["id"]

    # Skipping straight to ONBOARDED is illegal.
    bad_resp = await client.post(
        f"/vendors/{vendor_id}/transition", json={"target_state": "ONBOARDED"}, headers=auth_headers()
    )
    assert bad_resp.status_code == 422

    good_resp = await client.post(
        f"/vendors/{vendor_id}/transition", json={"target_state": "QUESTIONNAIRE_SENT"}, headers=auth_headers()
    )
    assert good_resp.status_code == 200
    assert good_resp.json()["onboarding_state"] == "QUESTIONNAIRE_SENT"


async def test_full_questionnaire_lifecycle_completes_vendor_to_questionnaire_completed(client):
    create_resp = await client.post("/vendors", json=VENDOR_PAYLOAD, headers=auth_headers())
    vendor_id = create_resp.json()["id"]

    gen_resp = await client.post(f"/vendors/{vendor_id}/questionnaire", headers=auth_headers())
    assert gen_resp.status_code == 201
    questionnaire = gen_resp.json()
    assert questionnaire["tier"] == "Critical"
    assert len(questionnaire["questions"]) == 36  # Critical tier -> full 36-question bank
    assert questionnaire["status"] == "SENT"

    vendor_after_send = await client.get(f"/vendors/{vendor_id}", headers=auth_headers())
    assert vendor_after_send.json()["onboarding_state"] == "QUESTIONNAIRE_SENT"

    # Answer every question with YES -> average score should be 100.
    responses = [{"question_code": q["code"], "answer": "YES"} for q in questionnaire["questions"]]
    update_resp = await client.put(
        f"/vendors/{vendor_id}/questionnaire/responses", json={"responses": responses}, headers=auth_headers()
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "COMPLETED"

    vendor_after_complete = await client.get(f"/vendors/{vendor_id}", headers=auth_headers())
    assert vendor_after_complete.json()["onboarding_state"] == "QUESTIONNAIRE_COMPLETED"

    score_resp = await client.get(f"/vendors/{vendor_id}/questionnaire/score", headers=auth_headers())
    assert score_resp.status_code == 200
    assert score_resp.json()["score"] == 100.0


async def test_partial_questionnaire_answers_do_not_complete_it(client):
    create_resp = await client.post("/vendors", json=VENDOR_PAYLOAD, headers=auth_headers())
    vendor_id = create_resp.json()["id"]
    gen_resp = await client.post(f"/vendors/{vendor_id}/questionnaire", headers=auth_headers())
    questions = gen_resp.json()["questions"]

    partial = [{"question_code": questions[0]["code"], "answer": "NO"}]
    update_resp = await client.put(
        f"/vendors/{vendor_id}/questionnaire/responses", json={"responses": partial}, headers=auth_headers()
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "IN_PROGRESS"

    vendor_after = await client.get(f"/vendors/{vendor_id}", headers=auth_headers())
    assert vendor_after.json()["onboarding_state"] == "QUESTIONNAIRE_SENT"


async def test_document_upload_and_list(client):
    create_resp = await client.post("/vendors", json=VENDOR_PAYLOAD, headers=auth_headers())
    vendor_id = create_resp.json()["id"]

    files = {"file": ("iso27001.pdf", b"%PDF-1.4 fake content", "application/pdf")}
    upload_resp = await client.post(
        f"/vendors/{vendor_id}/documents",
        data={"document_type": "ISO27001_CERT"},
        files=files,
        headers=auth_headers(),
    )
    assert upload_resp.status_code == 201
    assert upload_resp.json()["document_type"] == "ISO27001_CERT"

    list_resp = await client.get(f"/vendors/{vendor_id}/documents", headers=auth_headers(role="analyst"))
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


async def test_get_unknown_vendor_returns_404(client):
    resp = await client.get(
        "/vendors/00000000-0000-0000-0000-000000000000", headers=auth_headers(role="analyst")
    )
    assert resp.status_code == 404
