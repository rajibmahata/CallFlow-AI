from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.lead import LeadStatus


class LeadBase(BaseModel):
    name: str
    phone: str
    age: Optional[int] = None
    city: Optional[str] = None
    language: str = "en"

    @field_validator("phone")
    @classmethod
    def _phone_not_empty(cls, v: str) -> str:
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if not cleaned:
            raise ValueError("Phone number must not be empty")
        return cleaned


class LeadCreate(LeadBase):
    campaign_id: int
    do_not_call: bool = False


class LeadUpdate(BaseModel):
    status: Optional[LeadStatus] = None
    do_not_call: Optional[bool] = None
    callback_at: Optional[datetime] = None
    language: Optional[str] = None


class LeadResponse(LeadBase):
    id: int
    campaign_id: int
    status: LeadStatus
    do_not_call: bool
    ai_summary: Optional[str] = None
    sentiment_score: Optional[int] = None
    confidence_score: Optional[int] = None
    attendees_count: int
    recording_url: Optional[str] = None
    callback_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    page_size: int


class CSVUploadResponse(BaseModel):
    total_rows: int
    imported: int
    duplicates: int
    dnd_filtered: int
    errors: int
