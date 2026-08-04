from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import SbomComponent, Vulnerability
from ..schemas import ComponentOut, CriticalPathVendor, SupplyChainGraph
from ..services import graph as graph_svc

router = APIRouter(prefix="/sbom/graph", tags=["sbom-graph"])


@router.get("", response_model=SupplyChainGraph)
async def supply_chain_graph(
    vendor_id: str | None = Query(default=None),
    _user: TokenPayload = Depends(get_current_user),
) -> SupplyChainGraph:
    """Force-directed graph view (vendors -> components -> vulnerabilities).

    Optional `vendor_id` scopes to one vendor's subgraph; omit for the whole
    portfolio. Critical-path nodes are flagged via betweenness centrality.
    Returns an empty graph (not an error) if Neo4j is unavailable.
    """
    data = await graph_svc.get_supply_chain_graph(vendor_id)
    return SupplyChainGraph(**data)


@router.get("/critical-path", response_model=list[CriticalPathVendor])
async def critical_path_vendors(
    limit: int = Query(default=10, ge=1, le=50),
    _user: TokenPayload = Depends(get_current_user),
) -> list[CriticalPathVendor]:
    """Vendors ranked by betweenness centrality + PageRank -- the ones whose
    compromise would cascade widest across the supply chain."""
    rows = await graph_svc.get_critical_path_vendors(limit)
    return [CriticalPathVendor(**r) for r in rows]


@router.get("/cve/{cve_id}/impact", response_model=list[ComponentOut])
async def cve_impact(
    cve_id: str,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_user),
) -> list[SbomComponent]:
    """Demo Scenario 1: given a (newly-published) CVE, return every affected
    component across all vendors -- the SBOM cross-reference that identifies
    blast radius in seconds. Relational query (authoritative), CVE-indexed."""
    comp_ids_stmt = select(Vulnerability.component_id).where(Vulnerability.cve_id == cve_id)
    stmt = (
        select(SbomComponent)
        .where(SbomComponent.id.in_(comp_ids_stmt))
        .options(selectinload(SbomComponent.vulnerabilities))
        .order_by(SbomComponent.vendor_id)
    )
    return list((await db.execute(stmt)).scalars().all())
