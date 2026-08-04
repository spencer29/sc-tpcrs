"""SOC 2 -- AICPA Trust Services Criteria (2017, revised 2022).

Covers the Common Criteria (CC1-CC9, which map to the Security category / COSO
principles) plus the additional-category criteria for Availability (A),
Confidentiality (C), Processing Integrity (PI) and Privacy (P). Reference IDs
are the published TSC point-of-focus numbering (e.g. "CC6.1", "P3.2").
"""

from __future__ import annotations

from . import ControlSpec, FRAMEWORK_SOC2

FW = FRAMEWORK_SOC2

_CC = "Common Criteria (Security)"
_AVAIL = "Availability"
_CONF = "Confidentiality"
_PI = "Processing Integrity"
_PRIV = "Privacy"


def _c(ref: str, domain: str, title: str, weight: int = 3, tags: tuple[str, ...] = ()) -> ControlSpec:
    return ControlSpec(
        control_id=f"SOC2-{ref}",
        framework=FW,
        reference=ref,
        domain=domain,
        title=title,
        objective=f"SOC 2 Trust Services Criteria {ref} -- {title}.",
        weight=weight,
        tags=tags,
    )


CONTROLS: list[ControlSpec] = [
    # CC1 -- Control Environment
    _c("CC1.1", _CC, "The entity demonstrates a commitment to integrity and ethical values", 3, ("governance",)),
    _c("CC1.2", _CC, "The board exercises oversight of internal control", 3, ("governance",)),
    _c("CC1.3", _CC, "Management establishes structures, reporting lines and authorities", 3, ("governance",)),
    _c("CC1.4", _CC, "The entity demonstrates a commitment to attract, develop and retain competent people", 2, ("hr",)),
    _c("CC1.5", _CC, "The entity holds individuals accountable for internal control responsibilities", 3, ("governance",)),
    # CC2 -- Communication and Information
    _c("CC2.1", _CC, "The entity obtains or generates relevant, quality information", 3, ("governance",)),
    _c("CC2.2", _CC, "The entity internally communicates information supporting internal control", 3, ("governance",)),
    _c("CC2.3", _CC, "The entity communicates with external parties on internal-control matters", 3, ("third-party",)),
    # CC3 -- Risk Assessment
    _c("CC3.1", _CC, "The entity specifies objectives to enable identification of risks", 3, ("risk",)),
    _c("CC3.2", _CC, "The entity identifies and analyzes risks to achieving its objectives", 4, ("risk",)),
    _c("CC3.3", _CC, "The entity considers the potential for fraud in assessing risks", 3, ("risk",)),
    _c("CC3.4", _CC, "The entity identifies and assesses changes that could impact internal control", 3, ("risk",)),
    # CC4 -- Monitoring Activities
    _c("CC4.1", _CC, "The entity selects and performs ongoing and separate control evaluations", 3, ("assurance",)),
    _c("CC4.2", _CC, "The entity evaluates and communicates internal-control deficiencies", 3, ("assurance",)),
    # CC5 -- Control Activities
    _c("CC5.1", _CC, "The entity selects and develops control activities that mitigate risks", 3, ("governance",)),
    _c("CC5.2", _CC, "The entity selects and develops general controls over technology", 3, ("governance",)),
    _c("CC5.3", _CC, "The entity deploys control activities through policies and procedures", 3, ("governance",)),
    # CC6 -- Logical and Physical Access Controls
    _c("CC6.1", _CC, "Logical access security software and infrastructure protect information assets", 5, ("access-control",)),
    _c("CC6.2", _CC, "New internal and external users are registered and authorized before access", 4, ("access-control",)),
    _c("CC6.3", _CC, "Access to data and software is authorized, modified and removed based on roles", 4, ("access-control",)),
    _c("CC6.4", _CC, "Physical access to facilities and protected assets is restricted", 3, ("physical",)),
    _c("CC6.5", _CC, "The entity discontinues logical/physical protections only after data disposal", 3, ("data-protection",)),
    _c("CC6.6", _CC, "The entity implements controls to protect against threats from outside its boundaries", 4, ("network",)),
    _c("CC6.7", _CC, "The entity restricts the transmission, movement and removal of information", 4, ("data-protection",)),
    _c("CC6.8", _CC, "The entity implements controls to prevent or detect unauthorized software", 3, ("malware",)),
    # CC7 -- System Operations
    _c("CC7.1", _CC, "The entity uses detection and monitoring to identify configuration changes and vulnerabilities", 4, ("vuln-mgmt", "monitoring")),
    _c("CC7.2", _CC, "The entity monitors system components for anomalies indicative of malicious acts", 4, ("monitoring",)),
    _c("CC7.3", _CC, "The entity evaluates security events to determine whether they are incidents", 4, ("incident",)),
    _c("CC7.4", _CC, "The entity responds to identified security incidents with a defined program", 4, ("incident",)),
    _c("CC7.5", _CC, "The entity identifies, develops and implements recovery from incidents", 3, ("incident", "resilience")),
    # CC8 -- Change Management
    _c("CC8.1", _CC, "The entity authorizes, designs, tests and approves changes before implementation", 4, ("secure-dev",)),
    # CC9 -- Risk Mitigation
    _c("CC9.1", _CC, "The entity identifies, selects and develops risk-mitigation activities", 3, ("risk",)),
    _c("CC9.2", _CC, "The entity assesses and manages risks associated with vendors and business partners", 5, ("third-party",)),
    # Availability
    _c("A1.1", _AVAIL, "The entity maintains and monitors capacity to meet availability commitments", 3, ("resilience",)),
    _c("A1.2", _AVAIL, "The entity provides environmental protections, backup and recovery infrastructure", 4, ("resilience",)),
    _c("A1.3", _AVAIL, "The entity tests recovery-plan procedures supporting system recovery", 3, ("resilience",)),
    # Confidentiality
    _c("C1.1", _CONF, "The entity identifies and maintains confidential information to meet its commitments", 4, ("data-protection",)),
    _c("C1.2", _CONF, "The entity disposes of confidential information to meet its commitments", 3, ("data-protection",)),
    # Processing Integrity
    _c("PI1.1", _PI, "The entity obtains and uses relevant, quality information over processing", 2, ("data-integrity",)),
    _c("PI1.2", _PI, "System inputs are complete and accurate over processing", 3, ("data-integrity",)),
    _c("PI1.3", _PI, "System processing is complete, valid, accurate, timely and authorized", 3, ("data-integrity",)),
    _c("PI1.4", _PI, "System output is complete, accurate and distributed to meet commitments", 2, ("data-integrity",)),
    _c("PI1.5", _PI, "The entity stores inputs and outputs completely, accurately and timely", 2, ("data-integrity",)),
    # Privacy
    _c("P1.1", _PRIV, "Notice about privacy practices is provided to data subjects", 3, ("privacy",)),
    _c("P2.1", _PRIV, "Choice and consent regarding personal information are communicated and obtained", 4, ("privacy",)),
    _c("P3.1", _PRIV, "Personal information is collected consistently with the entity's objectives", 3, ("privacy",)),
    _c("P3.2", _PRIV, "Explicit consent for sensitive personal information is obtained where required", 4, ("privacy",)),
    _c("P4.1", _PRIV, "Personal information is used, retained and disposed of per commitments", 4, ("privacy", "data-protection")),
    _c("P5.1", _PRIV, "Data subjects can access their personal information for review and update", 3, ("privacy",)),
    _c("P6.1", _PRIV, "Personal information is disclosed to third parties only with consent and per commitments", 4, ("privacy", "third-party")),
    _c("P7.1", _PRIV, "The entity collects and maintains accurate, complete and relevant personal information", 2, ("privacy",)),
    _c("P8.1", _PRIV, "A process addresses privacy-related inquiries, complaints and disputes", 3, ("privacy",)),
]
