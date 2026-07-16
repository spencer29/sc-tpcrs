"""Adapter mode-switch registry.

Each adapter module registers its concrete `ExternalAdapter` subclass here via
`@register_adapter("key")`. Callers never construct adapters directly -- they
call `get_adapter("key")`, which reads `{KEY}_MODE` from the environment
(default `"mock"`, matching `.env.example`) and returns a cached singleton
instance for that `(key, mode)` pair. This is the mechanism `adapters/base.py`
docstring refers to.
"""

from __future__ import annotations

import os

from .base import AdapterMode, ExternalAdapter

_ADAPTER_CLASSES: dict[str, type[ExternalAdapter]] = {}
_INSTANCES: dict[tuple[str, str], ExternalAdapter] = {}


def register_adapter(key: str):
    """Class decorator: `@register_adapter("nvd")` on an ExternalAdapter subclass."""

    def _decorator(cls: type[ExternalAdapter]) -> type[ExternalAdapter]:
        _ADAPTER_CLASSES[key] = cls
        return cls

    return _decorator


def _mode_for(key: str) -> AdapterMode:
    raw = os.environ.get(f"{key.upper()}_MODE", "mock").strip().lower()
    return "real" if raw == "real" else "mock"


def get_adapter(key: str) -> ExternalAdapter:
    """Return a cached adapter instance for `key`, honoring `{KEY}_MODE`.

    Raises KeyError if no adapter has been registered under `key` (typically
    means the adapter module was never imported -- import it once at service
    startup so its `@register_adapter` decorator runs).
    """
    if key not in _ADAPTER_CLASSES:
        raise KeyError(
            f"No adapter registered under '{key}'. Import the adapter module "
            f"(e.g. sc_tpcrs_common.adapters.{key}_adapter) before calling get_adapter()."
        )
    mode = _mode_for(key)
    cache_key = (key, mode)
    if cache_key not in _INSTANCES:
        _INSTANCES[cache_key] = _ADAPTER_CLASSES[key](mode=mode)
    return _INSTANCES[cache_key]


def registered_keys() -> list[str]:
    return sorted(_ADAPTER_CLASSES)


async def health_check_all() -> dict[str, bool]:
    """Health-check every registered, already-instantiated adapter.

    Only checks adapters that have actually been used (via get_adapter) so a
    service that only ever touches "nvd" and "kev" doesn't pay to construct
    every adapter type just to report health.
    """
    results: dict[str, bool] = {}
    for (key, _mode), adapter in _INSTANCES.items():
        results[key] = await adapter.health_check()
    return results
