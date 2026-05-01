"""
Compliance service — DND checks, call-time window enforcement, scrub list.
"""
from __future__ import annotations

from datetime import datetime

import pytz
import redis as redis_lib

from app.config import settings
from app.models.lead import Lead

_redis_client: redis_lib.Redis | None = None
DND_SCRUB_KEY = "dnd_scrub:{country}"


def _get_redis() -> redis_lib.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


# ---------------------------------------------------------------------------
# DND scrub list (per-country Redis set)
# ---------------------------------------------------------------------------

def add_to_scrub_list(phones: list[str], country: str = "generic") -> int:
    """Add phone numbers to the DND scrub list. Returns count added."""
    r = _get_redis()
    key = DND_SCRUB_KEY.format(country=country)
    if phones:
        return r.sadd(key, *phones)
    return 0


def is_in_scrub_list(phone: str, country: str = "generic") -> bool:
    r = _get_redis()
    key = DND_SCRUB_KEY.format(country=country)
    return bool(r.sismember(key, phone))


# ---------------------------------------------------------------------------
# Call time window
# ---------------------------------------------------------------------------

def is_within_calling_window(tz_name: str | None = None) -> bool:
    """
    Returns True if the current time is within the configured calling window.
    """
    tz_name = tz_name or settings.default_timezone
    try:
        tz = pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone(settings.default_timezone)

    now = datetime.now(tz)
    return settings.call_window_start <= now.hour < settings.call_window_end


# ---------------------------------------------------------------------------
# Composite check
# ---------------------------------------------------------------------------

def is_callable(lead: Lead, country: str = "generic") -> tuple[bool, str]:
    """
    Full compliance check for a lead.

    Returns:
        (True, "") if callable
        (False, reason) if not callable
    """
    if lead.do_not_call:
        return False, "Lead marked do_not_call"

    if is_in_scrub_list(lead.phone, country):
        return False, "Phone in DND scrub list"

    if not is_within_calling_window():
        return False, f"Outside calling window ({settings.call_window_start}–{settings.call_window_end})"

    return True, ""
