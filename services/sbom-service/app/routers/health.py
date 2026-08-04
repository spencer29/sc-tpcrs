from __future__ import annotations

from fastapi import APIRouter

from ..services import graph as graph_svc

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    # Report Neo4j reachability without failing the health check on it -- the
    # graph is an enhancement; the service is healthy as long as it can serve
    # its HTTP API and relational cross-reference.
    return {"status": "ok", "service": "sbom-service", "neo4j": await graph_svc.health()}
