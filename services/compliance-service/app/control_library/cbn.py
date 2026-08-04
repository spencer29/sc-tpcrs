"""CBN Risk-Based Cybersecurity Framework and Guidelines.

The Central Bank of Nigeria issued a Risk-Based Cybersecurity Framework and
Guidelines for Deposit Money Banks & Payment Service Providers (and a parallel
one for OFIs). Its principal chapters are captured here as controls -- these
are the domestic regulator's cyber expectations that a Nigerian fintech
cascades onto its critical third parties. References use a "CBN" prefix.
"""

from __future__ import annotations

from . import ControlSpec, FRAMEWORK_CBN

FW = FRAMEWORK_CBN

_GOV = "Governance and oversight"
_RISK = "Cyber risk management"
_RESILIENCE = "Resilience and continuity"
_OPS = "Cybersecurity operations"
_CTI = "Threat intelligence and metrics"
_COMPLIANCE = "Compliance and assurance"


def _c(ref: str, domain: str, title: str, weight: int = 3, tags: tuple[str, ...] = ()) -> ControlSpec:
    return ControlSpec(
        control_id=f"CBN-{ref}",
        framework=FW,
        reference=ref,
        domain=domain,
        title=title,
        objective=f"CBN Cybersecurity Framework ({ref}) -- {title}.",
        weight=weight,
        tags=tags,
    )


CONTROLS: list[ControlSpec] = [
    # Governance
    _c("2.1", _GOV, "The board and senior management provide cybersecurity oversight and direction", 4, ("governance",)),
    _c("2.2", _GOV, "A board-approved cybersecurity strategy and policy are established and reviewed", 4, ("governance",)),
    _c("2.3", _GOV, "A Chief Information Security Officer (CISO) is appointed with a clear mandate", 4, ("governance",)),
    _c("2.4", _GOV, "Cybersecurity roles, responsibilities and reporting lines are defined", 3, ("governance",)),
    _c("2.5", _GOV, "A cybersecurity budget and adequate resources are allocated", 2, ("governance",)),
    # Cyber risk management
    _c("3.1", _RISK, "A cybersecurity risk-management framework identifies, assesses and treats cyber risk", 5, ("risk",)),
    _c("3.2", _RISK, "Information assets are identified, classified and assigned risk owners", 4, ("asset-mgmt", "risk")),
    _c("3.3", _RISK, "Third-party and outsourcing cyber risks are assessed and managed", 5, ("third-party", "risk")),
    _c("3.4", _RISK, "A cyber-risk appetite and tolerance are defined and monitored", 3, ("risk",)),
    _c("3.5", _RISK, "Risk assessments are performed before deploying new products, channels or technologies", 3, ("risk",)),
    # Cybersecurity operations
    _c("4.1", _OPS, "Preventive controls (access management, hardening, segmentation) are implemented", 5, ("access-control", "hardening")),
    _c("4.2", _OPS, "Multi-factor authentication protects critical systems and privileged access", 5, ("access-control", "mfa")),
    _c("4.3", _OPS, "A vulnerability- and patch-management programme is operated", 5, ("vuln-mgmt",)),
    _c("4.4", _OPS, "Secure configuration and change-management processes are enforced", 3, ("hardening",)),
    _c("4.5", _OPS, "Data protection and encryption controls safeguard sensitive data", 5, ("crypto", "data-protection")),
    _c("4.6", _OPS, "Security event logging and continuous monitoring (SOC/SIEM) are in place", 4, ("monitoring",)),
    _c("4.7", _OPS, "Anti-malware and email/endpoint protection controls are deployed", 3, ("malware",)),
    # Resilience and incident response
    _c("5.1", _RESILIENCE, "A cyber incident-response plan is documented, tested and maintained", 5, ("incident",)),
    _c("5.2", _RESILIENCE, "Cybersecurity incidents are reported to the CBN within the mandated timeline", 5, ("incident",)),
    _c("5.3", _RESILIENCE, "Business continuity and disaster-recovery plans address cyber disruption", 4, ("resilience",)),
    _c("5.4", _RESILIENCE, "Backups are maintained, protected and periodically restore-tested", 4, ("resilience",)),
    # Threat intelligence and metrics
    _c("6.1", _CTI, "Cyber threat intelligence is gathered and acted upon", 3, ("threat-intel",)),
    _c("6.2", _CTI, "The entity participates in sector threat-information sharing", 2, ("threat-intel",)),
    _c("6.3", _CTI, "Cybersecurity metrics and KRIs are reported to management and the board", 3, ("governance",)),
    _c("6.4", _CTI, "Regular security awareness and phishing-simulation training is conducted", 3, ("awareness",)),
    # Compliance and assurance
    _c("7.1", _COMPLIANCE, "Periodic cybersecurity self-assessment and maturity assessment are performed", 3, ("assurance",)),
    _c("7.2", _COMPLIANCE, "Independent cybersecurity audits and penetration tests are conducted", 4, ("assurance", "vuln-mgmt")),
    _c("7.3", _COMPLIANCE, "A compliance return on the framework is rendered to the CBN as required", 3, ("compliance",)),
    _c("7.4", _COMPLIANCE, "Regulatory findings and remediation actions are tracked to closure", 3, ("compliance",)),
]
