from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import Base, engine
from .routers import dashboard, health, internal, risk
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


app = FastAPI(title="SC-TPCRS risk-service", lifespan=lifespan)

app.include_router(health.router)
app.include_router(risk.router)
app.include_router(dashboard.router)
app.include_router(internal.router)
