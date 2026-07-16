"""Vendor onboarding lifecycle state machine.

INITIATED -> QUESTIONNAIRE_SENT -> QUESTIONNAIRE_COMPLETED ->
ASSESSMENT_IN_PROGRESS -> {ONBOARDED, REJECTED}

ONBOARDED and REJECTED are terminal. Every legal transition is expected to
be followed by a Kafka publish (see services/events.py) and an audit_log
entry -- this module only validates the transition itself.
"""

from __future__ import annotations

STATES: tuple[str, ...] = (
    "INITIATED",
    "QUESTIONNAIRE_SENT",
    "QUESTIONNAIRE_COMPLETED",
    "ASSESSMENT_IN_PROGRESS",
    "ONBOARDED",
    "REJECTED",
)

TERMINAL_STATES: frozenset[str] = frozenset({"ONBOARDED", "REJECTED"})

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "INITIATED": frozenset({"QUESTIONNAIRE_SENT"}),
    "QUESTIONNAIRE_SENT": frozenset({"QUESTIONNAIRE_COMPLETED"}),
    "QUESTIONNAIRE_COMPLETED": frozenset({"ASSESSMENT_IN_PROGRESS"}),
    "ASSESSMENT_IN_PROGRESS": frozenset({"ONBOARDED", "REJECTED"}),
    "ONBOARDED": frozenset(),
    "REJECTED": frozenset(),
}


class InvalidTransitionError(ValueError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot transition vendor from {current!r} to {target!r}")
        self.current = current
        self.target = target


def validate_transition(current: str, target: str) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise InvalidTransitionError(current, target)
