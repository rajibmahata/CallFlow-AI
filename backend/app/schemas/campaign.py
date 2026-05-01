from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.campaign import LLMProvider, ScriptVariant


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    event_name: str
    event_date: datetime
    event_location: str
    capacity: int = 100
    llm_provider: LLMProvider = LLMProvider.OPENAI
    script_variant: ScriptVariant = ScriptVariant.A
    script_config: Optional[dict] = None
    max_daily_calls: int = 200


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[datetime] = None
    event_location: Optional[str] = None
    capacity: Optional[int] = None
    llm_provider: Optional[LLMProvider] = None
    script_variant: Optional[ScriptVariant] = None
    script_config: Optional[dict] = None
    is_active: Optional[bool] = None
    max_daily_calls: Optional[int] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    event_name: str
    event_date: datetime
    event_location: str
    capacity: int
    llm_provider: LLMProvider
    script_variant: ScriptVariant
    script_config: Optional[dict] = None
    is_active: bool
    max_daily_calls: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignStartRequest(BaseModel):
    campaign_id: int
    batch_size: int = 50


class CampaignStartResponse(BaseModel):
    campaign_id: int
    leads_queued: int
    message: str
