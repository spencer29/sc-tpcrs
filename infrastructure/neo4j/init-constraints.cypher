// Constraints/indexes only for this build pass -- no data is loaded here.
// The Vendor/Component/Vulnerability graph itself is populated by
// sbom-service's ingestion pipeline, which is deferred to a future pass.
// This file proves Neo4j connectivity and reserves the target schema shape
// described in the blueprint (Organisation/Vendor/SubVendor/SoftwareComponent/
// Vulnerability nodes).

CREATE CONSTRAINT vendor_id_unique IF NOT EXISTS
FOR (v:Vendor) REQUIRE v.id IS UNIQUE;

CREATE CONSTRAINT component_purl_unique IF NOT EXISTS
FOR (c:SoftwareComponent) REQUIRE c.purl IS UNIQUE;

CREATE CONSTRAINT vulnerability_cve_unique IF NOT EXISTS
FOR (vu:Vulnerability) REQUIRE vu.cve_id IS UNIQUE;

CREATE INDEX vendor_risk_tier IF NOT EXISTS
FOR (v:Vendor) ON (v.risk_tier);
