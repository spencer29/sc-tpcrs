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

    # A browser SPA legitimately fans out many calls per page (e.g. the vendor
    # list renders one risk-score request per row). 100/min is fine for a
    # server-to-server client but too low for one interactive user clicking
    # through pages -- overridable via GATEWAY_RATE_LIMIT_PER_MIN.
    gateway_rate_limit_per_min: int = 300
    gateway_login_rate_limit_per_min: int = 5

    # Comma-separated list. The frontend (browser) calls the gateway from a
    # different origin (:5173 vs :8080) -- without CORS headers here, every
    # fetch() from the SPA is silently blocked by the browser regardless of
    # the API itself working fine (curl/server-to-server calls bypass CORS
    # entirely, which is why this gap doesn't show up in backend testing).
    cors_allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
