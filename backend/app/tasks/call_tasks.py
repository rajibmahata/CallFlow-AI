"""
Celery tasks for call dispatch, transcript analysis, and confirmation SMS.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import structlog

from app.celery_app import celery_app

log = structlog.get_logger(__name__)


def _run_async(coro):
    """Run an async coroutine in a sync Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Batch queue leads for a campaign
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="app.tasks.call_tasks.batch_queue_leads", max_retries=2)
def batch_queue_leads(self, campaign_id: int, batch_size: int = 50) -> dict:
    """Transition NEW leads to QUEUED and dispatch call tasks."""
    from app.database import AsyncSessionFactory
    from app.models.lead import Lead, LeadStatus
    from sqlalchemy.future import select

    async def _run():
        async with AsyncSessionFactory() as db:
            result = await db.execute(
                select(Lead)
                .where(
                    Lead.campaign_id == campaign_id,
                    Lead.status == LeadStatus.NEW,
                    Lead.do_not_call == False,  # noqa: E712
                )
                .limit(batch_size)
            )
            leads = result.scalars().all()
            queued = 0
            for lead in leads:
                from app.core.state_machine import InvalidTransitionError, transition_lead
                try:
                    lead.status = transition_lead(lead, "queue")
                    queued += 1
                except InvalidTransitionError:
                    continue
            await db.commit()

            # Dispatch individual call tasks
            for lead in leads[:queued]:
                dispatch_single_call.delay(lead.id, campaign_id)

            log.info("batch_queue.complete", campaign_id=campaign_id, queued=queued)
            return {"queued": queued, "campaign_id": campaign_id}

    return _run_async(_run())


# ---------------------------------------------------------------------------
# Dispatch a single outbound call
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="app.tasks.call_tasks.dispatch_single_call", max_retries=3, default_retry_delay=60)
def dispatch_single_call(self, lead_id: int, campaign_id: int) -> dict:
    """Create an outbound call via Retell AI for a single lead."""
    from app.database import AsyncSessionFactory
    from app.models.campaign import Campaign
    from app.models.lead import Lead
    from app.services.compliance_service import is_callable

    async def _run():
        async with AsyncSessionFactory() as db:
            lead = await db.get(Lead, lead_id)
            campaign = await db.get(Campaign, campaign_id)

            if not lead or not campaign:
                log.warning("dispatch.lead_or_campaign_not_found", lead_id=lead_id)
                return {"error": "Lead or campaign not found"}

            callable_ok, reason = is_callable(lead)
            if not callable_ok:
                log.info("dispatch.skipped", lead_id=lead_id, reason=reason)
                return {"skipped": True, "reason": reason}

            from app.services.call_service import create_outbound_call
            retell_call_id = await create_outbound_call(lead, campaign_id, campaign.script_config)

            # Create initial call log
            from app.models.call_log import CallLog
            call_log = CallLog(
                lead_id=lead.id,
                campaign_id=campaign_id,
                retell_call_id=retell_call_id,
                language=lead.language,
                script_variant=campaign.script_variant.value if campaign.script_variant else None,
            )
            db.add(call_log)
            await db.commit()

            log.info("dispatch.call_created", lead_id=lead_id, retell_call_id=retell_call_id)
            return {"retell_call_id": retell_call_id, "lead_id": lead_id}

    try:
        return _run_async(_run())
    except Exception as exc:
        log.error("dispatch.error", lead_id=lead_id, error=str(exc))
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Analyze transcript (triggered by webhook post-call)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="app.tasks.call_tasks.analyze_transcript_task", max_retries=2)
def analyze_transcript_task(self, call_log_id: int) -> dict:
    """
    Run CrewAI transcript analyzer + follow-up strategist on a completed call.
    Updates CallLog, Lead status, and creates reminders as needed.
    """
    from app.database import AsyncSessionFactory
    from app.models.call_log import CallLog
    from app.models.campaign import Campaign
    from app.models.lead import Lead, LeadStatus

    async def _run():
        async with AsyncSessionFactory() as db:
            call_log = await db.get(CallLog, call_log_id)
            if not call_log or not call_log.transcript:
                return {"error": "No transcript to analyze"}

            lead = await db.get(Lead, call_log.lead_id)
            campaign = await db.get(Campaign, call_log.campaign_id)
            if not lead or not campaign:
                return {"error": "Lead or campaign not found"}

            llm_provider = campaign.llm_provider.value

            # --- Step 1: Transcript Analysis ---
            from app.agents.transcript_analyzer import run_transcript_analyzer
            analysis = run_transcript_analyzer(call_log.transcript, llm_provider)

            # Update call log with analysis results
            call_log.intent = analysis.intent
            call_log.sentiment_score = analysis.sentiment_score
            call_log.confidence_score = analysis.confidence
            call_log.ai_summary = analysis.summary
            call_log.questions_asked = json.dumps(analysis.questions_asked)
            call_log.concerns = json.dumps(analysis.concerns)
            call_log.attendees_mentioned = analysis.attendees

            # Update lead with latest AI data
            lead.ai_summary = analysis.summary
            lead.sentiment_score = analysis.sentiment_score
            lead.confidence_score = analysis.confidence
            lead.attendees_count = analysis.attendees

            # --- Step 2: Follow-up Strategy ---
            from app.agents.followup_strategist import run_followup_strategist
            strategy = run_followup_strategist(
                intent=analysis.intent,
                summary=analysis.summary,
                confidence=analysis.confidence,
                attendees=analysis.attendees,
                concerns=analysis.concerns,
                lead_name=lead.name,
                lead_language=lead.language,
                event_name=campaign.event_name,
                event_date=campaign.event_date.strftime("%d %b %Y, %I %p"),
                event_location=campaign.event_location,
                llm_provider=llm_provider,
            )

            # --- Step 3: Apply strategy ---
            from app.core.state_machine import InvalidTransitionError, transition_lead
            from app.core.websocket import ws_manager

            if strategy.next_action == "NEEDS_HUMAN_APPROVAL":
                try:
                    lead.status = transition_lead(lead, "show_interest")
                    lead.status = transition_lead(lead, "flag_confirmation")
                except InvalidTransitionError:
                    pass

                # Schedule confirmation reminders (48h, 24h, 2h before event)
                _schedule_reminders(db, lead, campaign)

            elif strategy.next_action == "SCHEDULE_CALLBACK" and strategy.callback_delta_hours:
                try:
                    lead.status = transition_lead(lead, "schedule_callback")
                    lead.callback_at = datetime.now(timezone.utc) + timedelta(hours=strategy.callback_delta_hours)
                except InvalidTransitionError:
                    pass

            elif strategy.next_action == "MARK_NOT_INTERESTED":
                try:
                    lead.status = transition_lead(lead, "reject")
                except InvalidTransitionError:
                    pass

            await db.commit()

            log.info(
                "transcript.analyzed",
                call_log_id=call_log_id,
                intent=analysis.intent,
                next_action=strategy.next_action,
                confidence=analysis.confidence,
            )
            return {
                "call_log_id": call_log_id,
                "intent": analysis.intent,
                "next_action": strategy.next_action,
            }

    try:
        return _run_async(_run())
    except Exception as exc:
        log.error("transcript.analyze_error", call_log_id=call_log_id, error=str(exc))
        raise self.retry(exc=exc)


