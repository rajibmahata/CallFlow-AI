import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.call_log import CallLog
    from app.models.reminder import Reminder


class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    QUEUED = "QUEUED"
    CALLING = "CALLING"
    ANSWERED = "ANSWERED"
    INTERESTED = "INTERESTED"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    ATTENDED = "ATTENDED"
    NOT_INTERESTED = "NOT_INTERESTED"
    CALLBACK = "CALLBACK"
    NO_ANSWER = "NO_ANSWER"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )

    # Contact info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="en")

    # State
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), nullable=False, default=LeadStatus.NEW, index=True
    )
    do_not_call: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # AI enrichment (populated after transcript analysis)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0–100
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0–100
    attendees_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Scheduling
    callback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="leads")  # noqa: F821
    call_logs: Mapped[list["CallLog"]] = relationship(
        "CallLog", back_populates="lead", cascade="all, delete-orphan"
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        "Reminder", back_populates="lead", cascade="all, delete-orphan"
    )
