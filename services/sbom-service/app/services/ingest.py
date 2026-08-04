"""SBOM ingestion orchestrator (Module 3 pipeline).

Ties the stages together for one ingest call:
  parse -> normalise PURLs -> SSRF-screen external refs -> CVE cross-reference
  -> persist (Postgres, source of truth) -> mirror to Neo4j (fail-soft)
  -> emit Kafka events (sbom.ingestion.events + per-critical cve.alerts).

The relational write is authoritative and transactional; the graph mirror and
Kafka publish are best-effort enhancements that never fail the ingest.
"""

from __future__ import annotations

import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import SbomComponent, SbomDocument, Vulnerability
from . import events, graph
from .audit import record_audit_event
from .cve_scanner import scan_components
from .internal_auth import get_vendor_summary
from .parsers import detect_and_parse
from .ssrf_guard import is_ref_fetchable


async def ingest_sbom(
    db: AsyncSession,
    *,
    vendor_id: uuid.UUID,
    content: str,
    actor: str,
    document_name: str | None = None,
    format_hint: str | None = None,
) -> tuple[SbomDocument, list[SbomComponent], float]:
    start = time.perf_counter()
    vendor_id_str = str(vendor_id)

    # (i) parse + PURL normalisation --------------------------------------
    parsed = detect_and_parse(content, format_hint=format_hint)

    # SSRF screening of external references. We never fetch by default; record
    # the decision per URL so incomplete/blocked refs are visible for review.
    ref_review: list[dict] = []
    for url in parsed.external_refs:
        allowed, reason = is_ref_fetchable(url)
        if not allowed:
            ref_review.append({"url": url, "action": "not_fetched", "reason": reason})

    synthesised = [c for c in parsed.components if c.synthesised]
    review_notes: dict = {}
    if synthesised:
        review_notes["synthesised_purls"] = [
            {"name": c.name, "version": c.version, "purl": c.purl} for c in synthesised
        ]
    if ref_review:
        review_notes["external_refs"] = ref_review
    incomplete = bool(synthesised)

    # (ii) CVE cross-referencing ------------------------------------------
    scanned = await scan_components(parsed.components)
    vulnerable_count = sum(1 for sc in scanned if sc.vulnerabilities)

    # persist (authoritative) ---------------------------------------------
    document = SbomDocument(
        vendor_id=vendor_id,
        sbom_format=parsed.sbom_format,
        spec_version=parsed.spec_version,
        serialization=parsed.serialization,
        document_name=document_name or parsed.document_name,
        component_count=len(parsed.components),
        vulnerable_count=vulnerable_count,
        incomplete=incomplete,
        review_notes=review_notes,
        ingested_by=actor,
    )
    db.add(document)
    await db.flush()  # assigns document.id

    stored_components: list[SbomComponent] = []
    critical_alerts: list[Vulnerability] = []
    for sc in scanned:
        comp = SbomComponent(
            document_id=document.id,
            vendor_id=vendor_id,
            component_name=sc.component.name,
            version=sc.component.version,
            ecosystem=sc.component.ecosystem,
            purl=sc.component.purl,
            cpe=sc.component.cpe,
            file_hash=sc.component.file_hash,
            purl_synthesised=sc.component.synthesised,
        )
        db.add(comp)
        await db.flush()
        for v in sc.vulnerabilities:
            vuln = Vulnerability(
                component_id=comp.id,
                vendor_id=vendor_id,
                cve_id=v.cve_id,
                description=v.description,
                cvss_score=v.cvss_score,
                cvss_vector=v.cvss_vector,
                severity=v.severity,
                kev_flag=v.kev_flag,
                known_ransomware=v.known_ransomware,
                ssvc_priority=v.ssvc_priority,
            )
            db.add(vuln)
            if v.severity == "Critical" or v.kev_flag:
                critical_alerts.append(vuln)
        stored_components.append(comp)

    await record_audit_event(
        db,
        actor=actor,
        action="SBOM_INGESTED",
        resource=f"vendor:{vendor_id_str}",
        details={
            "document_id": str(document.id),
            "format": parsed.sbom_format,
            "components": len(parsed.components),
            "vulnerable": vulnerable_count,
            "incomplete": incomplete,
        },
    )
    await db.commit()
    await db.refresh(document)
    for comp in stored_components:
        await db.refresh(comp)

    # (iii) mirror to Neo4j (fail-soft) -----------------------------------
    summary = await get_vendor_summary(vendor_id_str)
    vendor_name = (summary or {}).get("name", vendor_id_str)
    tier = (summary or {}).get("overall_tier")
    await graph.upsert_vendor_subgraph(
        vendor_id=vendor_id_str, vendor_name=vendor_name, tier=tier, scanned=scanned
    )

    # events (best effort) -------------------------------------------------
    await events.publish_ingestion_event(
        vendor_id=vendor_id_str,
        document_id=str(document.id),
        component_count=len(parsed.components),
        vulnerable_count=vulnerable_count,
    )
    for v in critical_alerts:
        await events.publish_cve_alert(
            vendor_id=vendor_id_str,
            cve_id=v.cve_id,
            cvss_score=v.cvss_score,
            severity=v.severity,
            kev_flag=v.kev_flag,
        )

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return document, stored_components, round(elapsed_ms, 2)
