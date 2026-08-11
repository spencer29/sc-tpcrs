"""Sweep orchestration + snapshot/alert persistence.

`run_sweep` is the continuous-monitoring heartbeat: for every vendor in the
portfolio it collects a posture reading, computes drift vs the vendor's
previous snapshot, writes a new append-only snapshot, and upserts any alerts
the reading triggers. Newly-opened/changed alerts are published to
MONITORING_ALERTS after commit so incident-service (Module 6) can react.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import MonitoringAlert, MonitoringSnapshot
from ..schemas import SweepResult
from . import alert_engine, vendor_client
from .audit import record_audit_event
from .posture import collect_posture, rotating_probe


async def _previous_snapshot(db: AsyncSession, vendor_id: uuid.UUID) -> MonitoringSnapshot | None:
    return await db.scalar(
        select(MonitoringSnapshot)
        .where(MonitoringSnapshot.vendor_id == vendor_id)
        .order_by(MonitoringSnapshot.observed_at.desc())
        .limit(1)
    )


async def sweep_vendor(
    db: AsyncSession, vendor_id: str, *, sweep_epoch: int
) -> tuple[MonitoringSnapshot, list[MonitoringAlert], int]:
    """Sweep a single vendor. Returns (snapshot, touched_alerts, created_count).

    Does not commit -- caller owns the transaction."""
    vendor_uuid = uuid.UUID(str(vendor_id))
    prev = await _previous_snapshot(db, vendor_uuid)
    prev_services = list(prev.raw.get("shodan", {}).get("open_services", [])) if prev is not None else None
    prev_exposure = float(prev.exposure_index) if prev is not None else None

    probe = rotating_probe(str(vendor_id), sweep_epoch)
    reading = await collect_posture(str(vendor_id), drift_probe=probe)

    drift = round(reading.exposure_index - prev_exposure, 2) if prev_exposure is not None else 0.0

    snapshot = MonitoringSnapshot(
        vendor_id=vendor_uuid,
        posture_score=reading.posture_score,
        open_service_count=len(reading.open_services),
        ioc_match_count=reading.ioc_match_count,
        abuse_report_count=reading.abuse_report_count,
        exposure_index=reading.exposure_index,
        drift=drift,
        raw=reading.raw,
        observed_at=datetime.now(timezone.utc),
    )
    db.add(snapshot)
    await db.flush()

    specs = alert_engine.evaluate_snapshot(
        str(vendor_id),
        reading,
        previous_exposure=prev_exposure,
        previous_services=prev_services,
    )
    touched: list[MonitoringAlert] = []
    created = 0
    for spec in specs:
        alert, was_created = await alert_engine.upsert_alert(db, spec)
        touched.append(alert)
        created += 1 if was_created else 0

    return snapshot, touched, created


async def run_sweep(db: AsyncSession, *, actor: str, sweep_epoch: int, limit: int = 200) -> tuple[SweepResult, list[MonitoringAlert]]:
    """Sweep the whole vendor portfolio. Commits, then returns the result plus
    the alerts that were opened/updated (for the caller to publish)."""
    started = time.perf_counter()
    vendors = await vendor_client.list_vendor_ids(limit=limit)

    snapshots_written = 0
    alerts_opened = 0
    alerts_updated = 0
    all_touched: list[MonitoringAlert] = []

    for v in vendors:
        try:
            _snap, touched, created = await sweep_vendor(db, v["id"], sweep_epoch=sweep_epoch)
        except Exception:  # noqa: BLE001 - one bad vendor must not abort the whole sweep
            continue
        snapshots_written += 1
        alerts_opened += created
        alerts_updated += len(touched) - created
        all_touched.extend(touched)

    await record_audit_event(
        db,
        actor=actor,
        action="MONITORING_SWEEP",
        resource="portfolio",
        details={
            "vendors_swept": len(vendors),
            "snapshots_written": snapshots_written,
            "alerts_opened": alerts_opened,
            "alerts_updated": alerts_updated,
            "sweep_epoch": sweep_epoch,
        },
    )
    await db.commit()

    result = SweepResult(
        vendors_swept=len(vendors),
        snapshots_written=snapshots_written,
        alerts_opened=alerts_opened,
        alerts_updated=alerts_updated,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    return result, all_touched


# --- Read helpers used by routers/dashboard ---
async def latest_snapshot_per_vendor(db: AsyncSession, limit: int = 1000) -> list[MonitoringSnapshot]:
    rows = list(
        await db.scalars(
            select(MonitoringSnapshot).order_by(MonitoringSnapshot.observed_at.desc()).limit(limit)
        )
    )
    latest: dict[uuid.UUID, MonitoringSnapshot] = {}
    for r in rows:
        if r.vendor_id not in latest:
            latest[r.vendor_id] = r
    return list(latest.values())


async def vendor_snapshots(db: AsyncSession, vendor_id: uuid.UUID, limit: int = 50) -> list[MonitoringSnapshot]:
    return list(
        await db.scalars(
            select(MonitoringSnapshot)
            .where(MonitoringSnapshot.vendor_id == vendor_id)
            .order_by(MonitoringSnapshot.observed_at.desc())
            .limit(limit)
        )
    )


async def list_alerts(
    db: AsyncSession,
    *,
    vendor_id: uuid.UUID | None = None,
    status: str | None = None,
    severity: str | None = None,
    limit: int = 100,
) -> list[MonitoringAlert]:
    stmt = select(MonitoringAlert)
    if vendor_id is not None:
        stmt = stmt.where(MonitoringAlert.vendor_id == vendor_id)
    if status is not None:
        stmt = stmt.where(MonitoringAlert.status == status)
    if severity is not None:
        stmt = stmt.where(MonitoringAlert.severity == severity)
    stmt = stmt.order_by(MonitoringAlert.last_seen_at.desc()).limit(limit)
    return list(await db.scalars(stmt))


async def get_alert(db: AsyncSession, alert_id: uuid.UUID) -> MonitoringAlert | None:
    return await db.get(MonitoringAlert, alert_id)


async def count_open_alerts(db: AsyncSession) -> int:
    return int(
        await db.scalar(
            select(func.count()).select_from(MonitoringAlert).where(MonitoringAlert.status != "resolved")
        )
        or 0
    )
