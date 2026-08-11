from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "postgresql+asyncpg://sctpcrs:sctpcrs_dev_password@localhost:5432/monitoring"
    kafka_bootstrap_servers: str = "localhost:9092"
    vendor_service_url: str = "http://vendor-service:8000"
    seed_random_seed: int = 42

    # Continuous-monitoring sweep cadence. In a real deployment this would be
    # a cron/Celery-beat schedule (e.g. hourly); here the in-process scheduler
    # runs a sweep every `sweep_interval_seconds`. Kept long by default so the
    # demo isn't noisy; the API also exposes a manual "sweep now" trigger.
    sweep_interval_seconds: int = 900
    # Run one sweep shortly after startup so a fresh stack has data to show.
    sweep_on_startup: bool = True
    sweep_startup_delay_seconds: int = 15

    # Drift thresholds (points, on the 0-100 posture scale) that promote a
    # snapshot delta into an alert of escalating severity.
    posture_drift_warning: float = 8.0
    posture_drift_critical: float = 20.0


settings = Settings()
