"""whatsapp mesaj geçmişi + Gemini alan çıkarımı için maliyet-kontrol sayaçları

WhatsApp Intake Agent artık gelen mesaj metnini Gemini'ye göndererek district/
budget_min/budget_max/room_count/radius_km çıkarıyor (bkz. app/agents/
whatsapp_extract.py). whatsapp_messages, lead_notes (0011) ile birebir aynı
RLS deseninde — hem gelen (in) hem giden (out) mesajları danışman panelinde
gösterilebilir şekilde tutar; whatsapp_inbound_events'ten (0007, sadece
idempotency, mesaj metni yok) farklıdır. leads.llm_extraction_count/
last_llm_extraction_at, kötü niyetli/aşırı mesajlaşan bir lead'in Gemini
faturasını şişirmesini önleyen 24 saatlik kayan pencere hız sınırı için.
fields_extracted_by_ai, danışman panelinde "AI ile dolduruldu" rozetini
tetikleyen basit tek-bayrak sinyal (alan bazlı değil).

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.add_column("leads", sa.Column("llm_extraction_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("leads", sa.Column("last_llm_extraction_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leads", sa.Column("fields_extracted_by_ai", sa.Boolean(), nullable=False, server_default="false"))

    op.create_table(
        "whatsapp_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("office_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offices.id"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),  # in | out
        sa.Column("message_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("external_message_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_whatsapp_messages_lead_id", "whatsapp_messages", ["lead_id"])
    op.execute("ALTER TABLE whatsapp_messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE whatsapp_messages FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY office_isolation ON whatsapp_messages
        USING (office_id = NULLIF(current_setting('app.current_office_id', true), '')::uuid)
        WITH CHECK (office_id = NULLIF(current_setting('app.current_office_id', true), '')::uuid)
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON whatsapp_messages TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL PRIVILEGES ON whatsapp_messages FROM {APP_ROLE}")
    op.execute("DROP POLICY IF EXISTS office_isolation ON whatsapp_messages")
    op.drop_index("ix_whatsapp_messages_lead_id", table_name="whatsapp_messages")
    op.drop_table("whatsapp_messages")
    op.drop_column("leads", "fields_extracted_by_ai")
    op.drop_column("leads", "last_llm_extraction_at")
    op.drop_column("leads", "llm_extraction_count")
