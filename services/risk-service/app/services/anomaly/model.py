from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import joblib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import AnomalyFlag, RiskScoreHistory
from .features import FEATURE_NAMES, build_feature_vector

logger = logging.getLogger("risk-service.anomaly")

ML_DIR = Path(__file__).resolve().parent.parent.parent / "ml"
ANOMALY_THRESHOLD = 0.7

_model = None
_model_version = "unversioned"
_load_attempted = False


def _load_model():
    """Lazily loads the committed model artifact. Fails soft (returns None)
    if it isn't present -- e.g. `make train-anomaly-model` hasn't been run
    yet in a fresh checkout -- consistent with this project's
    degrade-don't-crash posture for optional enrichment steps."""
    global _model, _model_version, _load_attempted
    if _model is None and not _load_attempted:
        _load_attempted = True
        try:
            _model = joblib.load(ML_DIR / "model.pkl")
            metrics_path = ML_DIR / "metrics.json"
            if metrics_path.exists():
                _model_version = json.loads(metrics_path.read_text()).get("model_version", "unversioned")
        except FileNotFoundError:
            logger.warning(
                "Anomaly model artifact not found at %s -- run `make train-anomaly-model`. "
                "Anomaly detection disabled until then.",
                ML_DIR / "model.pkl",
            )
    return _model


async def evaluate_anomaly(
    db: AsyncSession, vendor_id: uuid.UUID | str, current_row: RiskScoreHistory
) -> AnomalyFlag | None:
    model = _load_model()
    if model is None:
        return None

    stmt = (
        select(RiskScoreHistory)
        .where(RiskScoreHistory.vendor_id == vendor_id, RiskScoreHistory.id != current_row.id)
        .order_by(RiskScoreHistory.computed_at.desc())
        .limit(1)
    )
    previous = (await db.execute(stmt)).scalar_one_or_none()
    previous_vrs = float(previous.vrs_score) if previous is not None else float(current_row.vrs_score)
    delta = float(current_row.vrs_score) - previous_vrs

    features = build_feature_vector(
        questionnaire_score=float(current_row.questionnaire_score),
        external_posture_score=float(current_row.external_posture_score),
        vulnerability_score=float(current_row.vulnerability_score),
        breach_history_score=float(current_row.breach_history_score),
        threat_intel_score=float(current_row.threat_intel_score),
        compliance_score=float(current_row.compliance_score),
        vrs_score=float(current_row.vrs_score),
        tier=current_row.tier,
        vrs_delta_vs_previous=delta,
    )

    proba = float(model.predict_proba([features])[0][1])
    is_anomalous = proba >= ANOMALY_THRESHOLD

    flag = AnomalyFlag(
        vendor_id=vendor_id,
        anomaly_score=proba,
        is_anomalous=is_anomalous,
        feature_snapshot=dict(zip(FEATURE_NAMES, features, strict=True)),
        model_version=_model_version,
    )
    db.add(flag)
    await db.flush()
    return flag
