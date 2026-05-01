import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.lead import Lead


class ReminderChannel(str, enum.Enum):
    SMS = "SMS"
    CALL = "CALL"


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )

    channel: Mapped[ReminderChannel] = mapped_column(
        Enum(ReminderChannel), nullable=False, default=ReminderChannel.SMS
    )
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="reminders")
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="reminders")
