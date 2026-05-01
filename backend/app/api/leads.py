"""
Leads API endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AdminOrAgent, AdminRequired, AnyRole
from app.core.state_machine import InvalidTransitionError, transition_lead
from app.core.websocket import ws_manager
from app.database import get_db
from app.models.lead import Lead, LeadStatus
from app.schemas.lead import CSVUploadResponse, LeadListResponse, LeadResponse, LeadUpdate
from app.services.compliance_service import add_to_scrub_list
from app.services.lead_service import import_leads_from_csv
from app.tasks.call_tasks import dispatch_single_call

router = APIRouter()


@router.post("/upload", response_model=CSVUploadResponse, dependencies=[AdminOrAgent])
async def upload_leads(
    campaign_id: int,
    file: UploadFile = File(...),
    country: str = Query(default="generic"),
    db: AsyncSession = Depends(get_db),
):
    """Upload a CSV file of leads for a campaign."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    content = await file.read()
    try:
        return await import_leads_from_csv(content, campaign_id, db, country)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload-dnd-scrub", dependencies=[AdminRequired])
async def upload_dnd_scrub(
    file: UploadFile = File(...),
    country: str = Query(default="generic"),
):
    """Upload a DND scrub list CSV (single column: phone). Stores in Redis."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    import io
    import pandas as pd
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content), header=None, names=["phone"])
    phones = df["phone"].astype(str).str.strip().tolist()
    count = add_to_scrub_list(phones, country)
    return {"added": count, "country": country}


@router.get("", response_model=LeadListResponse, dependencies=[AnyRole])
async def list_leads(
    campaign_id: int | None = None,
    status: LeadStatus | None = None,
    language: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(Lead)
    if campaign_id:
        query = query.where(Lead.campaign_id == campaign_id)
    if status:
        query = query.where(Lead.status == status)
    if language:
        query = query.where(Lead.language == language)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(Lead.created_at.desc())
    result = await db.execute(query)
    leads = result.scalars().all()

    return LeadListResponse(items=leads, total=total, page=page, page_size=page_size)


@router.get("/{lead_id}", response_model=LeadResponse, dependencies=[AnyRole])
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse, dependencies=[AdminOrAgent])
async def update_lead(lead_id: int, body: LeadUpdate, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(lead, field, value)
    return lead


@router.post("/{lead_id}/approve", response_model=LeadResponse, dependencies=[AdminRequired])
async def approve_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Admin approves a NEEDS_CONFIRMATION lead → CONFIRMED + SMS sent."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    try:
        new_status = transition_lead(lead, "confirm")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    lead.status = new_status

    # Trigger SMS confirmation via Celery
    from app.tasks.call_tasks import send_confirmation_sms_task
    send_confirmation_sms_task.delay(lead_id)

    # Broadcast to live dashboard
    await ws_manager.broadcast("lead.confirmed", {"lead_id": lead_id, "name": lead.name})

    return lead


@router.post("/{lead_id}/reject", response_model=LeadResponse, dependencies=[AdminOrAgent])
async def reject_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Admin/agent rejects a lead → NOT_INTERESTED."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    try:
        new_status = transition_lead(lead, "reject")
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    lead.status = new_status
    return lead
