"""
Lead state machine using the `transitions` library.
Defines all valid transitions and fires hooks on each.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from transitions import Machine, MachineError

from app.models.lead import LeadStatus

if TYPE_CHECKING:
    from app.models.lead import Lead


# All valid transitions: (trigger_name, source, dest)
TRANSITIONS = [
    # Happy path
    {"trigger": "queue", "source": LeadStatus.NEW, "dest": LeadStatus.QUEUED},
    {"trigger": "start_call", "source": LeadStatus.QUEUED, "dest": LeadStatus.CALLING},
    {"trigger": "answer", "source": LeadStatus.CALLING, "dest": LeadStatus.ANSWERED},
    {"trigger": "show_interest", "source": LeadStatus.ANSWERED, "dest": LeadStatus.INTERESTED},
    {"trigger": "flag_confirmation", "source": LeadStatus.INTERESTED, "dest": LeadStatus.NEEDS_CONFIRMATION},
    {"trigger": "confirm", "source": LeadStatus.NEEDS_CONFIRMATION, "dest": LeadStatus.CONFIRMED},
    {"trigger": "attend", "source": LeadStatus.CONFIRMED, "dest": LeadStatus.ATTENDED},

    # Rejection paths
    {
        "trigger": "reject",
        "source": [
            LeadStatus.ANSWERED,
            LeadStatus.INTERESTED,
            LeadStatus.NEEDS_CONFIRMATION,
            LeadStatus.CALLING,
        ],
        "dest": LeadStatus.NOT_INTERESTED,
    },

    # No answer
    {"trigger": "no_answer", "source": LeadStatus.CALLING, "dest": LeadStatus.NO_ANSWER},

    # Callback requested
    {
        "trigger": "schedule_callback",
        "source": [LeadStatus.ANSWERED, LeadStatus.CALLING, LeadStatus.NO_ANSWER],
        "dest": LeadStatus.CALLBACK,
    },

    # Retry from CALLBACK / NO_ANSWER
    {"trigger": "retry_call", "source": LeadStatus.CALLBACK, "dest": LeadStatus.QUEUED},
    {"trigger": "retry_call", "source": LeadStatus.NO_ANSWER, "dest": LeadStatus.QUEUED},
]

STATES = [s.value for s in LeadStatus]


class LeadFSM:
    """
    Wraps a Lead DB row with transition logic.
    Usage:
        fsm = LeadFSM(lead)
        fsm.queue()           # raises MachineError if invalid
        lead.status = fsm.state
    """

    def __init__(self, lead: "Lead") -> None:
        self._lead = lead
        self.state: str = lead.status.value

        Machine(
            model=self,
            states=STATES,
            transitions=TRANSITIONS,
            initial=self.state,
            ignore_invalid_triggers=False,
            auto_transitions=False,
        )

    def apply(self, trigger: str) -> LeadStatus:
        """
        Fire a named trigger and return the resulting status.
        Raises MachineError for invalid transitions.
        """
        try:
            getattr(self, trigger)()
        except AttributeError as exc:
            raise MachineError(f"Unknown trigger: {trigger}") from exc

        return LeadStatus(self.state)


class InvalidTransitionError(Exception):
    """Raised when a transition is not allowed for the current state."""


def transition_lead(lead: "Lead", trigger: str) -> LeadStatus:
    """
    Convenience wrapper: validate + apply a trigger, return new status.
    Converts MachineError → InvalidTransitionError (HTTP 409).
    """
    try:
        fsm = LeadFSM(lead)
        return fsm.apply(trigger)
    except MachineError as exc:
        raise InvalidTransitionError(
            f"Cannot apply '{trigger}' to lead in state '{lead.status.value}': {exc}"
        ) from exc
