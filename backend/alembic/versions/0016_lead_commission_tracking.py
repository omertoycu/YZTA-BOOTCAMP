"""komisyon takibi: lead'e deal_amount/commission_amount/deal_closed_at

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-06

Komisyon takibi hero özelliği: kazanılan bir lead'e satış/kira bedeli ve
danışmanın kazandığı komisyon kaydedilebilir. status="won" geçişine otomatik
bağlanmaz (bkz. app/models/lead.py) — ayrı bir PATCH /leads/{id}/deal endpoint'i.
Reports/overview bu alanlardan toplam gelir/ortalama komisyon/bölgeye göre
gelir hesaplar.
"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("deal_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("leads", sa.Column("commission_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("leads", sa.Column("deal_closed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "deal_closed_at")
    op.drop_column("leads", "commission_amount")
    op.drop_column("leads", "deal_amount")
