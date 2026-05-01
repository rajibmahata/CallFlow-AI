"""
Calls API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.auth import AdminOrAgent, AnyRole
from app.database import get_db
from app.models.call_log import CallLog
from app.models.lead import Lead, LeadStatus
from app.schemas.call_log import CallLogResponse, InitiateCallRequest, InitiateCallResponse
from app.services.compliance_service import is_callable
from app.tasks.call_tasks import dispatch_single_call

router = APIRouter()


@router.post("/{lead_id}", response_model=InitiateCallResponse, dependencies=[AdminOrAgent])
async def initiate_call(
    lead_id: int,
    body: InitiateCallRequest = InitiateCallRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger an outbound call for a specific lead."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    callable_ok, reason = is_callable(lead)
    if not callable_ok:
        raise HTTPException(status_code=422, detail=f"Lead is not callable: {reason}")

    if lead.status not in (LeadStatus.NEW, LeadStatus.QUEUED, LeadStatus.CALLBACK, LeadStatus.NO_ANSWER):
        raise HTTPException(
            status_code=409, detail=f"Lead status '{lead.status.value}' is not eligible for calling"
        )

    # Enqueue via Celery (non-blocking)
    task = dispatch_single_call.delay(lead_id, body.campaign_id or lead.campaign_id)
    return InitiateCallResponse(
        lead_id=lead_id,
        retell_call_id="",  # Populated after Celery task completes
        message=f"Call dispatch queued. Task ID: {task.id}",
    )


@router.get("/logs/{lead_id}", response_model=list[CallLogResponse], dependencies=[AnyRole])
async def get_call_logs(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Get all call logs for a lead."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    result = await db.execute(
        select(CallLog).where(CallLog.lead_id == lead_id).order_by(CallLog.created_at.desc())
    )
    return result.scalars().all()
