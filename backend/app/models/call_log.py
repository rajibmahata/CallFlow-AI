import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.lead import Lead


class CallDirection(str, enum.Enum):
    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"


class CallOutcome(str, enum.Enum):
    ANSWERED = "ANSWERED"
    NO_ANSWER = "NO_ANSWER"
    VOICEMAIL = "VOICEMAIL"
    BUSY = "BUSY"
    FAILED = "FAILED"


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )

    # Retell identifiers
    retell_call_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Call metadata
    direction: Mapped[CallDirection] = mapped_column(
        Enum(CallDirection), nullable=False, default=CallDirection.OUTBOUND
    )
    outcome: Mapped[CallOutcome | None] = mapped_column(Enum(CallOutcome), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recording_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Transcript & AI analysis
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sentiment_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0–100
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0–100
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    questions_asked: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    concerns: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    attendees_mentioned: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Script variant used
    script_variant: Mapped[str | None] = mapped_column(String(10), nullable=True)
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="en")

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="call_logs")
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="call_logs")  # noqa: F821
