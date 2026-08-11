"""Alert generation, deduplication, and lifecycle.

Two entry points produce alerts:
  1. `evaluate_snapshot` -- turns a fresh posture snapshot (drift, new exposed
     services) into zero or more alert specs.
  2. `alert_from_event` -- turns another service's Kafka event (critical CVE,
     non-compliant assessment, risk anomaly, threat-intel match) into an alert
     spec.

Both feed `upsert_alert`, which deduplicates on (vendor_id, dedup_key) among
OPEN alerts: a repeat of the same open finding bumps occurrence_count and
last_seen_at instead of creating a new row, so a persistently-exposed vendor
doesn't generate a new alert every single sweep. A resolved finding that recurs
opens a fresh alert (the old resolved row is history).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import MonitoringAlert
from .posture import PostureReading

# Alert types.
POSTURE_DRIFT = "POSTURE_DRIFT"
NEW_EXPOSED_SERVICE = "NEW_EXPOSED_SERVICE"
THREAT_INTEL_MATCH = "THREAT_INTEL_MATCH"
CRITICAL_CVE = "CRITICAL_CVE"
COMPLIANCE_GAP = "COMPLIANCE_GAP"
RISK_ANOMALY = "RISK_ANOMALY"

# High-risk service ports/protocols that should never be freshly exposed.
_SENSITIVE_SERVICES = {"rdp", "ftp", "smtp", "telnet"}


@dataclass
class AlertSpec:
    vendor_id: str
    alert_type: str
    severity: str
    title: str
    description: str
    dedup_key: str
    source: str = "sweep"
    details: dict = field(default_factory=dict)


def _drift_severity(drift: float) -> str | None:
    if drift >= settings.posture_drift_critical:
        return "Critical"
    if drift >= settings.posture_drift_warning:
        return "High"
    return None


def evaluate_snapshot(
    vendor_id: str,
    reading: PostureReading,
    *,
    previous_exposure: float | None,
    previous_services: list[str] | None,
) -> list[AlertSpec]:
    """Derive alert specs from a new snapshot vs the vendor's previous state."""
    specs: list[AlertSpec] = []

    # 1. Posture drift (exposure worsened by >= threshold).
    if previous_exposure is not None:
        drift = round(reading.exposure_index - previous_exposure, 2)
        sev = _drift_severity(drift)
        if sev is not None:
            specs.append(
                AlertSpec(
                    vendor_id=vendor_id,
                    alert_type=POSTURE_DRIFT,
                    severity=sev,
                    title=f"Security posture degraded by {drift:.1f} points",
                    description=(
                        f"Exposure index rose from {previous_exposure:.1f} to "
                        f"{reading.exposure_index:.1f} since the last sweep."
                    ),
                    dedup_key=f"{POSTURE_DRIFT}",
                    details={"drift": drift, "exposure_index": reading.exposure_index},
                )
            )

    # 2. Newly-exposed sensitive services.
    prev = set(previous_services or [])
    new_sensitive = sorted((set(reading.open_services) - prev) & _SENSITIVE_SERVICES)
    for svc in new_sensitive:
        specs.append(
            AlertSpec(
                vendor_id=vendor_id,
                alert_type=NEW_EXPOSED_SERVICE,
                severity="High",
                title=f"Newly exposed sensitive service: {svc.upper()}",
                description=f"The '{svc}' service is now internet-exposed and was not in the prior scan.",
                dedup_key=f"{NEW_EXPOSED_SERVICE}:{svc}",
                details={"service": svc, "open_services": reading.open_services},
            )
        )

    # 3. Active threat-intel IOC matches.
    if reading.ioc_match_count > 0:
        specs.append(
            AlertSpec(
                vendor_id=vendor_id,
                alert_type=THREAT_INTEL_MATCH,
                severity="High" if reading.ioc_match_count >= 3 else "Medium",
                title=f"{reading.ioc_match_count} threat-intel IOC match(es)",
                description="Indicators of compromise associated with this vendor's assets were observed.",
                dedup_key=f"{THREAT_INTEL_MATCH}",
                details={"ioc_match_count": reading.ioc_match_count},
            )
        )

    return specs


