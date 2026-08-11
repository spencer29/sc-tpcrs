"""Consumer dispatch: event_type -> topic hint derivation.

The shared consumer routes every topic to one handler, so handle_event must
recover the originating topic from the event_type prefix. We patch the DB-touching
`_handle_event` to capture the hint (its SessionLocal points at a different engine
than the test StaticPool, so we don't exercise it here -- upsert persistence is
covered in test_alert_engine)."""

from __future__ import annotations

import uuid

import pytest
from sc_tpcrs_common.kafka_topics import (
    COMPLIANCE_ASSESSMENT_EVENTS,
    CVE_ALERTS,
    RISK_ANOMALY_ALERTS,
)

from app.services import events


@pytest.fixture
def capture_hint(monkeypatch):
    seen = {}

    async def _fake(topic_hint, event):
        seen["topic"] = topic_hint
        seen["event"] = event

    monkeypatch.setattr(events, "_handle_event", _fake)
    return seen


async def test_cve_event_routes_to_cve_topic(capture_hint):
    await events.handle_event({"event_type": "cve.critical", "payload": {"vendor_id": str(uuid.uuid4())}})
    assert capture_hint["topic"] == CVE_ALERTS


async def test_compliance_event_routes_to_compliance_topic(capture_hint):
    await events.handle_event({"event_type": "compliance.assessed", "payload": {}})
    assert capture_hint["topic"] == COMPLIANCE_ASSESSMENT_EVENTS


async def test_risk_anomaly_event_routes_to_risk_topic(capture_hint):
    await events.handle_event({"event_type": "risk.anomaly.detected", "payload": {}})
    assert capture_hint["topic"] == RISK_ANOMALY_ALERTS


async def test_unknown_event_falls_back_to_event_type(capture_hint):
    await events.handle_event({"event_type": "something.else", "payload": {}})
    assert capture_hint["topic"] == "something.else"


def test_consumed_topics_are_the_three_upstream_modules():
    assert set(events._CONSUMED_TOPICS) == {CVE_ALERTS, COMPLIANCE_ASSESSMENT_EVENTS, RISK_ANOMALY_ALERTS}
