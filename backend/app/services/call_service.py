"""
Retell AI call service.
Wraps Retell REST API for creating outbound phone calls.
"""
from __future__ import annotations

import httpx
import structlog

from app.config import settings
from app.models.lead import Lead

log = structlog.get_logger(__name__)

RETELL_BASE_URL = "https://api.retellai.com"


async def create_outbound_call(lead: Lead, campaign_id: int, script_config: dict | None = None) -> str:
    """
    Initiate an outbound call via Retell AI.

    Returns:
        retell_call_id (str)

    Raises:
        httpx.HTTPStatusError on API failure.
    """
    metadata = {
        "lead_id": lead.id,
        "lead_name": lead.name,
        "campaign_id": campaign_id,
        "language": lead.language,
    }

    payload = {
        "from_number": settings.retell_from_number,
        "to_number": lead.phone,
        "agent_id": settings.retell_agent_id,
        "metadata": metadata,
        "retell_llm_dynamic_variables": _build_dynamic_vars(lead, script_config),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{RETELL_BASE_URL}/v2/create-phone-call",
            headers={
                "Authorization": f"Bearer {settings.retell_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()

    data = response.json()
    call_id = data.get("call_id", "")
    log.info("retell.call_created", lead_id=lead.id, retell_call_id=call_id)
    return call_id


def _build_dynamic_vars(lead: Lead, script_config: dict | None) -> dict:
    """Build the dynamic LLM variables injected into the Retell agent prompt."""
    config = script_config or {}
    return {
        "lead_name": lead.name,
        "lead_city": lead.city or "your area",
        "language": lead.language,
        "warm_context": config.get(
            "warm_context",
            "the letter we recently sent about our upcoming seminar",
        ),
        "event_name": config.get("event_name", "our upcoming seminar"),
        "event_date": config.get("event_date", "this month"),
        "event_location": config.get("event_location", "a nearby venue"),
        "script_variant": config.get("script_variant", "A"),
    }


async def get_call_recording_url(retell_call_id: str) -> str | None:
    """Fetch recording URL for a completed call."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            response = await client.get(
                f"{RETELL_BASE_URL}/v2/get-call/{retell_call_id}",
                headers={"Authorization": f"Bearer {settings.retell_api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("recording_url")
        except httpx.HTTPError:
            log.warning("retell.recording_fetch_failed", retell_call_id=retell_call_id)
            return None
