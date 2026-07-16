from __future__ import annotations

import pytest

from app.services.tiering import compute_tier


def test_all_low_yields_low():
    assert compute_tier("Low", "Low", "Low") == "Low"


def test_all_critical_yields_critical():
    assert compute_tier("Critical", "Critical", "Critical") == "Critical"


def test_all_medium_yields_medium():
    assert compute_tier("Medium", "Medium", "Medium") == "Medium"


def test_single_critical_dimension_dominates():
    assert compute_tier("Critical", "Low", "Low") == "Critical"
    assert compute_tier("Low", "Critical", "Low") == "Critical"
    assert compute_tier("Low", "Low", "Critical") == "Critical"


def test_single_high_dominates_over_low_and_medium():
    assert compute_tier("High", "Low", "Medium") == "High"


def test_mixed_dimensions_take_the_max():
    assert compute_tier("Medium", "High", "Low") == "High"
    assert compute_tier("Low", "Medium", "High") == "High"


def test_invalid_dimension_value_raises():
    with pytest.raises(ValueError):
        compute_tier("Nonexistent", "Low", "Low")
