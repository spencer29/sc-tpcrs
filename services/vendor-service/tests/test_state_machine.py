from __future__ import annotations

import pytest

from app.services.state_machine import (
    STATES,
    TERMINAL_STATES,
    InvalidTransitionError,
    validate_transition,
)


@pytest.mark.parametrize(
    "current,target",
    [
        ("INITIATED", "QUESTIONNAIRE_SENT"),
        ("QUESTIONNAIRE_SENT", "QUESTIONNAIRE_COMPLETED"),
        ("QUESTIONNAIRE_COMPLETED", "ASSESSMENT_IN_PROGRESS"),
        ("ASSESSMENT_IN_PROGRESS", "ONBOARDED"),
        ("ASSESSMENT_IN_PROGRESS", "REJECTED"),
    ],
)
def test_valid_transitions_pass(current, target):
    validate_transition(current, target)  # must not raise


@pytest.mark.parametrize(
    "current,target",
    [
        ("INITIATED", "ONBOARDED"),  # skipping states
        ("INITIATED", "ASSESSMENT_IN_PROGRESS"),
        ("QUESTIONNAIRE_SENT", "INITIATED"),  # backwards
        ("QUESTIONNAIRE_SENT", "ASSESSMENT_IN_PROGRESS"),  # skip
        ("ONBOARDED", "ASSESSMENT_IN_PROGRESS"),  # out of terminal state
        ("REJECTED", "ASSESSMENT_IN_PROGRESS"),  # out of terminal state
        ("ONBOARDED", "REJECTED"),
    ],
)
def test_invalid_transitions_raise(current, target):
    with pytest.raises(InvalidTransitionError):
        validate_transition(current, target)


def test_terminal_states_have_no_outgoing_transitions():
    for state in TERMINAL_STATES:
        for target in STATES:
            with pytest.raises(InvalidTransitionError):
                validate_transition(state, target)


def test_all_states_are_reachable_in_the_table():
    # Every non-terminal state must have at least one legal transition.
    from app.services.state_machine import ALLOWED_TRANSITIONS

    for state in STATES:
        if state in TERMINAL_STATES:
            continue
        assert len(ALLOWED_TRANSITIONS[state]) > 0
