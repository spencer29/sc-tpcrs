"""SC-TPCRS compliance-service (Module 5).

Third-party compliance monitoring against a multi-framework control library
(ISO 27001:2022, PCI DSS v4.0, SOC 2, NDPR/NDPA, CBN): control-catalogue
lookup, per-vendor assessment with weighted scoring, gap analysis rolled up by
domain, and regulator-ready reporting. Consumes vendor lifecycle events to
auto-baseline vendors and emits compliance.assessment.events for downstream
monitoring/incident services.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routers import compliance, controls, dashboard, health
from .services.events import build_consumer

_consumer = build_consumer()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: create tables if they don't exist yet (Alembic
    # migrations remain the source of truth for staging/production).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _consumer.start_background()
    yield
    await _consumer.stop()


app = FastAPI(title="SC-TPCRS compliance-service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(controls.router)
app.include_router(compliance.router)
app.include_router(dashboard.router)
