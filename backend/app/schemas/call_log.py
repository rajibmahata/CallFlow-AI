from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.call_log import CallDirection, CallOutcome


class CallLogResponse(BaseModel):
    id: int
    lead_id: int
    campaign_id: int
    retell_call_id: Optional[str] = None
    direction: CallDirection
    outcome: Optional[CallOutcome] = None
    duration_seconds: int
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    intent: Optional[str] = None
    sentiment_score: Optional[int] = None
    confidence_score: Optional[int] = None
    ai_summary: Optional[str] = None
    questions_asked: Optional[str] = None
    concerns: Optional[str] = None
    attendees_mentioned: int
    script_variant: Optional[str] = None
    language: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class InitiateCallRequest(BaseModel):
    campaign_id: Optional[int] = None


class InitiateCallResponse(BaseModel):
    lead_id: int
    retell_call_id: str
    message: str
