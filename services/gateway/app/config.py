from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    redis_url: str = "redis://localhost:6379/0"

    auth_service_url: str = "http://auth-service:8000"
    vendor_service_url: str = "http://vendor-service:8000"
    risk_service_url: str = "http://risk-service:8000"
    sbom_service_url: str = "http://sbom-service:8000"
    compliance_service_url: str = "http://compliance-service:8000"
    monitoring_service_url: str = "http://monitoring-service:8000"
    incident_service_url: str = "http://incident-service:8000"

    gateway_rate_limit_per_min: int = 100
    gateway_login_rate_limit_per_min: int = 5


settings = Settings()
