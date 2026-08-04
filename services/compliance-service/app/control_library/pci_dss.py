"""PCI DSS v4.0 -- the 12 principal requirements and their defined
sub-requirements.

Reference IDs follow the v4.0 numbering (e.g. "1.2.5"). Titles paraphrase the
requirement intent at sub-requirement granularity -- enough for gap analysis
and to map a gap back to the source, without reproducing the standard's full
normative text.
"""

from __future__ import annotations

from . import ControlSpec, FRAMEWORK_PCI_DSS

FW = FRAMEWORK_PCI_DSS

_DOMAINS = {
    1: "Req 1: Network security controls",
    2: "Req 2: Secure configurations",
    3: "Req 3: Protect stored account data",
    4: "Req 4: Protect data in transit",
    5: "Req 5: Protect against malicious software",
    6: "Req 6: Secure systems and software",
    7: "Req 7: Restrict access by need to know",
    8: "Req 8: Identify users and authenticate access",
    9: "Req 9: Restrict physical access",
    10: "Req 10: Log and monitor access",
    11: "Req 11: Test security regularly",
    12: "Req 12: Support information security with policies",
}


def _c(ref: str, title: str, weight: int = 3, tags: tuple[str, ...] = ()) -> ControlSpec:
    req = int(ref.split(".")[0])
    return ControlSpec(
        control_id=f"PCIDSS-{ref}",
        framework=FW,
        reference=ref,
        domain=_DOMAINS[req],
        title=title,
        objective=f"PCI DSS v4.0 Requirement {ref} -- {title}.",
        weight=weight,
        tags=tags,
    )


