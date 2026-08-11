"""End-to-end sweep orchestration against the in-memory DB."""

from __future__ import annotations

import uuid

import pytest

from app.models import MonitoringAlert, MonitoringSnapshot
from app.services import sweep_service
from sqlalchemy import func, select


async def test_run_sweep_writes_one_snapshot_per_vendor(db_session, stub_vendors):
    vids = [str(uuid.uuid4()) for _ in range(3)]
    stub_vendors(vids)

    result, touched = await sweep_service.run_sweep(db_session, actor="tester", sweep_epoch=1)

    assert result.vendors_swept == 3
    assert result.snapshots_written == 3
    count = await db_session.scalar(select(func.count()).select_from(MonitoringSnapshot))
    assert count == 3


async def test_second_sweep_appends_history(db_session, stub_vendors):
    vid = str(uuid.uuid4())
    stub_vendors([vid])

    await sweep_service.run_sweep(db_session, actor="tester", sweep_epoch=1)
    await sweep_service.run_sweep(db_session, actor="tester", sweep_epoch=2)

    rows = await sweep_service.vendor_snapshots(db_session, uuid.UUID(vid))
    assert len(rows) == 2
    # Latest first.
    assert rows[0].observed_at >= rows[1].observed_at


async def test_latest_snapshot_per_vendor_dedupes(db_session, stub_vendors):
    vids = [str(uuid.uuid4()) for _ in range(2)]
    stub_vendors(vids)
    await sweep_service.run_sweep(db_session, actor="tester", sweep_epoch=1)
    await sweep_service.run_sweep(db_session, actor="tester", sweep_epoch=2)

    latest = await sweep_service.latest_snapshot_per_vendor(db_session)
    assert len(latest) == 2  # one row per vendor despite two sweeps each


async def test_sweep_records_audit_event(db_session, stub_vendors):
    from app.models import AuditLog

    stub_vendors([str(uuid.uuid4())])
    await sweep_service.run_sweep(db_session, actor="tester", sweep_epoch=1)

    audits = list(await db_session.scalars(select(AuditLog)))
    assert any(a.action == "MONITORING_SWEEP" for a in audits)
    # Hash-chain: each entry has a non-empty hash.
    assert all(a.hash for a in audits)


async def test_sweep_survives_a_bad_vendor(db_session, stub_vendors):
    # "not-a-uuid" makes sweep_vendor raise; the sweep must skip it and still
    # process the good vendor.
    good = str(uuid.uuid4())
    stub_vendors([good, "not-a-uuid"])

    result, _ = await sweep_service.run_sweep(db_session, actor="tester", sweep_epoch=1)

    assert result.vendors_swept == 2
    assert result.snapshots_written == 1


async def test_empty_portfolio_sweeps_cleanly(db_session, stub_vendors):
    stub_vendors([])
    result, touched = await sweep_service.run_sweep(db_session, actor="tester", sweep_epoch=1)
    assert result.snapshots_written == 0
    assert touched == []
