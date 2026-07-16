"""SBOM ingestion/SBOM graph analysis is deferred to a future build pass
(see the blueprint's Module 3). This skeleton exists only so the gateway's
routing table and docker-compose topology are complete end-to-end."""

from __future__ import annotations

from fastapi import FastAPI

from .routers import health

app = FastAPI(title="SC-TPCRS sbom-service (skeleton)")
app.include_router(health.router)
