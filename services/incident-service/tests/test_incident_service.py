from __future__ import annotations

import uuid

import pytest
from app.services import incident_service

VENDOR = str(uuid.uuid4())


async def test_create_incident_assigns_sequential_reference(db_session):
    a = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="First", description="",
        severity="Medium", category="MANUAL",
    )
    b = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="Second", description="",
        severity="Medium", category="MANUAL",
    )
    assert a.reference == "INC-000001"
    assert b.reference == "INC-000002"


async def test_create_high_severity_flags_cbn(db_session):
    inc = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="Breach", description="",
        severity="High", category="SECURITY_POSTURE",
    )
    assert inc.requires_cbn_notification is True
    # High but no personal data -> no NDPA.
    assert inc.requires_ndpa_notification is False


async def test_create_medium_severity_no_cbn(db_session):
    inc = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="Minor", description="",
        severity="Medium", category="MANUAL",
    )
    assert inc.requires_cbn_notification is False


async def test_personal_data_flags_ndpa(db_session):
    inc = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="PII", description="",
        severity="Medium", category="MANUAL", personal_data_involved=True,
    )
    assert inc.requires_ndpa_notification is True


async def test_data_breach_category_implies_ndpa(db_session):
    inc = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="Leak", description="",
        severity="High", category="DATA_BREACH",
    )
    assert inc.requires_ndpa_notification is True


async def test_create_drafts_required_notifications(db_session):
    inc = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="Both", description="",
        severity="Critical", category="DATA_BREACH", personal_data_involved=True,
    )
    await db_session.flush()
    notes = await incident_service.get_notifications(db_session, inc.id)
    regulators = {n.regulator for n in notes}
    assert regulators == {"CBN", "NDPC"}


async def test_create_seeds_timeline(db_session):
    inc = await incident_service.create_incident(
        db_session, actor="analyst", vendor_id=VENDOR, title="T", description="",
        severity="Low", category="MANUAL",
    )
    await db_session.flush()
    timeline = await incident_service.get_timeline(db_session, inc.id)
    assert any(t.event_type == "created" for t in timeline)


async def test_transition_status_happy_path(db_session):
    inc = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="T", description="",
        severity="High", category="MANUAL",
    )
    await incident_service.transition_status(db_session, inc, target="investigating", actor="u")
    assert inc.status == "investigating"
    await incident_service.transition_status(db_session, inc, target="contained", actor="u")
    assert inc.status == "contained"
    assert inc.contained_at is not None


async def test_transition_to_closed_stamps_resolved(db_session):
    inc = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="T", description="",
        severity="High", category="MANUAL",
    )
    await incident_service.transition_status(db_session, inc, target="closed", actor="u")
    assert inc.status == "closed"
    assert inc.closed_at is not None
    assert inc.resolved_at is not None  # closing without an explicit resolve stamps both


async def test_illegal_transition_raises(db_session):
    inc = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="T", description="",
        severity="High", category="MANUAL",
    )
    await incident_service.transition_status(db_session, inc, target="closed", actor="u")
    with pytest.raises(ValueError):
        await incident_service.transition_status(db_session, inc, target="investigating", actor="u")


async def test_same_status_transition_raises(db_session):
    inc = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="T", description="",
        severity="High", category="MANUAL",
    )
    with pytest.raises(ValueError):
        await incident_service.transition_status(db_session, inc, target="open", actor="u")


async def test_find_by_source_ref_dedup(db_session):
    inc = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="T", description="",
        severity="High", category="SECURITY_POSTURE", source="monitoring.alerts",
        source_ref="alert-123",
    )
    await db_session.flush()
    found = await incident_service.find_by_source_ref(db_session, "alert-123")
    assert found is not None and found.id == inc.id
    assert await incident_service.find_by_source_ref(db_session, "missing") is None


async def test_assign_incident_records_timeline(db_session):
    inc = await incident_service.create_incident(
        db_session, actor="u", vendor_id=VENDOR, title="T", description="",
        severity="Low", category="MANUAL",
    )
    await incident_service.assign_incident(db_session, inc, assignee="ciso@demo", actor="u")
    await db_session.flush()
    timeline = await incident_service.get_timeline(db_session, inc.id)
    assert inc.assignee == "ciso@demo"
    assert any(t.event_type == "assignment" for t in timeline)
