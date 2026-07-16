from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sc_tpcrs_common.jwt_shared import TokenPayload, get_current_user, require_role
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_db
from ..models import Vendor, VendorDocument
from ..schemas import DocumentOut
from ..services.audit import record_audit_event
from ..storage.local_file_store import LocalFileStore

router = APIRouter(prefix="/vendors/{vendor_id}/documents", tags=["documents"])

_store = LocalFileStore(settings.document_storage_root)

DOCUMENT_TYPES = (
    "CONTRACT",
    "ISO27001_CERT",
    "PCI_DSS_AOC",
    "SOC2_REPORT",
    "NDA",
    "OTHER",
)


async def _get_vendor_or_404(db: AsyncSession, vendor_id: uuid.UUID) -> Vendor:
    vendor = await db.get(Vendor, vendor_id)
    if vendor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor not found")
    return vendor


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    vendor_id: uuid.UUID,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(require_role("risk_officer", "admin")),
) -> VendorDocument:
    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown document_type: {document_type}")
    await _get_vendor_or_404(db, vendor_id)

    content = await file.read()
    document_id = uuid.uuid4()
    storage_path = await _store.save(str(vendor_id), str(document_id), file.filename or "upload", content)

    document = VendorDocument(
        id=document_id,
        vendor_id=vendor_id,
        document_type=document_type,
        file_name=file.filename or "upload",
        storage_path=storage_path,
        content_type=file.content_type,
        size_bytes=len(content),
        uploaded_by=user.sub,
    )
    db.add(document)
    await record_audit_event(
        db,
        actor=user.sub,
        action="DOCUMENT_UPLOADED",
        resource=f"vendor:{vendor_id}",
        details={"document_id": str(document_id), "document_type": document_type},
    )
    await db.commit()
    await db.refresh(document)
    return document


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    vendor_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: TokenPayload = Depends(get_current_user)
) -> list[VendorDocument]:
    await _get_vendor_or_404(db, vendor_id)
    stmt = select(VendorDocument).where(VendorDocument.vendor_id == vendor_id).order_by(VendorDocument.uploaded_at.desc())
    return list((await db.execute(stmt)).scalars().all())
