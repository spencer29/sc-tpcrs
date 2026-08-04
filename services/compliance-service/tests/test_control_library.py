from __future__ import annotations

from app.control_library import (
    ALL_FRAMEWORKS,
    all_controls,
    controls_by_id,
    controls_for_framework,
    framework_control_counts,
    library_size,
)


def test_library_is_non_trivial_and_multi_framework():
    # A real, sizeable control library spanning every required framework.
    assert library_size() >= 250
    counts = framework_control_counts()
    for fw in ALL_FRAMEWORKS:
        assert counts[fw] > 0, f"framework {fw} has no controls"


def test_iso27001_has_all_93_annex_a_controls():
    # ISO/IEC 27001:2022 Annex A is exactly 93 controls.
    assert len(controls_for_framework("ISO 27001:2022")) == 93


def test_every_framework_present():
    frameworks = {c.framework for c in all_controls()}
    assert frameworks == set(ALL_FRAMEWORKS)


def test_control_ids_are_globally_unique():
    ids = [c.control_id for c in all_controls()]
    assert len(ids) == len(set(ids))


def test_controls_by_id_lookup_and_weights_in_range():
    index = controls_by_id()
    assert "ISO27001-5.19" in index  # supplier relationships
    assert "PCIDSS-8.4.2" in index  # MFA into the CDE
    for c in all_controls():
        assert 1 <= c.weight <= 5
        assert c.reference
        assert c.title


def test_third_party_and_supplier_controls_exist():
    # Module 5 is about *third-party* compliance -- the library must carry the
    # supplier/third-party controls that matter for that.
    tagged = [c for c in all_controls() if "third-party" in c.tags]
    assert len(tagged) >= 5
