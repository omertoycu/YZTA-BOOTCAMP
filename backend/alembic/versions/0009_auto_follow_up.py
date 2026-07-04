"""auto follow-up chain fields on leads

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-04

Otomatik WhatsApp takip zinciri (Sprint 2/3 hero özelliği): danışman bir lead
için zinciri açtığında scheduler (POST /internal/run-follow-ups, Railway cron
ile tetiklenir) vadesi gelen aşamanın mesajını gönderir ve bir sonraki aşamayı
planlar. Lead yanıt verirse (WhatsApp Intake Agent) zincir otomatik durur —
bkz. app/agents/follow_up.py.
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("auto_follow_up_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "leads",
        sa.Column("follow_up_stage", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("leads", sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True))
    # Scheduler her çalıştığında vadesi gelen lead'leri tarar; tablo büyüyünce
    # full scan olmasın diye sadece zinciri açık satırları kapsayan kısmi index.
    op.create_index(
        "ix_leads_next_follow_up_due",
        "leads",
        ["next_follow_up_at"],
        postgresql_where=sa.text("auto_follow_up_enabled AND next_follow_up_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_leads_next_follow_up_due", table_name="leads")
    op.drop_column("leads", "next_follow_up_at")
    op.drop_column("leads", "follow_up_stage")
    op.drop_column("leads", "auto_follow_up_enabled")
