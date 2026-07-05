"""manual reminder fields on leads

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-05

Sesli Not → CRM güncellemesi hero özelliği: danışman sahada "cuma günü tekrar
arayacağım" dediğinde bu, otomatik WhatsApp takip zincirinden (0009:
auto_follow_up_enabled/next_follow_up_at) tamamen ayrı, danışmana özel bir
kişisel hatırlatmadır — aday'a hiçbir otomatik mesaj gitmez, sadece panelde
görünür. Bu yüzden ayrı kolonlar: reminder_at/reminder_note.
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leads", sa.Column("reminder_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "reminder_note")
    op.drop_column("leads", "reminder_at")
