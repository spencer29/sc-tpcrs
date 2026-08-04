from __future__ import annotations

from fastapi import APIRouter

from ..control_library import ALL_FRAMEWORKS, all_controls, framework_control_counts, library_size
from ..schemas import ControlLibraryOut, ControlOut, FrameworkSummaryOut

# Static reference data -- no auth beyond the gateway's JWT check (any
# authenticated user may read the control catalogue). Mounted under the
# /compliance prefix the gateway forwards unchanged.
router = APIRouter(prefix="/compliance/controls", tags=["compliance-controls"])


@router.get("", response_model=ControlLibraryOut)
async def get_control_library() -> ControlLibraryOut:
    counts = framework_control_counts()
    return ControlLibraryOut(
        total_controls=library_size(),
        frameworks=[FrameworkSummaryOut(framework=fw, control_count=counts[fw]) for fw in ALL_FRAMEWORKS],
    )


@router.get("/list", response_model=list[ControlOut])
async def list_controls(framework: str | None = None) -> list[ControlOut]:
    controls = all_controls()
    if framework:
        controls = tuple(c for c in controls if c.framework == framework)
    return [
        ControlOut(
            control_id=c.control_id,
            framework=c.framework,
            reference=c.reference,
            domain=c.domain,
            title=c.title,
            objective=c.objective,
            weight=c.weight,
            tags=list(c.tags),
        )
        for c in controls
    ]
