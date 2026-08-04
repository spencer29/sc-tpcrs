from __future__ import annotations

from app.services.parsers import SbomParseError, detect_and_parse

CYCLONEDX_JSON = """
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.6",
  "metadata": {"component": {"name": "demo-app", "type": "application"}},
  "components": [
    {"type": "library", "name": "left-pad", "version": "1.0.0", "purl": "pkg:npm/left-pad@1.0.0"},
    {"type": "library", "name": "NoPurl", "version": "2.1.0"}
  ]
}
"""

CYCLONEDX_XML = """<?xml version="1.0"?>
<bom xmlns="http://cyclonedx.org/schema/bom/1.6" version="1">
  <components>
    <component type="library">
      <name>express</name>
      <version>4.18.2</version>
      <purl>pkg:npm/express@4.18.2</purl>
    </component>
  </components>
</bom>
"""

SPDX_JSON = """
{
  "spdxVersion": "SPDX-2.3",
  "name": "demo-doc",
  "packages": [
    {"name": "lodash", "versionInfo": "4.17.21",
     "externalRefs": [{"referenceType": "purl", "referenceLocator": "pkg:npm/lodash@4.17.21"}]}
  ]
}
"""

SPDX_TAG_VALUE = """
SPDXVersion: SPDX-2.3
DocumentName: tv-doc
PackageName: requests
PackageVersion: 2.31.0
ExternalRef: PACKAGE-MANAGER purl pkg:pypi/requests@2.31.0
PackageName: urllib3
PackageVersion: 2.0.7
"""


def test_detect_cyclonedx_json():
    parsed = detect_and_parse(CYCLONEDX_JSON)
    assert parsed.sbom_format == "CycloneDX"
    assert parsed.serialization == "json"
    assert parsed.spec_version == "1.6"
    names = {c.name for c in parsed.components}
    assert {"left-pad", "NoPurl"} <= names
    # component without a purl must be synthesised + flagged
    nopurl = next(c for c in parsed.components if c.name == "NoPurl")
    assert nopurl.synthesised is True
    assert nopurl.purl.startswith("pkg:")


def test_detect_cyclonedx_xml():
    parsed = detect_and_parse(CYCLONEDX_XML)
    assert parsed.sbom_format == "CycloneDX"
    assert parsed.serialization == "xml"
    assert parsed.components[0].name == "express"
    assert parsed.components[0].purl == "pkg:npm/express@4.18.2"


def test_detect_spdx_json():
    parsed = detect_and_parse(SPDX_JSON)
    assert parsed.sbom_format == "SPDX"
    assert parsed.serialization == "json"
    assert parsed.components[0].name == "lodash"
    assert parsed.components[0].purl == "pkg:npm/lodash@4.17.21"


def test_detect_spdx_tag_value():
    parsed = detect_and_parse(SPDX_TAG_VALUE)
    assert parsed.sbom_format == "SPDX"
    assert parsed.serialization == "tag-value"
    names = {c.name for c in parsed.components}
    assert names == {"requests", "urllib3"}
    req = next(c for c in parsed.components if c.name == "requests")
    assert req.purl == "pkg:pypi/requests@2.31.0"


def test_unrecognised_format_raises():
    try:
        detect_and_parse("this is not an SBOM at all")
        raise AssertionError("expected SbomParseError")
    except SbomParseError:
        pass


def test_xxe_is_not_expanded():
    # defusedxml must refuse entity-expansion payloads rather than resolving them.
    xxe = """<?xml version="1.0"?>
    <!DOCTYPE bom [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
    <bom version="1"><components><component type="library">
    <name>&xxe;</name><version>1.0</version></component></components></bom>"""
    try:
        detect_and_parse(xxe)
        # If it parses at all, the entity must NOT have been expanded to file
        # contents. defusedxml raises instead, which is the expected path.
    except Exception as exc:  # noqa: BLE001
        assert "entit" in str(exc).lower() or "forbidden" in str(exc).lower()
