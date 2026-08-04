"""NDPR 2019 / NDPA 2023 -- Nigeria Data Protection Regulation and Act.

Controls are derived from the principles and obligations of the NDPR (2019,
issued by NITDA) and the Nigeria Data Protection Act 2023 (which established
the Nigeria Data Protection Commission, NDPC). References use an "NDPR"/"NDPA"
prefix with the relevant principle/section. This is the domestic regime a
Nigerian fintech's data-processing third parties must satisfy.
"""

from __future__ import annotations

from . import ControlSpec, FRAMEWORK_NDPR

FW = FRAMEWORK_NDPR

_PRINCIPLES = "Data-processing principles"
_LAWFUL = "Lawful basis and consent"
_RIGHTS = "Data-subject rights"
_GOV = "Governance and accountability"
_SECURITY = "Security and breach"
_TRANSFER = "Cross-border transfer"
_THIRD_PARTY = "Processors and third parties"


def _c(ref: str, domain: str, title: str, weight: int = 3, tags: tuple[str, ...] = ()) -> ControlSpec:
    return ControlSpec(
        control_id=f"NDPR-{ref}",
        framework=FW,
        reference=ref,
        domain=domain,
        title=title,
        objective=f"NDPR/NDPA obligation ({ref}) -- {title}.",
        weight=weight,
        tags=tags,
    )


CONTROLS: list[ControlSpec] = [
    # Principles
    _c("NDPR-2.1(a)", _PRINCIPLES, "Personal data is collected and processed lawfully, fairly and transparently", 4, ("privacy",)),
    _c("NDPR-2.1(b)", _PRINCIPLES, "Personal data is collected for specified, explicit and legitimate purposes", 4, ("privacy",)),
    _c("NDPR-2.1(c)", _PRINCIPLES, "Data processed is adequate, relevant and limited to what is necessary (minimisation)", 4, ("privacy",)),
    _c("NDPA-24(d)", _PRINCIPLES, "Personal data is accurate and, where necessary, kept up to date", 3, ("privacy",)),
    _c("NDPA-24(e)", _PRINCIPLES, "Personal data is retained no longer than necessary for the purpose (storage limitation)", 4, ("privacy", "data-protection")),
    # Lawful basis and consent
    _c("NDPR-2.2", _LAWFUL, "A valid lawful basis exists for every processing activity", 5, ("privacy",)),
    _c("NDPR-2.3", _LAWFUL, "Consent is freely given, specific, informed and unambiguous, and is documented", 5, ("privacy",)),
    _c("NDPR-2.4", _LAWFUL, "Consent can be withdrawn as easily as it was given", 3, ("privacy",)),
    _c("NDPA-30", _LAWFUL, "Additional safeguards apply to processing sensitive personal data", 4, ("privacy",)),
    _c("NDPA-31", _LAWFUL, "Special protection is applied to the personal data of children", 4, ("privacy",)),
    # Data-subject rights
    _c("NDPR-3.1(a)", _RIGHTS, "Right of access: data subjects can obtain confirmation and a copy of their data", 4, ("privacy",)),
    _c("NDPR-3.1(b)", _RIGHTS, "Right to rectification of inaccurate or incomplete personal data", 3, ("privacy",)),
    _c("NDPR-3.1(c)", _RIGHTS, "Right to erasure / to be forgotten is supported", 4, ("privacy",)),
    _c("NDPR-3.1(d)", _RIGHTS, "Right to restrict and object to processing is supported", 3, ("privacy",)),
    _c("NDPR-3.1(e)", _RIGHTS, "Right to data portability in a structured, machine-readable format", 3, ("privacy",)),
    _c("NDPA-37", _RIGHTS, "Rights regarding automated decision-making and profiling are honoured", 3, ("privacy",)),
    # Governance and accountability
    _c("NDPR-4.1", _GOV, "A conspicuous, NDPR-conformant privacy policy is published", 3, ("governance", "privacy")),
    _c("NDPA-32", _GOV, "A qualified Data Protection Officer (DPO) is designated", 4, ("governance",)),
    _c("NDPR-4.2", _GOV, "Records of processing activities (RoPA) are maintained", 3, ("governance",)),
    _c("NDPA-28", _GOV, "A Data Protection Impact Assessment is conducted for high-risk processing", 4, ("governance", "risk")),
    _c("NDPR-4.3", _GOV, "An annual data-protection audit is filed with the regulator (for major data controllers)", 3, ("assurance",)),
    _c("NDPA-44", _GOV, "The entity registers with the NDPC as a data controller/processor of major importance", 3, ("governance",)),
    # Security and breach
    _c("NDPR-2.6", _SECURITY, "Appropriate technical and organisational security measures protect personal data", 5, ("data-protection",)),
    _c("NDPA-39", _SECURITY, "Personal-data breaches are notified to the NDPC within 72 hours", 5, ("incident", "privacy")),
    _c("NDPA-39(2)", _SECURITY, "Affected data subjects are notified of high-risk breaches without undue delay", 4, ("incident", "privacy")),
    # Cross-border transfer
    _c("NDPR-2.11", _TRANSFER, "Cross-border transfers occur only to jurisdictions with adequate protection or safeguards", 4, ("privacy", "cloud")),
    _c("NDPA-41", _TRANSFER, "Transfers rely on an adequacy decision, binding instrument or a lawful derogation", 4, ("privacy",)),
    # Processors and third parties
    _c("NDPR-2.7", _THIRD_PARTY, "A written data-processing agreement binds every third-party processor", 5, ("third-party", "privacy")),
    _c("NDPA-29", _THIRD_PARTY, "Processors provide sufficient guarantees of compliant, secure processing", 5, ("third-party",)),
    _c("NDPA-29(3)", _THIRD_PARTY, "Sub-processor engagement requires prior authorisation and equivalent obligations", 4, ("third-party",)),
]
