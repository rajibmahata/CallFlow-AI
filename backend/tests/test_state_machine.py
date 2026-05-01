"""
Tests for LeadFSM state machine transitions.
"""
import pytest
from unittest.mock import MagicMock

from app.models.lead import LeadStatus


def make_lead(status: LeadStatus):
    lead = MagicMock()
    lead.status = status
    return lead


class TestLeadFSM:
    def test_queue_from_new(self):
        from app.core.state_machine import transition_lead
        lead = make_lead(LeadStatus.NEW)
        new_status = transition_lead(lead, "queue")
        assert new_status == LeadStatus.QUEUED

    def test_start_call(self):
        from app.core.state_machine import transition_lead
        lead = make_lead(LeadStatus.QUEUED)
        new_status = transition_lead(lead, "start_call")
        assert new_status == LeadStatus.CALLING

    def test_answered(self):
        from app.core.state_machine import transition_lead
        lead = make_lead(LeadStatus.CALLING)
        new_status = transition_lead(lead, "answer")
        assert new_status == LeadStatus.ANSWERED

    def test_show_interest(self):
        from app.core.state_machine import transition_lead
        lead = make_lead(LeadStatus.ANSWERED)
        new_status = transition_lead(lead, "show_interest")
        assert new_status == LeadStatus.INTERESTED

    def test_flag_confirmation(self):
        from app.core.state_machine import transition_lead
        lead = make_lead(LeadStatus.INTERESTED)
        new_status = transition_lead(lead, "flag_confirmation")
        assert new_status == LeadStatus.NEEDS_CONFIRMATION

    def test_confirm_lead(self):
        from app.core.state_machine import transition_lead
        lead = make_lead(LeadStatus.NEEDS_CONFIRMATION)
        new_status = transition_lead(lead, "confirm")
        assert new_status == LeadStatus.CONFIRMED

    def test_reject_lead(self):
        from app.core.state_machine import transition_lead
        lead = make_lead(LeadStatus.NEEDS_CONFIRMATION)
        new_status = transition_lead(lead, "reject")
        assert new_status == LeadStatus.NOT_INTERESTED

    def test_no_answer(self):
        from app.core.state_machine import transition_lead
        lead = make_lead(LeadStatus.CALLING)
        new_status = transition_lead(lead, "no_answer")
        assert new_status == LeadStatus.NO_ANSWER

    def test_schedule_callback(self):
        from app.core.state_machine import transition_lead
        lead = make_lead(LeadStatus.ANSWERED)
        new_status = transition_lead(lead, "schedule_callback")
        assert new_status == LeadStatus.CALLBACK

    def test_invalid_transition_raises(self):
        from app.core.state_machine import InvalidTransitionError, transition_lead
        lead = make_lead(LeadStatus.CONFIRMED)
        with pytest.raises(InvalidTransitionError):
            transition_lead(lead, "queue")

    def test_attend(self):
        from app.core.state_machine import transition_lead
        lead = make_lead(LeadStatus.CONFIRMED)
        new_status = transition_lead(lead, "attend")
        assert new_status == LeadStatus.ATTENDED