def _schedule_reminders(db, lead, campaign) -> None:
    """Create reminder rows for T-48h, T-24h, T-2h before event."""
    from app.models.reminder import Reminder, ReminderChannel

    for hours_before in [48, 24, 2]:
        scheduled_at = campaign.event_date - timedelta(hours=hours_before)
        if scheduled_at > datetime.now(timezone.utc):
            reminder = Reminder(
                lead_id=lead.id,
                campaign_id=campaign.id,
                channel=ReminderChannel.SMS,
                message=f"Reminder: {hours_before}h before event",  # expanded in reminder_tasks
                scheduled_at=scheduled_at,
            )
            db.add(reminder)


# ---------------------------------------------------------------------------
# Send confirmation SMS (triggered by admin Approve action)
# ---------------------------------------------------------------------------

@celery_app.task(name="app.tasks.call_tasks.send_confirmation_sms_task")
def send_confirmation_sms_task(lead_id: int) -> dict:
    from app.database import AsyncSessionFactory
    from app.models.campaign import Campaign
    from app.models.lead import Lead

    async def _run():
        async with AsyncSessionFactory() as db:
            lead = await db.get(Lead, lead_id)
            if not lead:
                return {"error": "Lead not found"}
            campaign = await db.get(Campaign, lead.campaign_id)
            if not campaign:
                return {"error": "Campaign not found"}

            from app.services.sms_service import send_confirmation_sms
            sid = send_confirmation_sms(lead, campaign)
            log.info("confirmation_sms.sent", lead_id=lead_id, sid=sid)
            return {"sid": sid}

    return _run_async(_run())


# ---------------------------------------------------------------------------
# Retry scheduled callbacks
# ---------------------------------------------------------------------------

@celery_app.task(name="app.tasks.call_tasks.retry_scheduled_callbacks")
def retry_scheduled_callbacks() -> dict:
    """Check CALLBACK leads whose callback_at is now due and re-queue them."""
    from app.database import AsyncSessionFactory
    from app.models.lead import Lead, LeadStatus
    from sqlalchemy.future import select

    async def _run():
        async with AsyncSessionFactory() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(Lead).where(
                    Lead.status == LeadStatus.CALLBACK,
                    Lead.callback_at <= now,
                    Lead.do_not_call == False,  # noqa: E712
                )
            )
            leads = result.scalars().all()
            for lead in leads:
                from app.core.state_machine import InvalidTransitionError, transition_lead
                try:
                    lead.status = transition_lead(lead, "retry_call")
                    dispatch_single_call.delay(lead.id, lead.campaign_id)
                except InvalidTransitionError:
                    pass
            await db.commit()
            return {"retried": len(leads)}

    return _run_async(_run())
