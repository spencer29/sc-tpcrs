"""Common contract every external-integration adapter implements.

Every real external dependency in the blueprint (NVD, CISA KEV, MISP,
VirusTotal, Shodan, AbuseIPDB, Jira/ServiceNow) is accessed exclusively
through a subclass of `ExternalAdapter`. Callers only ever depend on this
interface, never on a concrete mock/real implementation directly -- see
`registry.py` for how the mode switch works.

Mock responses must be:
  1. Deterministic for a given input (same params -> same fake result),
     using `stable_seed()` below rather than Python's randomized `hash()`,
     so demo runs and tests are repeatable.
  2. Schema-shaped like the real API's response, so a future switch to
     `mode="real"` requires no downstream parsing changes.
"""

from __future__ import annotations

import hashlib
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from faker import Faker

AdapterMode = Literal["mock", "real"]


def stable_seed(*parts: Any) -> int:
    """Deterministic 32-bit seed derived from arbitrary parts.

    Uses sha256 rather than Python's built-in hash(), which is randomized
    per-process (PYTHONHASHSEED) and therefore NOT safe for reproducible
    mock data across separate runs/services.
    """
    material = "|".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()
    return int(digest[:8], 16)


def seeded_random(*parts: Any) -> random.Random:
    return random.Random(stable_seed(*parts))


def seeded_faker(*parts: Any) -> Faker:
    fake = Faker()
    Faker.seed(stable_seed(*parts))
    return fake


@dataclass
class AdapterResult:
    source: str
    data: Any
    fetched_at: str
    is_mock: bool

    @classmethod
    def make(cls, source: str, data: Any, is_mock: bool) -> "AdapterResult":
        return cls(source=source, data=data, fetched_at=datetime.now(timezone.utc).isoformat(), is_mock=is_mock)


class ExternalAdapter(ABC):
    """Base class for every external-integration adapter.

    Subclasses implement `_fetch_mock` (always available, no network/API key
    required) and optionally `_fetch_real` (requires a live API key; raises
    NotImplementedError by default until a real integration is wired up).
    """

    name: str = "unknown"

    def __init__(self, mode: AdapterMode = "mock") -> None:
        self.mode = mode

    async def fetch(self, **params: Any) -> AdapterResult:
        if self.mode == "real":
            return await self._fetch_real(**params)
        return await self._fetch_mock(**params)

    @abstractmethod
    async def _fetch_mock(self, **params: Any) -> AdapterResult: ...

    async def _fetch_real(self, **params: Any) -> AdapterResult:
        raise NotImplementedError(
            f"{self.name} adapter has no 'real' backend wired up in this prototype. "
            f"Set {self.name.upper()}_MODE=mock or implement _fetch_real()."
        )

    async def health_check(self) -> bool:
        return True
