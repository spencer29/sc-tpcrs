"""Internal/seeding-only endpoints.

`vendor_tech_stack` is a seed-populated stub standing in for real SBOM
ingestion (sbom-service is deferred -- see models.py's VendorTechStack
docstring). This endpoint exists purely so the seed script (a separate
container with no direct DB access, by design -- see README.md) can
populate it over HTTP like everything else it seeds. admin-only.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sc_tpcrs_common.jwt_shared import TokenPayload, require_role
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import VendorTechStack
from ..schemas import TechStackBulkIn

router = APIRouter(prefix="/internal/vendors/{vendor_id}/tech-stack", tags=["internal"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_tech_stack_components(
    vendor_id: uuid.UUID,
    payload: TechStackBulkIn,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(require_role("admin")),
) -> dict:
    for component in payload.components:
        db.add(
            VendorTechStack(
                vendor_id=vendor_id,
                component_name=component.component_name,
                component_version=component.component_version,
                ecosystem=component.ecosystem,
            )
        )
    await db.commit()
    return {"vendor_id": str(vendor_id), "components_added": len(payload.components)}
