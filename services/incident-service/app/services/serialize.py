"""Model -> schema serialization with the computed `sla_breached` field."""

from __future__ import annotations

from ..models import Incident
from ..schemas import IncidentOut
from .lifecycle import is_sla_breached


def to_incident_out(incident: Incident) -> IncidentOut:
    out = IncidentOut.model_validate(incident)
    out.sla_breached = is_sla_breached(incident.sla_due_at, incident.status)
    return out
