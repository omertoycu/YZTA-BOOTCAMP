"""yer gösterme randevusu fields on leads

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-05

Yer gösterme randevusu + takvim daveti hero özelliği: danışman bir aday için
somut bir randevu (tarih/saat + konum) planlar, .ics dosyası indirebilir ve
opsiyonel bir WhatsApp onay mesajı gönderir. appointment_reminder_sent,
randevudan 24 saat önce tek seferlik otomatik hatırlatmanın (bkz.
app/agents/appointment_reminder.py) tekrar gönderilmesini engeller.
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leads", sa.Column("appointment_location", sa.String(255), nullable=True))
    op.add_column(
        "leads",
        sa.Column("appointment_reminder_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Cron her çalıştığında vadesi gelen randevuları tarar; sadece randevusu
    # olan/hatırlatması gönderilmemiş satırları kapsayan kısmi index.
    op.create_index(
        "ix_leads_appointment_reminder_due",
        "leads",
        ["appointment_at"],
        postgresql_where=sa.text("appointment_at IS NOT NULL AND NOT appointment_reminder_sent"),
    )


def downgrade() -> None:
    op.drop_index("ix_leads_appointment_reminder_due", table_name="leads")
    op.drop_column("leads", "appointment_reminder_sent")
    op.drop_column("leads", "appointment_location")
    op.drop_column("leads", "appointment_at")
