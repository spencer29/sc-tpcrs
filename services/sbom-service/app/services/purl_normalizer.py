"""PURL normalisation pre-processor (Module 3 requirement).

Every component the pipeline stores must have a canonical Package URL (purl)
so CVE cross-referencing and the Neo4j graph key on a single stable identifier.
Real-world SBOMs are messy: many components ship without a purl at all, or with
an inconsistently-cased/typed one. This module:

  1. Parses an existing purl when present (packageurl-python), re-canonicalising
     it so `pkg:NPM/Left-Pad@1.0.0` and `pkg:npm/left-pad@1.0.0` collapse.
  2. SYNTHESISES a purl from name+version+ecosystem when absent, and flags the
     component (`synthesised=True`) so the SBOM is marked for manual review.
  3. Maps common SBOM ecosystem/type spellings to purl `type` values.

Returns a NormalisedComponent the parsers and cve_scanner both consume.
"""

from __future__ import annotations

from dataclasses import dataclass

from packageurl import PackageURL

# SBOM "type"/ecosystem spellings -> canonical purl type.
_ECOSYSTEM_TO_PURL_TYPE = {
    "npm": "npm",
    "node": "npm",
    "javascript": "npm",
    "pypi": "pypi",
    "python": "pypi",
    "pip": "pypi",
    "maven": "maven",
    "java": "maven",
    "gem": "gem",
    "ruby": "gem",
    "golang": "golang",
    "go": "golang",
    "cargo": "cargo",
    "rust": "cargo",
    "nuget": "nuget",
    "dotnet": "nuget",
    "composer": "composer",
    "php": "composer",
    "deb": "deb",
    "rpm": "rpm",
    "apk": "apk",
    "docker": "docker",
    "oci": "oci",
    "generic": "generic",
    "library": "generic",
    "application": "generic",
    "framework": "generic",
}


@dataclass
class NormalisedComponent:
    name: str
    version: str
    ecosystem: str
    purl: str
    synthesised: bool
    cpe: str | None = None
    file_hash: str | None = None


def _purl_type_for(ecosystem: str) -> str:
    return _ECOSYSTEM_TO_PURL_TYPE.get((ecosystem or "").strip().lower(), "generic")


def _ecosystem_from_purl_type(purl_type: str) -> str:
    # Inverse mapping, best-effort: the mock NVD adapter takes `ecosystem`, and
    # we want it to look like a real ecosystem name, not the purl type verbatim.
    for eco, ptype in _ECOSYSTEM_TO_PURL_TYPE.items():
        if ptype == purl_type and eco in {"npm", "pypi", "maven", "golang", "cargo", "nuget", "composer"}:
            return eco
    return purl_type


def normalise(
    *,
    name: str,
    version: str | None,
    ecosystem: str | None = None,
    purl: str | None = None,
    cpe: str | None = None,
    file_hash: str | None = None,
) -> NormalisedComponent:
    version = (version or "").strip()
    name = (name or "").strip()

    if purl:
        try:
            parsed = PackageURL.from_string(purl.strip())
            eco = _ecosystem_from_purl_type(parsed.type)
            canonical = PackageURL(
                type=parsed.type,
                namespace=parsed.namespace,
                name=parsed.name,
                version=parsed.version or version or None,
            ).to_string()
            return NormalisedComponent(
                name=parsed.name or name,
                version=parsed.version or version,
                ecosystem=eco,
                purl=canonical,
                synthesised=False,
                cpe=cpe,
                file_hash=file_hash,
            )
        except ValueError:
            # Malformed purl -> fall through to synthesis and flag for review.
            pass

    # Synthesise from name + version + ecosystem.
    purl_type = _purl_type_for(ecosystem or "generic")
    synthesised = PackageURL(type=purl_type, name=name or "unknown", version=version or None).to_string()
    return NormalisedComponent(
        name=name or "unknown",
        version=version,
        ecosystem=_ecosystem_from_purl_type(purl_type),
        purl=synthesised,
        synthesised=True,
        cpe=cpe,
        file_hash=file_hash,
    )
