from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "postgresql+asyncpg://sctpcrs:sctpcrs_dev_password@localhost:5432/risk"
    kafka_bootstrap_servers: str = "localhost:9092"
    redis_url: str = "redis://localhost:6379/0"
    vendor_service_url: str = "http://vendor-service:8000"
    seed_random_seed: int = 42


settings = Settings()
