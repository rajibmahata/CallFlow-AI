"""
Webhook handlers for Retell AI and Twilio SMS.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.core.state_machine import InvalidTransitionError, transition_lead
from app.core.websocket import ws_manager
from app.database import get_db
from app.models.call_log import CallLog, CallOutcome
from app.models.lead import Lead, LeadStatus
from app.services.sms_service import is_opt_out_message
from app.tasks.call_tasks import analyze_transcript_task

router = APIRouter()
log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Retell webhook signature verification
# ---------------------------------------------------------------------------

def _verify_retell_signature(request_body: bytes, signature: str) -> bool:
    """Verify Retell HMAC-SHA256 webhook signature."""
    if not settings.retell_webhook_secret:
        return True  # Skip verification in dev if secret not configured

    expected = hmac.new(
        settings.retell_webhook_secret.encode(),
        request_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


# ---------------------------------------------------------------------------
# Retell webhook
# ---------------------------------------------------------------------------

@router.post("/retell")
async def retell_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body_bytes = await request.body()

    # Signature check
    sig = request.headers.get("X-Retell-Signature", "")
    if not _verify_retell_signature(body_bytes, sig):
        log.warning("retell.webhook_signature_invalid")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event")
    call_data = payload.get("data", {})
    retell_call_id = call_data.get("call_id", "")
    metadata = call_data.get("metadata", {})
    lead_id = metadata.get("lead_id")

    log.info("retell.webhook_received", event=event_type, call_id=retell_call_id, lead_id=lead_id)

    if not lead_id:
        return Response(status_code=200)

    lead = await db.get(Lead, int(lead_id))
    if not lead:
        log.warning("retell.lead_not_found", lead_id=lead_id)
        return Response(status_code=200)

    # -----------------------------------------------------------------------
    # call_started
    # -----------------------------------------------------------------------
    if event_type == "call_started":
        try:
            new_status = transition_lead(lead, "start_call")
            lead.status = new_status
        except InvalidTransitionError:
            pass  # May already be in CALLING state

        # Create CallLog entry
        call_log = CallLog(
            lead_id=lead.id,
            campaign_id=lead.campaign_id,
            retell_call_id=retell_call_id,
            started_at=datetime.now(timezone.utc),
            language=lead.language,
        )
        db.add(call_log)
        await db.flush()

        await ws_manager.broadcast("call.started", {
            "lead_id": lead.id,
            "name": lead.name,
            "phone": lead.phone[-4:],  # last 4 digits only
            "retell_call_id": retell_call_id,
        })

    # -----------------------------------------------------------------------
    # call_ended
    # -----------------------------------------------------------------------
    elif event_type == "call_ended":
        end_data = call_data

        # Find existing call log
        result = await db.execute(
            select(CallLog).where(CallLog.retell_call_id == retell_call_id)
        )
        call_log = result.scalar_one_or_none()

        if not call_log:
            call_log = CallLog(
                lead_id=lead.id,
                campaign_id=lead.campaign_id,
                retell_call_id=retell_call_id,
                language=lead.language,
            )
            db.add(call_log)

        # Determine outcome
        disconnect_reason = end_data.get("disconnect_reason", "")
        if disconnect_reason in ("user_hangup", "agent_hangup", "call_transfer"):
            outcome = CallOutcome.ANSWERED
        elif disconnect_reason in ("voicemail", "no-answer"):
            outcome = CallOutcome.NO_ANSWER
        elif disconnect_reason == "busy":
            outcome = CallOutcome.BUSY
        else:
            outcome = CallOutcome.ANSWERED if end_data.get("transcript") else CallOutcome.NO_ANSWER

        call_log.outcome = outcome
        call_log.ended_at = datetime.now(timezone.utc)
        call_log.duration_seconds = int(end_data.get("duration_ms", 0) / 1000)
        call_log.transcript = end_data.get("transcript", "")
        call_log.recording_url = end_data.get("recording_url")
        call_log.script_variant = metadata.get("script_variant")

        # Transition lead state
        try:
            if outcome == CallOutcome.NO_ANSWER:
                lead.status = transition_lead(lead, "no_answer")
            else:
                lead.status = transition_lead(lead, "answer")
        except InvalidTransitionError:
            pass

        await db.flush()

        await ws_manager.broadcast("call.ended", {
            "lead_id": lead.id,
            "retell_call_id": retell_call_id,
            "outcome": outcome.value,
            "duration_seconds": call_log.duration_seconds,
        })

        # Trigger async transcript analysis if there's a transcript
        if call_log.transcript:
            analyze_transcript_task.delay(call_log.id)

    # -----------------------------------------------------------------------
    # call_analyzed (Retell's own analysis callback)
    # -----------------------------------------------------------------------
    elif event_type == "call_analyzed":
        pass  # We do our own analysis via CrewAI

    return Response(status_code=200)


# ---------------------------------------------------------------------------
# Twilio inbound SMS (opt-out handling)
# ---------------------------------------------------------------------------

@router.post("/sms")
async def twilio_sms_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle inbound Twilio SMS — detect opt-out and set do_not_call."""
    form = await request.form()
    from_number = str(form.get("From", ""))
    body = str(form.get("Body", ""))

    if not from_number:
        return Response(content="<Response/>", media_type="text/xml")

    log.info("sms.inbound", from_number=from_number[-4:], body_preview=body[:20])

    if is_opt_out_message(body):
        # Find all leads with this phone and mark do_not_call
        result = await db.execute(select(Lead).where(Lead.phone == from_number))
        leads = result.scalars().all()
        for lead in leads:
            lead.do_not_call = True
            try:
                transition_lead(lead, "reject")
                lead.status = LeadStatus.NOT_INTERESTED
            except InvalidTransitionError:
                pass
        await db.flush()
        log.info("sms.opt_out", from_number=from_number[-4:], leads_updated=len(leads))

    # Twilio expects TwiML response
    return Response(content="<Response/>", media_type="text/xml")