CONTROLS: list[ControlSpec] = [
    # Req 1 -- Network security controls
    _c("1.1.1", "Processes and mechanisms for network security controls are defined", 3, ("network", "governance")),
    _c("1.2.1", "Configuration standards for NSC rulesets are defined and applied", 4, ("network",)),
    _c("1.2.5", "All services, protocols and ports allowed are identified and justified", 4, ("network",)),
    _c("1.3.1", "Inbound traffic to the CDE is restricted to that which is necessary", 5, ("network",)),
    _c("1.3.2", "Outbound traffic from the CDE is restricted to that which is necessary", 4, ("network",)),
    _c("1.4.1", "NSCs are implemented between trusted and untrusted networks", 5, ("network",)),
    _c("1.4.4", "System components storing cardholder data are not directly accessible from untrusted networks", 5, ("network", "data-protection")),
    # Req 2 -- Secure configurations
    _c("2.1.1", "Processes for applying secure configurations are defined", 3, ("hardening",)),
    _c("2.2.1", "Configuration standards are developed, implemented and maintained", 4, ("hardening",)),
    _c("2.2.2", "Vendor default accounts are managed (removed or secured)", 5, ("hardening", "access-control")),
    _c("2.2.4", "Only necessary services, protocols, daemons and functions are enabled", 3, ("hardening",)),
    _c("2.3.1", "Wireless environments are configured securely and defaults changed", 3, ("network",)),
    # Req 3 -- Protect stored account data
    _c("3.1.1", "Processes for protecting stored account data are defined", 4, ("data-protection",)),
    _c("3.2.1", "Storage of account data is kept to a minimum with a retention policy", 5, ("data-protection",)),
    _c("3.3.1", "Sensitive authentication data is not stored after authorization", 5, ("data-protection",)),
    _c("3.4.1", "PAN is masked when displayed; only those with a need see more than the BIN/last-4", 4, ("data-protection",)),
    _c("3.5.1", "PAN is rendered unreadable anywhere it is stored (e.g. strong cryptography)", 5, ("crypto", "data-protection")),
    _c("3.6.1", "Cryptographic keys protecting stored account data are secured", 5, ("crypto",)),
    _c("3.7.1", "Key-management policies and procedures cover the full key lifecycle", 4, ("crypto",)),
    # Req 4 -- Protect data in transit
    _c("4.1.1", "Processes for protecting cardholder data with strong cryptography in transit are defined", 4, ("crypto",)),
    _c("4.2.1", "Strong cryptography protects PAN during transmission over open, public networks", 5, ("crypto", "network")),
    _c("4.2.2", "PAN is secured with strong cryptography whenever sent via end-user messaging technologies", 3, ("crypto",)),
    # Req 5 -- Protect against malicious software
    _c("5.1.1", "Processes for protecting systems from malicious software are defined", 3, ("malware",)),
    _c("5.2.1", "An anti-malware solution is deployed on all applicable system components", 4, ("malware",)),
    _c("5.2.3", "System components not at risk of malware are periodically evaluated", 2, ("malware",)),
    _c("5.3.1", "The anti-malware solution is kept current and performs periodic/continuous scans", 4, ("malware",)),
    _c("5.4.1", "Anti-phishing mechanisms protect personnel against phishing attacks", 4, ("malware", "awareness")),
    # Req 6 -- Secure systems and software
    _c("6.1.1", "Processes for developing and maintaining secure systems are defined", 3, ("secure-dev",)),
    _c("6.2.1", "Bespoke and custom software is developed securely", 4, ("secure-dev",)),
    _c("6.2.4", "Software engineering techniques prevent or mitigate common software attacks", 4, ("secure-dev",)),
    _c("6.3.1", "Security vulnerabilities are identified and assigned a risk ranking", 5, ("vuln-mgmt",)),
    _c("6.3.2", "An inventory of bespoke, custom and third-party software components is maintained", 5, ("vuln-mgmt", "supply-chain")),
    _c("6.3.3", "All system components are protected from known vulnerabilities via security patches", 5, ("vuln-mgmt",)),
    _c("6.4.1", "Public-facing web applications are protected against attacks (review or WAF)", 4, ("secure-dev", "network")),
    _c("6.4.3", "All payment-page scripts are managed, authorized and integrity-assured", 4, ("secure-dev",)),
    _c("6.5.1", "Changes to system components follow established change-control procedures", 3, ("secure-dev",)),
    # Req 7 -- Restrict access by need to know
    _c("7.1.1", "Processes for restricting access by business need to know are defined", 3, ("access-control",)),
    _c("7.2.1", "An access-control model defines access based on business need", 4, ("access-control",)),
    _c("7.2.4", "User accounts and access privileges are reviewed periodically", 4, ("access-control",)),
    _c("7.2.5", "System and application accounts and access are managed and least-privileged", 4, ("access-control",)),
    _c("7.3.1", "Access to system components is managed via an access-control system", 3, ("access-control",)),
    # Req 8 -- Identify and authenticate access
    _c("8.1.1", "Processes for identifying users and authenticating access are defined", 3, ("access-control",)),
    _c("8.2.1", "All users are assigned a unique ID before access to system components", 5, ("access-control",)),
    _c("8.2.2", "Group, shared and generic accounts are only used when necessary and managed", 4, ("access-control",)),
    _c("8.3.1", "Strong authentication for users and administrators is enforced", 5, ("access-control",)),
    _c("8.3.6", "Minimum password/passphrase length and complexity are enforced", 3, ("access-control",)),
    _c("8.4.2", "MFA is implemented for all access into the cardholder data environment", 5, ("access-control", "mfa")),
    _c("8.5.1", "MFA systems are resistant to replay and configured to prevent misuse", 4, ("access-control", "mfa")),
    _c("8.6.1", "Application and system accounts and their authentication factors are managed", 4, ("access-control",)),
    # Req 9 -- Restrict physical access
    _c("9.1.1", "Processes for restricting physical access to cardholder data are defined", 2, ("physical",)),
    _c("9.2.1", "Physical access controls manage entry into facilities and systems in the CDE", 3, ("physical",)),
    _c("9.3.1", "Physical access for personnel and visitors is authorized and managed", 3, ("physical",)),
    _c("9.4.1", "Media with cardholder data is physically secured", 3, ("physical", "data-protection")),
    _c("9.5.1", "POI devices are protected from tampering and unauthorized substitution", 4, ("physical",)),
    # Req 10 -- Log and monitor
    _c("10.1.1", "Processes for logging and monitoring access are defined", 3, ("monitoring",)),
    _c("10.2.1", "Audit logs capture all individual user access to cardholder data and key events", 5, ("monitoring",)),
    _c("10.3.1", "Audit logs are protected from destruction and unauthorized modification", 4, ("monitoring",)),
    _c("10.4.1", "Audit logs are reviewed (including via automated mechanisms) at least daily", 4, ("monitoring",)),
    _c("10.6.1", "Time-synchronization technology keeps system clocks consistent", 2, ("monitoring",)),
    _c("10.7.2", "Failures of critical security control systems are detected, alerted and responded to", 4, ("monitoring", "incident")),
    # Req 11 -- Test security regularly
    _c("11.1.1", "Processes for regularly testing security of systems and networks are defined", 3, ("assurance",)),
    _c("11.2.1", "Authorized and unauthorized wireless access points are managed and tested for", 3, ("network",)),
    _c("11.3.1", "Internal vulnerability scans are performed regularly and findings resolved", 5, ("vuln-mgmt",)),
    _c("11.3.2", "External vulnerability scans are performed by an ASV at least quarterly", 5, ("vuln-mgmt",)),
    _c("11.4.1", "External and internal penetration testing is performed regularly", 4, ("assurance", "vuln-mgmt")),
    _c("11.5.1", "Intrusion-detection/prevention techniques detect and alert on network intrusions", 4, ("monitoring",)),
    _c("11.6.1", "A change- and tamper-detection mechanism monitors payment pages", 3, ("monitoring",)),
    # Req 12 -- Governance
    _c("12.1.1", "An overall information security policy is established, published and maintained", 4, ("governance",)),
    _c("12.2.1", "Acceptable-use policies for end-user technologies are defined", 2, ("governance",)),
    _c("12.3.1", "Risks to the cardholder data environment are formally assessed and managed", 4, ("governance", "risk")),
    _c("12.5.2", "PCI DSS scope is documented and confirmed at least annually", 3, ("governance",)),
    _c("12.6.1", "A formal security-awareness program is in place for all personnel", 3, ("awareness",)),
    _c("12.8.1", "Third-party service providers (TPSPs) with whom account data is shared are inventoried", 5, ("third-party",)),
    _c("12.8.2", "Written agreements with TPSPs acknowledge their responsibility for account data", 5, ("third-party",)),
    _c("12.8.4", "A program monitors TPSPs' PCI DSS compliance status at least annually", 5, ("third-party",)),
    _c("12.8.5", "Information about which PCI DSS requirements are managed by each TPSP is maintained", 4, ("third-party",)),
    _c("12.10.1", "An incident-response plan exists and is ready to be activated", 4, ("incident",)),
]
