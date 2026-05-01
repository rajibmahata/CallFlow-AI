"""Initial schema – creates all tables

Revision ID: 0001
Revises: 
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------
    # users
    # -------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="agent"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # -------------------------------------------------------------------
    # campaigns
    # -------------------------------------------------------------------
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("event_name", sa.String(length=255), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_location", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("max_daily_calls", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("llm_provider", sa.String(length=32), nullable=False, server_default="openai"),
        sa.Column("script_variant", sa.String(length=8), nullable=False, server_default="A"),
        sa.Column("script_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # -------------------------------------------------------------------
    # leads
    # -------------------------------------------------------------------
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("phone_hash", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=False, server_default="en"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("do_not_call", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("attendees_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("callback_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("custom_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leads_campaign_id", "leads", ["campaign_id"])
    op.create_index("ix_leads_phone_hash", "leads", ["phone_hash"])
    op.create_index("ix_leads_status", "leads", ["status"])

    # -------------------------------------------------------------------
    # call_logs
    # -------------------------------------------------------------------
    op.create_table(
        "call_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("retell_call_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="initiated"),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("recording_url", sa.String(length=512), nullable=True),
        sa.Column("intent", sa.String(length=64), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("questions_asked", sa.Text(), nullable=True),
        sa.Column("concerns", sa.Text(), nullable=True),
        sa.Column("attendees_mentioned", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=True),
        sa.Column("script_variant", sa.String(length=8), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_call_logs_lead_id", "call_logs", ["lead_id"])
    op.create_index("ix_call_logs_retell_call_id", "call_logs", ["retell_call_id"])

    # -------------------------------------------------------------------
    # reminders
    # -------------------------------------------------------------------
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False, server_default="sms"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reminders_lead_id", "reminders", ["lead_id"])
    op.create_index("ix_reminders_scheduled_at", "reminders", ["scheduled_at"])


def downgrade() -> None:
    op.drop_table("reminders")
    op.drop_table("call_logs")
    op.drop_table("leads")
    op.drop_table("campaigns")
    op.drop_table("users")
