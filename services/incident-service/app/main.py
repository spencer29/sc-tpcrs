"""Incident response integration (impact assessment, CBN/NDPA notification
generation, ticketing) is deferred to a future build pass (see the
blueprint's Module 6). This skeleton exists only so the gateway's routing
table and docker-compose topology are complete end-to-end."""

from __future__ import annotations

from fastapi import FastAPI

from .routers import health

app = FastAPI(title="SC-TPCRS incident-service (skeleton)")
app.include_router(health.router)
