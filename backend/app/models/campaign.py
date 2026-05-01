import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.call_log import CallLog
    from app.models.lead import Lead


class LLMProvider(str, enum.Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


class ScriptVariant(str, enum.Enum):
    A = "A"
    B = "B"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Event details
    event_name: Mapped[str] = mapped_column(String(200), nullable=False)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_location: Mapped[str] = mapped_column(String(300), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # Configuration
    llm_provider: Mapped[LLMProvider] = mapped_column(
        Enum(LLMProvider), nullable=False, default=LLMProvider.OPENAI
    )
    script_variant: Mapped[ScriptVariant] = mapped_column(
        Enum(ScriptVariant), nullable=False, default=ScriptVariant.A
    )
    script_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Compliance
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_daily_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=200)

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
    leads: Mapped[list["Lead"]] = relationship(
        "Lead", back_populates="campaign", cascade="all, delete-orphan"
    )
    call_logs: Mapped[list["CallLog"]] = relationship(
        "CallLog", back_populates="campaign", cascade="all, delete-orphan"
    )
    reminders: Mapped[list["Reminder"]] = relationship(  # noqa: F821
        "Reminder", back_populates="campaign", cascade="all, delete-orphan"
    )
