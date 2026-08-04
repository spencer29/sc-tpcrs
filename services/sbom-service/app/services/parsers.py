"""SBOM parsers: CycloneDX (JSON/XML) and SPDX (JSON/tag-value).

Each parser returns a `ParsedSbom` of NormalisedComponent plus the detected
format/spec-version/serialization and any external-reference URLs (which the
ingest pipeline runs past the SSRF guard). Parsing is dependency-light and
XXE-safe (defusedxml) -- we read the fields the pipeline needs rather than
fully validating against the CycloneDX/SPDX schemas, which is the pragmatic
"closest faithful equivalent" the blueprint allows.

`detect_and_parse` sniffs the format so callers can accept an opaque SBOM blob,
matching `POST /sbom/ingest` taking raw `content`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from defusedxml.ElementTree import fromstring as safe_xml_fromstring

from .purl_normalizer import NormalisedComponent, normalise


@dataclass
class ParsedSbom:
    sbom_format: str
    serialization: str
    spec_version: str | None
    document_name: str | None
    components: list[NormalisedComponent]
    external_refs: list[str] = field(default_factory=list)


class SbomParseError(ValueError):
    """Raised when content cannot be recognised as any supported SBOM format."""


# --------------------------------------------------------------- CycloneDX --
def _hash_from_cyclonedx(comp: dict) -> str | None:
    for h in comp.get("hashes", []) or []:
        if h.get("content"):
            return h["content"]
    return None


def parse_cyclonedx_json(text: str) -> ParsedSbom:
    doc = json.loads(text)
    components: list[NormalisedComponent] = []
    refs: list[str] = []

    for comp in doc.get("components", []) or []:
        components.append(
            normalise(
                name=comp.get("name", ""),
                version=comp.get("version"),
                ecosystem=comp.get("type"),
                purl=comp.get("purl"),
                cpe=comp.get("cpe"),
                file_hash=_hash_from_cyclonedx(comp),
            )
        )
        for ref in comp.get("externalReferences", []) or []:
            if ref.get("url"):
                refs.append(ref["url"])

    for ref in doc.get("externalReferences", []) or []:
        if ref.get("url"):
            refs.append(ref["url"])

    name = (doc.get("metadata", {}) or {}).get("component", {}).get("name")
    return ParsedSbom(
        sbom_format="CycloneDX",
        serialization="json",
        spec_version=str(doc.get("specVersion")) if doc.get("specVersion") else None,
        document_name=name,
        components=components,
        external_refs=refs,
    )


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_cyclonedx_xml(text: str) -> ParsedSbom:
    root = safe_xml_fromstring(text)
    spec_version = root.attrib.get("version") or None
    components: list[NormalisedComponent] = []
    refs: list[str] = []

    for elem in root.iter():
        if _strip_ns(elem.tag) != "component":
            continue
        fields: dict[str, str] = {}
        cpe = None
        purl = None
        file_hash = None
        for child in elem:
            tag = _strip_ns(child.tag)
            if tag in ("name", "version") and child.text:
                fields[tag] = child.text.strip()
            elif tag == "cpe" and child.text:
                cpe = child.text.strip()
            elif tag == "purl" and child.text:
                purl = child.text.strip()
            elif tag == "hashes":
                for h in child:
                    if _strip_ns(h.tag) == "hash" and h.text:
                        file_hash = h.text.strip()
                        break
            elif tag == "externalReferences":
                for r in child.iter():
                    if _strip_ns(r.tag) == "url" and r.text:
                        refs.append(r.text.strip())
        components.append(
            normalise(
                name=fields.get("name", ""),
                version=fields.get("version"),
                ecosystem=elem.attrib.get("type"),
                purl=purl,
                cpe=cpe,
                file_hash=file_hash,
            )
        )

    return ParsedSbom(
        sbom_format="CycloneDX",
        serialization="xml",
        spec_version=spec_version,
        document_name=None,
        components=components,
        external_refs=refs,
    )


# -------------------------------------------------------------------- SPDX --
_SPDX_PURL_TYPE_HINT = re.compile(r"pkg:(?P<type>[a-zA-Z0-9.+-]+)/")


def _spdx_purl_and_cpe(pkg: dict) -> tuple[str | None, str | None]:
    purl = None
    cpe = None
    for ref in pkg.get("externalRefs", []) or []:
        ref_type = (ref.get("referenceType") or "").lower()
        locator = ref.get("referenceLocator")
        if ref_type == "purl" and locator:
            purl = locator
        elif ref_type.startswith("cpe") and locator:
            cpe = locator
    return purl, cpe


def parse_spdx_json(text: str) -> ParsedSbom:
    doc = json.loads(text)
    components: list[NormalisedComponent] = []
    refs: list[str] = []

    for pkg in doc.get("packages", []) or []:
        purl, cpe = _spdx_purl_and_cpe(pkg)
        download = pkg.get("downloadLocation")
        if download and download not in ("NOASSERTION", "NONE"):
            refs.append(download)
        components.append(
            normalise(
                name=pkg.get("name", ""),
                version=pkg.get("versionInfo"),
                ecosystem=None,  # SPDX has no ecosystem field; purl type drives it
                purl=purl,
                cpe=cpe,
            )
        )

    return ParsedSbom(
        sbom_format="SPDX",
        serialization="json",
        spec_version=doc.get("spdxVersion"),
        document_name=doc.get("name"),
        components=components,
        external_refs=refs,
    )


def parse_spdx_tag_value(text: str) -> ParsedSbom:
    """SPDX tag-value: line-oriented `Tag: value`. A new PackageName starts a
    new package record; PackageVersion / ExternalRef / PackageDownloadLocation
    attach to the current one."""
    components: list[NormalisedComponent] = []
    refs: list[str] = []
    doc_name: str | None = None
    spec_version: str | None = None

    cur: dict | None = None

    def flush() -> None:
        nonlocal cur
        if cur is not None:
            components.append(
                normalise(
                    name=cur.get("name", ""),
                    version=cur.get("version"),
                    ecosystem=None,
                    purl=cur.get("purl"),
                    cpe=cur.get("cpe"),
                )
            )
        cur = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        tag, _, value = line.partition(":")
        tag = tag.strip()
        value = value.strip()

        if tag == "SPDXVersion":
            spec_version = value
        elif tag == "DocumentName":
            doc_name = value
        elif tag == "PackageName":
            flush()
            cur = {"name": value}
        elif cur is not None and tag == "PackageVersion":
            cur["version"] = value
        elif cur is not None and tag == "PackageDownloadLocation":
            if value not in ("NOASSERTION", "NONE"):
                refs.append(value)
        elif cur is not None and tag == "ExternalRef":
            # e.g. "PACKAGE-MANAGER purl pkg:npm/left-pad@1.0.0"
            parts = value.split()
            if len(parts) >= 3:
                ref_type, locator = parts[1].lower(), parts[2]
                if ref_type == "purl":
                    cur["purl"] = locator
                elif ref_type.startswith("cpe"):
                    cur["cpe"] = locator
    flush()

    return ParsedSbom(
        sbom_format="SPDX",
        serialization="tag-value",
        spec_version=spec_version,
        document_name=doc_name,
        components=components,
        external_refs=refs,
    )


# ---------------------------------------------------------------- dispatch --
def detect_and_parse(content: str, *, format_hint: str | None = None) -> ParsedSbom:
    stripped = content.lstrip()

    # JSON (both CycloneDX and SPDX) -----------------------------------------
    if stripped.startswith("{"):
        try:
            doc = json.loads(content)
        except json.JSONDecodeError as exc:
            raise SbomParseError(f"content looks like JSON but failed to parse: {exc}") from exc
        if "bomFormat" in doc or doc.get("$schema", "").find("cyclonedx") != -1 or "components" in doc:
            return parse_cyclonedx_json(content)
        if "spdxVersion" in doc or "packages" in doc or "SPDXID" in doc:
            return parse_spdx_json(content)
        # Ambiguous JSON: honour hint, else default to CycloneDX.
        if format_hint and format_hint.upper() == "SPDX":
            return parse_spdx_json(content)
        return parse_cyclonedx_json(content)

    # XML (CycloneDX) --------------------------------------------------------
    if stripped.startswith("<"):
        return parse_cyclonedx_xml(content)

    # SPDX tag-value ---------------------------------------------------------
    if "SPDXVersion" in content or "PackageName" in content or "SPDXID" in content:
        return parse_spdx_tag_value(content)

    raise SbomParseError("Unrecognised SBOM format (expected CycloneDX JSON/XML or SPDX JSON/tag-value).")