# --- Kafka-event-sourced alerts ---
def alert_from_event(topic: str, event: dict) -> AlertSpec | None:
    """Map an inbound event envelope to an alert spec, or None if not actionable."""
    payload = event.get("payload", {})
    vendor_id = payload.get("vendor_id")
    if not vendor_id:
        return None

    # Critical CVE affecting a vendor's components (from sbom-service).
    if topic.endswith("cve.alerts") or event.get("event_type", "").startswith("cve."):
        cve = payload.get("cve_id", "a critical CVE")
        return AlertSpec(
            vendor_id=str(vendor_id),
            alert_type=CRITICAL_CVE,
            severity="Critical",
            title=f"Critical CVE affecting vendor components: {cve}",
            description=payload.get("description") or f"{cve} was flagged against this vendor's software components.",
            dedup_key=f"{CRITICAL_CVE}:{cve}",
            source=topic,
            details=payload,
        )

    # Non-compliant / critical-gap compliance assessment (from compliance-service).
    if "compliance" in topic or event.get("event_type", "").startswith("compliance."):
        status = payload.get("status")
        crit = int(payload.get("critical_gap_count", 0) or 0)
        if status == "Non-Compliant" or crit > 0:
            return AlertSpec(
                vendor_id=str(vendor_id),
                alert_type=COMPLIANCE_GAP,
                severity="High" if status == "Non-Compliant" else "Medium",
                title=f"Compliance issue: {status} ({crit} critical gap(s))",
                description=f"Latest {payload.get('framework', 'compliance')} assessment scored "
                f"{payload.get('compliance_score', '?')}% ({status}).",
                dedup_key=f"{COMPLIANCE_GAP}:{payload.get('framework', 'ALL')}",
                source=topic,
                details=payload,
            )
        return None

    # Risk anomaly (from risk-service).
    if "anomaly" in topic or event.get("event_type", "").startswith("risk.anomaly"):
        return AlertSpec(
            vendor_id=str(vendor_id),
            alert_type=RISK_ANOMALY,
            severity="High",
            title="Anomalous risk-score movement detected",
            description="risk-service flagged this vendor's latest score as anomalous.",
            dedup_key=f"{RISK_ANOMALY}",
            source=topic,
            details=payload,
        )

    return None


async def upsert_alert(db: AsyncSession, spec: AlertSpec) -> tuple[MonitoringAlert, bool]:
    """Insert a new alert, or bump an existing OPEN one with the same dedup key.

    Returns (alert, created) where created=True means a new row was inserted.
    Does not commit -- the caller owns the transaction."""
    import uuid as _uuid
    from datetime import datetime, timezone

    vendor_uuid = _uuid.UUID(str(spec.vendor_id))
    existing = await db.scalar(
        select(MonitoringAlert)
        .where(
            MonitoringAlert.vendor_id == vendor_uuid,
            MonitoringAlert.dedup_key == spec.dedup_key,
            MonitoringAlert.status != "resolved",
        )
        .order_by(MonitoringAlert.first_seen_at.desc())
        .limit(1)
    )
    now = datetime.now(timezone.utc)
    if existing is not None:
        existing.occurrence_count += 1
        existing.last_seen_at = now
        # Escalate severity if this occurrence is worse.
        if _severity_rank(spec.severity) > _severity_rank(existing.severity):
            existing.severity = spec.severity
            existing.title = spec.title
        existing.details = spec.details
        existing.published = False  # re-publish on material change
        return existing, False

    alert = MonitoringAlert(
        vendor_id=vendor_uuid,
        alert_type=spec.alert_type,
        severity=spec.severity,
        title=spec.title,
        description=spec.description,
        dedup_key=spec.dedup_key,
        source=spec.source,
        details=spec.details,
        status="open",
        occurrence_count=1,
        first_seen_at=now,
        last_seen_at=now,
        published=False,
    )
    db.add(alert)
    await db.flush()
    return alert, True


_SEVERITY_ORDER = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


def _severity_rank(sev: str) -> int:
    return _SEVERITY_ORDER.get(sev, 0)
