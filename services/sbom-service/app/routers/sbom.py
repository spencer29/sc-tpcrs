from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user, require_role
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import SbomComponent, SbomDocument, Vulnerability
from ..schemas import (
    ComponentOut,
    IngestRequest,
    IngestResponse,
    SbomDocumentOut,
    VulnerabilityOut,
)
from ..services.ingest import ingest_sbom
from ..services.parsers import SbomParseError

router = APIRouter(prefix="/sbom", tags=["sbom"])


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest(
    payload: IngestRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("risk_officer", "ciso", "admin")),
) -> IngestResponse:
    try:
        document, components, elapsed_ms = await ingest_sbom(
            db,
            vendor_id=payload.vendor_id,
            content=payload.content,
            actor=user.sub,
            document_name=payload.document_name,
            format_hint=payload.format_hint,
        )
    except SbomParseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

    # Re-load with vulnerabilities eagerly for the response.
    stmt = (
        select(SbomComponent)
        .where(SbomComponent.document_id == document.id)
        .options(selectinload(SbomComponent.vulnerabilities))
    )
    loaded = (await db.execute(stmt)).scalars().all()

    critical = [
        VulnerabilityOut.model_validate(v)
        for c in loaded
        for v in c.vulnerabilities
        if v.severity == "Critical" or v.kev_flag
    ]

    return IngestResponse(
        document=SbomDocumentOut.model_validate(document),
        components=[ComponentOut.model_validate(c) for c in loaded],
        critical_vulnerabilities=critical,
        processing_ms=elapsed_ms,
    )


@router.get("/vendors/{vendor_id}/documents", response_model=list[SbomDocumentOut])
async def list_vendor_sboms(
    vendor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> list[SbomDocument]:
    stmt = (
        select(SbomDocument)
        .where(SbomDocument.vendor_id == vendor_id)
        .order_by(SbomDocument.ingested_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


@router.get("/vendors/{vendor_id}/components", response_model=list[ComponentOut])
async def list_vendor_components(
    vendor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
    vulnerable_only: bool = Query(default=False),
) -> list[SbomComponent]:
    stmt = (
        select(SbomComponent)
        .where(SbomComponent.vendor_id == vendor_id)
        .options(selectinload(SbomComponent.vulnerabilities))
        .order_by(SbomComponent.component_name)
    )
    components = list((await db.execute(stmt)).scalars().all())
    if vulnerable_only:
        components = [c for c in components if c.vulnerabilities]
    return components


@router.get("/vendors/{vendor_id}/vulnerabilities", response_model=list[VulnerabilityOut])
async def list_vendor_vulnerabilities(
    vendor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> list[Vulnerability]:
    stmt = (
        select(Vulnerability)
        .where(Vulnerability.vendor_id == vendor_id)
        .order_by(Vulnerability.cvss_score.desc().nullslast())
    )
    return list((await db.execute(stmt)).scalars().all())
