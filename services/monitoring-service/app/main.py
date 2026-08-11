"""SC-TPCRS monitoring-service (Module 4 — Continuous Monitoring).

Periodically sweeps every vendor's external security posture (via the shared
mock adapters), records an append-only snapshot time series, detects posture
drift / newly-exposed services / threat-intel matches, and raises deduplicated
alerts. Also reacts to critical CVEs, non-compliant assessments, and risk
anomalies published by the other services, and publishes its own alerts to
MONITORING_ALERTS for incident-service (Module 6).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import Base, engine
from .routers import alerts, dashboard, health, monitoring
from .services.events import build_consumer
from .services.scheduler import SweepScheduler

_consumer = build_consumer()
_scheduler = SweepScheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: create tables if absent (Alembic remains source of truth).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _consumer.start_background()
    _scheduler.start_background()
    yield
    await _scheduler.stop()
    await _consumer.stop()


app = FastAPI(title="SC-TPCRS monitoring-service", lifespan=lifespan)

app.include_router(health.router)
app.include_router(monitoring.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
