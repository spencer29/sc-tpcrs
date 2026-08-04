from __future__ import annotations

from app.services.purl_normalizer import normalise


def test_existing_purl_is_canonicalised():
    c = normalise(name="Left-Pad", version="1.0.0", ecosystem="library", purl="pkg:npm/left-pad@1.0.0")
    assert c.synthesised is False
    assert c.purl == "pkg:npm/left-pad@1.0.0"
    assert c.ecosystem == "npm"


def test_missing_purl_is_synthesised_and_flagged():
    c = normalise(name="mypkg", version="2.3.4", ecosystem="python", purl=None)
    assert c.synthesised is True
    assert c.purl == "pkg:pypi/mypkg@2.3.4"
    assert c.ecosystem == "pypi"


def test_malformed_purl_falls_back_to_synthesis():
    c = normalise(name="thing", version="1.0", ecosystem="npm", purl="not-a-valid-purl")
    assert c.synthesised is True
    assert c.purl.startswith("pkg:npm/")


def test_unknown_ecosystem_defaults_to_generic():
    c = normalise(name="blob", version="9", ecosystem="somethingweird", purl=None)
    assert c.purl == "pkg:generic/blob@9"


def test_empty_name_becomes_unknown():
    c = normalise(name="", version="", ecosystem=None, purl=None)
    assert c.name == "unknown"
    assert c.purl.startswith("pkg:generic/unknown")
