"""SC-TPCRS sbom-service (Module 3).

CycloneDX/SPDX SBOM ingestion, CVE cross-referencing (mock NVD + CISA KEV
adapters), and a Neo4j dependency graph with betweenness/PageRank analytics.
See services/ingest.py for the pipeline and README/ARCHITECTURE for the
GDS-via-networkx and mock-adapter deviations.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import Base, engine
from .routers import graph, health, sbom
from .services import events
from .services.graph import close_driver


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: create tables if they don't exist yet (Alembic
    # migrations remain the source of truth for staging/production).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await events.close()
    await close_driver()


app = FastAPI(title="SC-TPCRS sbom-service", lifespan=lifespan)

app.include_router(health.router)
app.include_router(sbom.router)
app.include_router(graph.router)
