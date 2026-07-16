"""Local-disk document storage, behind a small Protocol so a future
MinioFileStore/S3 implementation is a drop-in swap without touching callers.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Protocol

import aiofiles


class FileStore(Protocol):
    async def save(self, vendor_id: str, document_id: str, filename: str, content: bytes) -> str: ...

    async def read(self, storage_path: str) -> bytes: ...


_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9_.\-]")


def _sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename)
    return _UNSAFE_CHARS.sub("_", base) or "file"


class LocalFileStore:
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    async def save(self, vendor_id: str, document_id: str, filename: str, content: bytes) -> str:
        # vendor_id/document_id are always server-generated UUIDs (never
        # taken from user input), so no traversal risk there; only the
        # human-supplied filename needs sanitizing.
        safe_name = _sanitize_filename(filename)
        relative_path = Path(str(uuid.UUID(vendor_id))) / f"{uuid.UUID(document_id)}_{safe_name}"
        full_path = self._root / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)
        return str(relative_path).replace(os.sep, "/")

    async def read(self, storage_path: str) -> bytes:
        full_path = (self._root / storage_path).resolve()
        if self._root.resolve() not in full_path.parents and full_path != self._root.resolve():
            raise ValueError("Invalid storage path")
        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()
