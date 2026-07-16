from __future__ import annotations

from fastapi import FastAPI

from .db import Base, engine
from .routers import auth, health

app = FastAPI(title="SC-TPCRS auth-service")

app.include_router(health.router)
app.include_router(auth.router)


@app.on_event("startup")
async def on_startup() -> None:
    # Dev convenience: create tables if they don't exist yet (Alembic
    # migrations remain the source of truth for staging/production).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
