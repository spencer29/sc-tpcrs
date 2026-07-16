from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "postgresql+asyncpg://sctpcrs:sctpcrs_dev_password@localhost:5432/auth"
    jwt_secret: str = "change_me_dev_only_shared_hs256_secret_please_rotate_in_real_deploys"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 7
    mfa_secret_enc_key: str = "change_me_dev_only_fernet_key_32byte_urlsafe_base64=="
    env: str = "production"

    @property
    def is_development(self) -> bool:
        return self.env.lower() == "development"


settings = Settings()
