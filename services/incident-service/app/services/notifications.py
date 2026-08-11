"""Regulatory breach/incident notification drafting.

Two Nigerian regimes are modelled:

  * **CBN** — the Central Bank of Nigeria expects supervised financial
    institutions to report material cyber incidents promptly (24h window here).
    Triggered for High/Critical incidents.
  * **NDPC** — under the Nigeria Data Protection Act 2023 (and the earlier
    NDPR), a personal-data breach must be notified to the Nigeria Data
    Protection Commission within 72 hours. Triggered when personal data is
    involved (category DATA_BREACH or an explicit analyst flag).

We generate a structured draft the responder reviews and "submits"; there is no
live regulator API integration (documented deviation). The draft text is
deterministic given the incident so it's demoable and testable.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..config import settings


def _fmt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def cbn_deadline(opened_at: datetime) -> datetime:
    return opened_at + timedelta(hours=settings.cbn_deadline_hours)


def ndpa_deadline(opened_at: datetime) -> datetime:
    return opened_at + timedelta(hours=settings.ndpa_deadline_hours)


def build_cbn_notification(
    *, reference: str, vendor_name: str, severity: str, category: str, description: str, opened_at: datetime
) -> str:
    deadline = cbn_deadline(opened_at)
    return (
        "CENTRAL BANK OF NIGERIA — CYBER INCIDENT NOTIFICATION\n"
        f"Incident reference: {reference}\n"
        f"Reporting deadline: {_fmt(deadline)} ({settings.cbn_deadline_hours}h from detection)\n"
        "Reporting institution: SC-TPCRS operator (licensed financial institution)\n"
        f"Affected third party / vendor: {vendor_name}\n"
        f"Incident severity: {severity}\n"
        f"Incident category: {category}\n"
        f"Detected at: {_fmt(opened_at)}\n\n"
        "Summary of incident:\n"
        f"{description or 'A material cyber incident was detected affecting a third-party vendor in the payment ecosystem.'}\n\n"
        "Immediate actions taken: incident opened in SC-TPCRS, response team engaged, "
        "affected vendor exposure under containment review.\n"
        "This is an initial notification; a full report will follow on resolution.\n"
    )


def build_ndpc_notification(
    *, reference: str, vendor_name: str, severity: str, description: str, opened_at: datetime
) -> str:
    deadline = ndpa_deadline(opened_at)
    return (
        "NIGERIA DATA PROTECTION COMMISSION (NDPC) — PERSONAL DATA BREACH NOTIFICATION\n"
        "Filed under the Nigeria Data Protection Act 2023 (NDPA) / NDPR\n"
        f"Incident reference: {reference}\n"
        f"Notification deadline: {_fmt(deadline)} ({settings.ndpa_deadline_hours}h from awareness)\n"
        "Data controller: SC-TPCRS operator\n"
        f"Data processor / third party involved: {vendor_name}\n"
        f"Assessed severity: {severity}\n"
        f"Became aware at: {_fmt(opened_at)}\n\n"
        "Nature of the breach:\n"
        f"{description or 'A security incident with potential exposure of personal data processed by a third-party vendor.'}\n\n"
        "Categories of data subjects and records: to be confirmed during investigation.\n"
        "Likely consequences: under assessment.\n"
        "Measures taken/proposed: incident contained via SC-TPCRS response workflow; "
        "affected data subjects to be notified where the risk is high.\n"
    )
