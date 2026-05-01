"""
SMS service — Twilio send + inbound opt-out handling.
"""
from __future__ import annotations

import structlog
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.config import settings
from app.models.campaign import Campaign
from app.models.lead import Lead

log = structlog.get_logger(__name__)

_twilio_client: Client | None = None


def get_twilio_client() -> Client:
    global _twilio_client
    if _twilio_client is None:
        _twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    return _twilio_client


# ---------------------------------------------------------------------------
# SMS Templates (multi-language)
# ---------------------------------------------------------------------------

def _build_confirmation_sms(lead: Lead, campaign: Campaign) -> str:
    event_date = campaign.event_date.strftime("%-d %b, %-I %p")
    seats = lead.attendees_count

    templates = {
        "en": (
            f"Hi {lead.name},\n"
            f"You are booked for {seats} seat{'s' if seats > 1 else ''}.\n"
            f"{event_date}\n"
            f"{campaign.event_location}\n"
            f"Reply STOP to opt out."
        ),
        "hi": (
            f"नमस्ते {lead.name},\n"
            f"आपकी {seats} सीट बुक हो गई है।\n"
            f"{event_date}\n"
            f"{campaign.event_location}\n"
            f"बंद करने के लिए STOP लिखें।"
        ),
    }
    return templates.get(lead.language, templates["en"])


def _build_reminder_sms(lead: Lead, campaign: Campaign, hours_before: int) -> str:
    event_date = campaign.event_date.strftime("%-d %b, %-I %p")
    time_label = f"{hours_before} hours" if hours_before < 24 else f"{hours_before // 24} day(s)"

    templates = {
        "en": (
            f"Reminder: {lead.name}, your seminar is in {time_label}.\n"
            f"{event_date} at {campaign.event_location}.\n"
            f"We look forward to seeing you!"
        ),
        "hi": (
            f"याद दिलाना: {lead.name}, आपका सेमिनार {time_label} में है।\n"
            f"{event_date}, {campaign.event_location}।"
        ),
    }
    return templates.get(lead.language, templates["en"])


# ---------------------------------------------------------------------------
# Send functions
# ---------------------------------------------------------------------------

def send_sms(to_number: str, body: str) -> str | None:
    """
    Send SMS via Twilio. Returns message SID or None on failure.
    Numbers must include country code (e.g. +919XXXXXXXXX).
    """
    try:
        message = get_twilio_client().messages.create(
            body=body,
            from_=settings.twilio_from_number,
            to=to_number,
        )
        log.info("sms.sent", to=to_number, sid=message.sid)
        return message.sid
    except TwilioRestException as exc:
        log.error("sms.failed", to=to_number, error=str(exc))
        return None


def send_confirmation_sms(lead: Lead, campaign: Campaign) -> str | None:
    body = _build_confirmation_sms(lead, campaign)
    return send_sms(lead.phone, body)


def send_reminder_sms(lead: Lead, campaign: Campaign, hours_before: int) -> str | None:
    body = _build_reminder_sms(lead, campaign, hours_before)
    return send_sms(lead.phone, body)


# ---------------------------------------------------------------------------
# Inbound opt-out detection
# ---------------------------------------------------------------------------

OPT_OUT_KEYWORDS = {"stop", "unsubscribe", "cancel", "quit", "end", "optout", "opt-out"}


def is_opt_out_message(body: str) -> bool:
    return body.strip().lower() in OPT_OUT_KEYWORDS
