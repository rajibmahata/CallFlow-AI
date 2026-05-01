"""
Campaign endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.auth import AdminOrAgent, AdminRequired, AnyRole
from app.database import get_db
from app.models.campaign import Campaign
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignStartRequest,
    CampaignStartResponse,
    CampaignUpdate,
)
from app.tasks.call_tasks import batch_queue_leads

router = APIRouter()


@router.post("", response_model=CampaignResponse, status_code=201, dependencies=[AdminRequired])
async def create_campaign(body: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(**body.model_dump())
    db.add(campaign)
    await db.flush()
    return campaign


@router.get("", response_model=list[CampaignResponse], dependencies=[AnyRole])
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    return result.scalars().all()


@router.get("/{campaign_id}", response_model=CampaignResponse, dependencies=[AnyRole])
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse, dependencies=[AdminRequired])
async def update_campaign(campaign_id: int, body: CampaignUpdate, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(campaign, field, value)
    return campaign


@router.post("/start", response_model=CampaignStartResponse, dependencies=[AdminOrAgent])
async def start_campaign(body: CampaignStartRequest, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, body.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if not campaign.is_active:
        raise HTTPException(status_code=400, detail="Campaign is not active")

    # Enqueue Celery task (non-blocking)
    task = batch_queue_leads.delay(body.campaign_id, body.batch_size)

    return CampaignStartResponse(
        campaign_id=body.campaign_id,
        leads_queued=0,  # actual count reported by Celery task
        message=f"Campaign started. Task ID: {task.id}",
    )
