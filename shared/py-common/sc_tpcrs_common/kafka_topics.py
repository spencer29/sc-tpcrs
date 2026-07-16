"""Canonical Kafka topic names shared by every service.

Keeping these as constants (rather than repeating string literals in each
service) avoids typo-based silent event-routing bugs across a 7-service event
graph.
"""

VENDOR_LIFECYCLE_EVENTS = "vendor.lifecycle.events"
RISK_SCORE_UPDATES = "risk.score.updates"
RISK_ANOMALY_ALERTS = "risk.anomaly.alerts"
RISK_THREAT_INTEL_MATCHES = "risk.threat_intel.matches"
SBOM_INGESTION_EVENTS = "sbom.ingestion.events"
CVE_ALERTS = "cve.alerts"
INCIDENT_EVENTS = "incident.events"

ALL_TOPICS = [
    VENDOR_LIFECYCLE_EVENTS,
    RISK_SCORE_UPDATES,
    RISK_ANOMALY_ALERTS,
    RISK_THREAT_INTEL_MATCHES,
    SBOM_INGESTION_EVENTS,
    CVE_ALERTS,
    INCIDENT_EVENTS,
]
