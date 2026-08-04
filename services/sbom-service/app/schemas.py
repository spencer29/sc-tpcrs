from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IngestRequest(BaseModel):
    """Ingest an SBOM for a vendor.

    `content` is the raw SBOM document (CycloneDX JSON/XML or SPDX
    JSON/tag-value). Format and serialization are auto-detected; the optional
    hints below only override detection when a caller already knows them.
    """

    vendor_id: uuid.UUID
    content: str = Field(min_length=1, max_length=10_000_000)  # 10MB gateway cap
    document_name: str | None = None
    format_hint: str | None = None  # "CycloneDX" | "SPDX"


class VulnerabilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cve_id: str
    description: str | None
    cvss_score: float | None
    severity: str
    kev_flag: bool
    known_ransomware: bool
    ssvc_priority: str
    status: str


class ComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    component_name: str
    version: str
    ecosystem: str
    purl: str
    cpe: str | None
    purl_synthesised: bool
    vulnerabilities: list[VulnerabilityOut] = []


class SbomDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendor_id: uuid.UUID
    sbom_format: str
    spec_version: str | None
    serialization: str | None
    document_name: str | None
    component_count: int
    vulnerable_count: int
    incomplete: bool
    review_notes: dict
    ingested_at: datetime


class IngestResponse(BaseModel):
    document: SbomDocumentOut
    components: list[ComponentOut]
    # Convenience roll-up so the demo scenario can assert "N critical CVEs found"
    # without re-walking the component tree client-side.
    critical_vulnerabilities: list[VulnerabilityOut]
    processing_ms: float


# ------------------------------------------------------------- graph views --
class GraphNode(BaseModel):
    id: str
    label: str  # "Vendor" | "SoftwareComponent" | "Vulnerability"
    name: str
    # Optional analytics attributes (present on Vendor/Component nodes)
    tier: str | None = None
    severity: str | None = None
    critical_path: bool = False
    centrality: float | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str  # "PROVIDES" | "DEPENDS_ON" | "AT_RISK"


class SupplyChainGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class CriticalPathVendor(BaseModel):
    vendor_id: str
    name: str
    betweenness: float
    pagerank: float
    dependent_component_count: int
