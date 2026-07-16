from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import Base, engine
from .routers import documents, health, questionnaires, vendors


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: create tables if they don't exist yet (Alembic
    # migrations remain the source of truth for staging/production).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="SC-TPCRS vendor-service", lifespan=lifespan)

app.include_router(health.router)
app.include_router(vendors.router)
app.include_router(questionnaires.router)
app.include_router(documents.router)
