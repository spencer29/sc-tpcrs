"""ISO/IEC 27001:2022 Annex A -- all 93 controls.

The 2022 revision reorganised Annex A into four themes: Organizational (A.5,
37 controls), People (A.6, 8), Physical (A.7, 14) and Technological (A.8, 34).
Reference IDs and titles are the published ones.
"""

from __future__ import annotations

from . import ControlSpec, FRAMEWORK_ISO_27001

FW = FRAMEWORK_ISO_27001


def _c(ref: str, domain: str, title: str, weight: int = 3, tags: tuple[str, ...] = ()) -> ControlSpec:
    return ControlSpec(
        control_id=f"ISO27001-{ref}",
        framework=FW,
        reference=f"A.{ref}",
        domain=domain,
        title=title,
        objective=f"ISO/IEC 27001:2022 Annex A.{ref} -- {title}.",
        weight=weight,
        tags=tags,
    )


_ORG = "Organizational controls (A.5)"
_PEOPLE = "People controls (A.6)"
_PHYSICAL = "Physical controls (A.7)"
_TECH = "Technological controls (A.8)"

CONTROLS: list[ControlSpec] = [
    # --- A.5 Organizational (37) ---
    _c("5.1", _ORG, "Policies for information security", 4, ("governance",)),
    _c("5.2", _ORG, "Information security roles and responsibilities", 4, ("governance",)),
    _c("5.3", _ORG, "Segregation of duties", 3),
    _c("5.4", _ORG, "Management responsibilities", 3, ("governance",)),
    _c("5.5", _ORG, "Contact with authorities", 2),
    _c("5.6", _ORG, "Contact with special interest groups", 2),
    _c("5.7", _ORG, "Threat intelligence", 4, ("threat-intel",)),
    _c("5.8", _ORG, "Information security in project management", 3),
    _c("5.9", _ORG, "Inventory of information and other associated assets", 3, ("asset-mgmt",)),
    _c("5.10", _ORG, "Acceptable use of information and other associated assets", 3, ("asset-mgmt",)),
    _c("5.11", _ORG, "Return of assets", 2, ("asset-mgmt",)),
    _c("5.12", _ORG, "Classification of information", 4, ("data-protection",)),
    _c("5.13", _ORG, "Labelling of information", 3, ("data-protection",)),
    _c("5.14", _ORG, "Information transfer", 3, ("data-protection",)),
    _c("5.15", _ORG, "Access control", 5, ("access-control",)),
    _c("5.16", _ORG, "Identity management", 4, ("access-control",)),
    _c("5.17", _ORG, "Authentication information", 5, ("access-control",)),
    _c("5.18", _ORG, "Access rights", 4, ("access-control",)),
    _c("5.19", _ORG, "Information security in supplier relationships", 5, ("third-party",)),
    _c("5.20", _ORG, "Addressing information security within supplier agreements", 5, ("third-party",)),
    _c("5.21", _ORG, "Managing information security in the ICT supply chain", 5, ("third-party", "supply-chain")),
    _c("5.22", _ORG, "Monitoring, review and change management of supplier services", 4, ("third-party",)),
    _c("5.23", _ORG, "Information security for use of cloud services", 4, ("cloud",)),
    _c("5.24", _ORG, "Information security incident management planning and preparation", 4, ("incident",)),
    _c("5.25", _ORG, "Assessment and decision on information security events", 3, ("incident",)),
    _c("5.26", _ORG, "Response to information security incidents", 4, ("incident",)),
    _c("5.27", _ORG, "Learning from information security incidents", 3, ("incident",)),
    _c("5.28", _ORG, "Collection of evidence", 3, ("incident",)),
    _c("5.29", _ORG, "Information security during disruption", 3, ("resilience",)),
    _c("5.30", _ORG, "ICT readiness for business continuity", 4, ("resilience",)),
    _c("5.31", _ORG, "Legal, statutory, regulatory and contractual requirements", 4, ("compliance",)),
    _c("5.32", _ORG, "Intellectual property rights", 2, ("compliance",)),
    _c("5.33", _ORG, "Protection of records", 3, ("data-protection",)),
    _c("5.34", _ORG, "Privacy and protection of PII", 5, ("privacy", "data-protection")),
    _c("5.35", _ORG, "Independent review of information security", 3, ("assurance",)),
    _c("5.36", _ORG, "Compliance with policies, rules and standards for information security", 3, ("compliance",)),
    _c("5.37", _ORG, "Documented operating procedures", 2),
    # --- A.6 People (8) ---
    _c("6.1", _PEOPLE, "Screening", 3, ("hr",)),
    _c("6.2", _PEOPLE, "Terms and conditions of employment", 2, ("hr",)),
    _c("6.3", _PEOPLE, "Information security awareness, education and training", 4, ("hr", "awareness")),
    _c("6.4", _PEOPLE, "Disciplinary process", 2, ("hr",)),
    _c("6.5", _PEOPLE, "Responsibilities after termination or change of employment", 3, ("hr",)),
    _c("6.6", _PEOPLE, "Confidentiality or non-disclosure agreements", 3, ("hr",)),
    _c("6.7", _PEOPLE, "Remote working", 3, ("remote",)),
    _c("6.8", _PEOPLE, "Information security event reporting", 3, ("incident",)),
    # --- A.7 Physical (14) ---
    _c("7.1", _PHYSICAL, "Physical security perimeters", 3, ("physical",)),
    _c("7.2", _PHYSICAL, "Physical entry", 3, ("physical",)),
    _c("7.3", _PHYSICAL, "Securing offices, rooms and facilities", 2, ("physical",)),
    _c("7.4", _PHYSICAL, "Physical security monitoring", 3, ("physical",)),
    _c("7.5", _PHYSICAL, "Protecting against physical and environmental threats", 2, ("physical",)),
    _c("7.6", _PHYSICAL, "Working in secure areas", 2, ("physical",)),
    _c("7.7", _PHYSICAL, "Clear desk and clear screen", 2, ("physical",)),
    _c("7.8", _PHYSICAL, "Equipment siting and protection", 2, ("physical",)),
    _c("7.9", _PHYSICAL, "Security of assets off-premises", 3, ("physical", "asset-mgmt")),
    _c("7.10", _PHYSICAL, "Storage media", 3, ("physical", "data-protection")),
    _c("7.11", _PHYSICAL, "Supporting utilities", 2, ("physical",)),
    _c("7.12", _PHYSICAL, "Cabling security", 2, ("physical",)),
    _c("7.13", _PHYSICAL, "Equipment maintenance", 2, ("physical",)),
    _c("7.14", _PHYSICAL, "Secure disposal or re-use of equipment", 3, ("physical", "data-protection")),
    # --- A.8 Technological (34) ---
    _c("8.1", _TECH, "User endpoint devices", 3, ("endpoint",)),
    _c("8.2", _TECH, "Privileged access rights", 5, ("access-control",)),
    _c("8.3", _TECH, "Information access restriction", 4, ("access-control",)),
    _c("8.4", _TECH, "Access to source code", 3, ("secure-dev",)),
    _c("8.5", _TECH, "Secure authentication", 5, ("access-control",)),
    _c("8.6", _TECH, "Capacity management", 2),
    _c("8.7", _TECH, "Protection against malware", 4, ("malware",)),
    _c("8.8", _TECH, "Management of technical vulnerabilities", 5, ("vuln-mgmt",)),
    _c("8.9", _TECH, "Configuration management", 3, ("hardening",)),
    _c("8.10", _TECH, "Information deletion", 3, ("data-protection",)),
    _c("8.11", _TECH, "Data masking", 3, ("data-protection",)),
    _c("8.12", _TECH, "Data leakage prevention", 4, ("data-protection",)),
    _c("8.13", _TECH, "Information backup", 4, ("resilience",)),
    _c("8.14", _TECH, "Redundancy of information processing facilities", 3, ("resilience",)),
    _c("8.15", _TECH, "Logging", 4, ("monitoring",)),
    _c("8.16", _TECH, "Monitoring activities", 4, ("monitoring",)),
    _c("8.17", _TECH, "Clock synchronization", 2, ("monitoring",)),
    _c("8.18", _TECH, "Use of privileged utility programs", 3, ("access-control",)),
    _c("8.19", _TECH, "Installation of software on operational systems", 3, ("hardening",)),
    _c("8.20", _TECH, "Networks security", 4, ("network",)),
    _c("8.21", _TECH, "Security of network services", 3, ("network",)),
    _c("8.22", _TECH, "Segregation of networks", 3, ("network",)),
    _c("8.23", _TECH, "Web filtering", 2, ("network",)),
    _c("8.24", _TECH, "Use of cryptography", 5, ("crypto",)),
    _c("8.25", _TECH, "Secure development life cycle", 4, ("secure-dev",)),
    _c("8.26", _TECH, "Application security requirements", 4, ("secure-dev",)),
    _c("8.27", _TECH, "Secure system architecture and engineering principles", 3, ("secure-dev",)),
    _c("8.28", _TECH, "Secure coding", 4, ("secure-dev",)),
    _c("8.29", _TECH, "Security testing in development and acceptance", 4, ("secure-dev",)),
    _c("8.30", _TECH, "Outsourced development", 3, ("secure-dev", "third-party")),
    _c("8.31", _TECH, "Separation of development, test and production environments", 3, ("secure-dev",)),
    _c("8.32", _TECH, "Change management", 3, ("secure-dev",)),
    _c("8.33", _TECH, "Test information", 2, ("secure-dev",)),
    _c("8.34", _TECH, "Protection of information systems during audit testing", 2, ("assurance",)),
]
