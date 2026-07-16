"""Vendor risk tiering: overall_tier = max(3 dimensions), by ordinal rank.

Pure function, independently unit-tested against every boundary combination
-- see tests/test_tiering.py.
"""

from __future__ import annotations

from typing import Literal

Tier = Literal["Critical", "High", "Medium", "Low"]

_ORDER: dict[str, int] = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}
_REVERSE: dict[int, Tier] = {v: k for k, v in _ORDER.items()}  # type: ignore[misc]


def compute_tier(data_access_scope: str, service_criticality: str, integration_depth: str) -> Tier:
    for value in (data_access_scope, service_criticality, integration_depth):
        if value not in _ORDER:
            raise ValueError(f"Invalid tier dimension value: {value!r}")
    rank = max(_ORDER[data_access_scope], _ORDER[service_criticality], _ORDER[integration_depth])
    return _REVERSE[rank]
