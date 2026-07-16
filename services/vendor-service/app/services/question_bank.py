"""Tier-scaled security questionnaire bank.

Scoped-down placeholder for the blueprint's full SIG-based 240-question
bank: 12 security domains x up to 3 ranked questions each = 36 questions
total. Rank 1 questions are included at every tier down to Low; rank 3
questions are Critical-tier only. This preserves the blueprint's
proportional tier-scaling *shape* (~120/90/60/30) at roughly 1/3 scale.

    Critical: 3 questions/domain -> 36 total
    High:     2 questions/domain -> 24 total
    Medium:   2 questions for half the domains, 1 for the other half -> 18 total
    Low:      1 question/domain -> 12 total
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tier = Literal["Critical", "High", "Medium", "Low"]

DOMAINS: tuple[str, ...] = (
    "Access Control and Identity Management",
    "Data Protection and Encryption",
    "Network and Infrastructure Security",
    "Application and Software Security",
    "Incident Response and Breach Notification",
    "Business Continuity and Disaster Recovery",
    "Physical and Environmental Security",
    "HR Security and Awareness",
    "Third-Party and Subcontractor Risk Management",
    "Regulatory Compliance and Legal",
    "Asset and Configuration Management",
    "Security Governance and Risk Management",
)

_QUESTION_TEXT: dict[str, tuple[str, str, str]] = {
    "Access Control and Identity Management": (
        "Is multi-factor authentication enforced for all privileged accounts?",
        "Are user access rights reviewed at least quarterly?",
        "Is role-based access control (RBAC) enforced with documented least-privilege policies?",
    ),
    "Data Protection and Encryption": (
        "Is data encrypted in transit using TLS 1.2 or higher?",
        "Is data encrypted at rest using an industry-standard algorithm (e.g. AES-256)?",
        "Are encryption keys managed via a dedicated key management system (KMS/HSM)?",
    ),
    "Network and Infrastructure Security": (
        "Are firewalls configured to deny-by-default on all network segments?",
        "Is network traffic segmented between production and non-production environments?",
        "Are intrusion detection/prevention systems (IDS/IPS) deployed and monitored 24/7?",
    ),
    "Application and Software Security": (
        "Are all internet-facing applications scanned for vulnerabilities at least quarterly?",
        "Is a secure software development lifecycle (SSDLC) documented and followed?",
        "Are dependencies scanned for known vulnerabilities on every release?",
    ),
    "Incident Response and Breach Notification": (
        "Is there a documented, tested incident response plan?",
        "Are breach notification timelines to customers/regulators contractually defined?",
        "Is a 24/7 security operations capability (internal or outsourced) in place?",
    ),
    "Business Continuity and Disaster Recovery": (
        "Is there a documented business continuity / disaster recovery plan?",
        "Is the DR plan tested at least annually?",
        "Are recovery time/point objectives (RTO/RPO) formally defined for critical systems?",
    ),
    "Physical and Environmental Security": (
        "Are data centres protected by physical access controls (badges, biometrics, etc.)?",
        "Is physical access to sensitive areas logged and reviewed?",
        "Are environmental controls (fire suppression, redundant power/cooling) in place?",
    ),
    "HR Security and Awareness": (
        "Do employees undergo background checks appropriate to their role?",
        "Is annual security awareness training mandatory for all staff?",
        "Are access rights revoked within 24 hours of employee termination?",
    ),
    "Third-Party and Subcontractor Risk Management": (
        "Is there a documented process for assessing subcontractor security risk?",
        "Are subcontractors contractually bound to equivalent security obligations?",
        "Is a current inventory of all subcontractors with data access maintained?",
    ),
    "Regulatory Compliance and Legal": (
        "Is the organisation compliant with applicable data protection regulation (e.g. NDPA)?",
        "Are compliance obligations reviewed whenever regulations change?",
        "Is a data processing agreement (DPA) in place for all data processed on our behalf?",
    ),
    "Asset and Configuration Management": (
        "Is there a maintained inventory of all hardware and software assets?",
        "Are system configurations hardened against a documented baseline (e.g. CIS Benchmarks)?",
        "Is configuration drift detected and remediated automatically?",
    ),
    "Security Governance and Risk Management": (
        "Is there a named executive accountable for information security?",
        "Is a formal risk assessment conducted at least annually?",
        "Is the organisation certified against ISO 27001 or an equivalent framework?",
    ),
}


@dataclass(frozen=True)
class Question:
    code: str
    domain: str
    rank: int  # 1 = included at every tier; 3 = Critical-only
    text: str


def _build_questions() -> tuple[Question, ...]:
    questions: list[Question] = []
    for domain_index, domain in enumerate(DOMAINS):
        for rank, text in enumerate(_QUESTION_TEXT[domain], start=1):
            code = f"{domain_index + 1:02d}-{rank}"
            questions.append(Question(code=code, domain=domain, rank=rank, text=text))
    return tuple(questions)


ALL_QUESTIONS: tuple[Question, ...] = _build_questions()

_ANSWER_SCORES: dict[str, float] = {"YES": 100.0, "PARTIAL": 50.0, "NO": 0.0}


def questions_for_tier(tier: Tier) -> list[Question]:
    if tier == "Critical":
        max_rank = {domain: 3 for domain in DOMAINS}
    elif tier == "High":
        max_rank = {domain: 2 for domain in DOMAINS}
    elif tier == "Medium":
        max_rank = {domain: (2 if index % 2 == 0 else 1) for index, domain in enumerate(DOMAINS)}
    elif tier == "Low":
        max_rank = {domain: 1 for domain in DOMAINS}
    else:
        raise ValueError(f"Unknown tier: {tier!r}")

    return [q for q in ALL_QUESTIONS if q.rank <= max_rank[q.domain]]


def score_for_answer(answer: str | None) -> float | None:
    """NA and unanswered questions are excluded from the average (return None)."""
    if answer is None or answer == "NA":
        return None
    if answer not in _ANSWER_SCORES:
        raise ValueError(f"Unknown answer value: {answer!r}")
    return _ANSWER_SCORES[answer]
