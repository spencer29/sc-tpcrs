from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "postgresql+asyncpg://sctpcrs:sctpcrs_dev_password@localhost:5432/vendor"
    kafka_bootstrap_servers: str = "localhost:9092"
    document_storage_root: str = "/data/vendor-documents"


settings = Settings()
