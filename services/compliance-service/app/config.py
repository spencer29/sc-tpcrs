from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "postgresql+asyncpg://sctpcrs:sctpcrs_dev_password@localhost:5432/compliance"
    kafka_bootstrap_servers: str = "localhost:9092"
    vendor_service_url: str = "http://vendor-service:8000"
    # Deterministic seed so mock evidence-collection / assessment generation
    # is reproducible across demo runs (same convention as risk-service).
    seed_random_seed: int = 42


settings = Settings()
