"""SC-TPCRS incident-service (Module 6 — Incident Response Integration).

Turns high/critical monitoring alerts into tracked incidents, drives their
lifecycle (open -> investigating -> contained -> resolved -> closed) with an
append-only timeline and an SLA clock, and drafts the Nigerian regulatory
notifications each incident warrants (CBN material-incident report, NDPC
personal-data-breach notification). Consumes MONITORING_ALERTS and publishes
INCIDENT_EVENTS.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import Base, engine
from .routers import dashboard, health, incidents
from .services.events import build_consumer

_consumer = build_consumer()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: create tables if absent (Alembic remains source of truth).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _consumer.start_background()
    yield
    await _consumer.stop()


app = FastAPI(title="SC-TPCRS incident-service", lifespan=lifespan)

app.include_router(health.router)
app.include_router(incidents.router)
app.include_router(dashboard.router)
