from __future__ import annotations

import pytest

from sc_tpcrs_common.adapters import kev_adapter, nvd_adapter  # noqa: F401 - register side effects
from sc_tpcrs_common.adapters.registry import get_adapter, registered_keys


def test_registered_keys_include_nvd_and_kev():
    keys = registered_keys()
    assert "nvd" in keys
    assert "kev" in keys


def test_get_adapter_defaults_to_mock_mode(monkeypatch):
    monkeypatch.delenv("NVD_MODE", raising=False)
    adapter = get_adapter("nvd")
    assert adapter.mode == "mock"


def test_get_adapter_respects_env_mode(monkeypatch):
    monkeypatch.setenv("KEV_MODE", "real")
    adapter = get_adapter("kev")
    assert adapter.mode == "real"
    monkeypatch.delenv("KEV_MODE", raising=False)


def test_get_adapter_caches_singleton_per_mode(monkeypatch):
    monkeypatch.delenv("NVD_MODE", raising=False)
    first = get_adapter("nvd")
    second = get_adapter("nvd")
    assert first is second


def test_get_adapter_unknown_key_raises():
    with pytest.raises(KeyError):
        get_adapter("does-not-exist")


@pytest.mark.asyncio
async def test_nvd_mock_fetch_is_deterministic():
    adapter = get_adapter("nvd")
    result_a = await adapter.fetch(component_name="some-lib", version="2.3.4")
    result_b = await adapter.fetch(component_name="some-lib", version="2.3.4")
    assert result_a.data == result_b.data
    assert result_a.is_mock is True
