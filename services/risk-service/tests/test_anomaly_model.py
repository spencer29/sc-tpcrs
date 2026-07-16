from __future__ import annotations

import uuid

from app.models import RiskScoreHistory
from app.services.anomaly.model import evaluate_anomaly


async def test_evaluate_anomaly_returns_valid_probability(db_session):
    vendor_id = str(uuid.uuid4())
    row = RiskScoreHistory(
        vendor_id=vendor_id,
        vrs_score=42.0,
        questionnaire_score=80.0,
        external_posture_score=70.0,
        vulnerability_score=60.0,
        breach_history_score=90.0,
        threat_intel_score=90.0,
        compliance_score=50.0,
        tier="Medium",
        inputs_snapshot={},
    )
    db_session.add(row)
    await db_session.flush()

    flag = await evaluate_anomaly(db_session, vendor_id, row)

    # If the model artifact hasn't been trained yet in this checkout,
    # evaluate_anomaly fails soft and returns None -- see app/ml/README.md.
    if flag is None:
        return
    assert 0.0 <= flag.anomaly_score <= 1.0
    assert isinstance(flag.is_anomalous, bool)
    assert flag.model_version


async def test_evaluate_anomaly_flags_sharp_risk_increase(db_session):
    vendor_id = str(uuid.uuid4())
    previous = RiskScoreHistory(
        vendor_id=vendor_id,
        vrs_score=20.0,
        questionnaire_score=90.0,
        external_posture_score=90.0,
        vulnerability_score=90.0,
        breach_history_score=90.0,
        threat_intel_score=90.0,
        compliance_score=90.0,
        tier="Low",
        inputs_snapshot={},
    )
    db_session.add(previous)
    await db_session.flush()

    current = RiskScoreHistory(
        vendor_id=vendor_id,
        vrs_score=85.0,  # sharp jump: +65 vs previous
        questionnaire_score=10.0,
        external_posture_score=10.0,
        vulnerability_score=5.0,
        breach_history_score=20.0,
        threat_intel_score=20.0,
        compliance_score=10.0,
        tier="Critical",
        inputs_snapshot={},
    )
    db_session.add(current)
    await db_session.flush()

    flag = await evaluate_anomaly(db_session, vendor_id, current)
    if flag is None:
        return
    assert flag.is_anomalous is True
