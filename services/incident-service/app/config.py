from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "postgresql+asyncpg://sctpcrs:sctpcrs_dev_password@localhost:5432/incident"
    kafka_bootstrap_servers: str = "localhost:9092"

    # Severity at/above which an inbound monitoring alert auto-opens an incident.
    # Critical/High are actioned automatically; Medium/Low are left to the
    # monitoring queue unless an analyst promotes them manually.
    auto_open_min_severity: str = "High"

    # Resolution SLA windows (hours) per severity. Critical mirrors the CBN
    # 24-hour material-incident reporting expectation; the rest are internal
    # response targets. `sla_due_at = opened_at + window`.
    sla_hours_critical: int = 24
    sla_hours_high: int = 72
    sla_hours_medium: int = 168
    sla_hours_low: int = 336

    # Regulatory notification deadlines (hours from incident open).
    # CBN: material cyber incidents at financial institutions reported within 24h.
    # NDPA/NDPR: personal-data breaches notified to the NDPC within 72h.
    cbn_deadline_hours: int = 24
    ndpa_deadline_hours: int = 72


settings = Settings()
