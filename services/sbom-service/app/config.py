from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "postgresql+asyncpg://sctpcrs:sctpcrs_dev_password@localhost:5432/sbom"
    kafka_bootstrap_servers: str = "localhost:9092"
    vendor_service_url: str = "http://vendor-service:8000"

    # Neo4j dependency graph. sbom-service is the only writer of the
    # Vendor/SoftwareComponent/Vulnerability graph (see infrastructure/neo4j).
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "sctpcrs_dev_password"

    # When Neo4j is unreachable (e.g. running unit tests without docker compose),
    # the graph writer fails soft rather than blocking SBOM ingestion -- the
    # relational cross-reference is the source of truth; the graph is an
    # enhancement, mirroring the Kafka "fail soft" stance in kafka_base.py.
    neo4j_enabled: bool = True

    # SSRF guard: SBOM external-reference URLs are NEVER fetched by default.
    # Even when enabled, only these hosts may be dereferenced (allow-list).
    sbom_fetch_external_refs: bool = False
    sbom_ref_allowed_hosts: str = ""  # comma-separated; empty = allow none


settings = Settings()
