"""Continuous monitoring (scheduled threat-intel/CVE jobs, alerting) is
deferred to a future build pass (see the blueprint's Module 4). This
skeleton exists only so the gateway's routing table and docker-compose
topology are complete end-to-end."""

from __future__ import annotations

from fastapi import FastAPI

from .routers import health

app = FastAPI(title="SC-TPCRS monitoring-service (skeleton)")
app.include_router(health.router)
