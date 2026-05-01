"""
Celery beat tasks: send due reminder SMS messages.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog

from app.celery_app import celery_app

log = structlog.get_logger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.reminder_tasks.send_due_reminders")
def send_due_reminders() -> dict:
    """
    Sweep reminders table for unsent reminders whose scheduled_at <= now.
    Sends SMS for each and marks sent_at.
    Runs every 15 minutes via Celery beat.
    """
    from app.database import AsyncSessionFactory
    from app.models.campaign import Campaign
    from app.models.lead import Lead, LeadStatus
    from app.models.reminder import Reminder
    from app.services.sms_service import send_reminder_sms
    from sqlalchemy.future import select

    async def _run():
        async with AsyncSessionFactory() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(Reminder).where(
                    Reminder.sent_at == None,  # noqa: E711
                    Reminder.scheduled_at <= now,
                )
            )
            reminders = result.scalars().all()

            sent = 0
            for reminder in reminders:
                lead = await db.get(Lead, reminder.lead_id)
                campaign = await db.get(Campaign, reminder.campaign_id)

                if not lead or not campaign:
                    continue

                # Only send to confirmed leads who haven't opted out
                if lead.do_not_call or lead.status not in (
                    LeadStatus.CONFIRMED, LeadStatus.NEEDS_CONFIRMATION
                ):
                    reminder.sent_at = now  # Mark as processed anyway
                    continue

                # Calculate hours_before for message template
                delta = campaign.event_date.replace(tzinfo=timezone.utc) - now
                hours_before = max(int(delta.total_seconds() / 3600), 0)

                sid = send_reminder_sms(lead, campaign, hours_before)
                if sid:
                    reminder.sent_at = now
                    sent += 1

            await db.commit()
            log.info("reminders.sent", count=sent, total_due=len(reminders))
            return {"sent": sent, "due": len(reminders)}

    return _run_async(_run())
