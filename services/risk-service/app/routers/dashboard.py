from __future__ import annotations

from fastapi import APIRouter, Depends
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user
from sc_tpcrs_common.redis_cache import RedisCache
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_db
from ..schemas import DashboardSummaryOut
from ..services.dashboard import DashboardService

router = APIRouter(prefix="/risk/dashboard", tags=["dashboard"])

_cache = RedisCache(settings.redis_url)
service = DashboardService(_cache)


@router.get("/summary", response_model=DashboardSummaryOut)
async def dashboard_summary(
    db: AsyncSession = Depends(get_db), _user: TokenPayload = Depends(get_current_user)
) -> DashboardSummaryOut:
    data = await service.get_summary(db)
    return DashboardSummaryOut(**data)
