"""whatsapp intake agent: office phone_number_id mapping + idempotent inbound events

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-03

Meta Cloud API webhook istekleri bir JWT taşımaz (Meta'nın sunucusu bize
istek atar) — bu yüzden hangi ofise ait olduğunu, mesajı alan WhatsApp
Business numarasının phone_number_id'sini offices.whatsapp_phone_number_id
ile eşleştirerek buluyoruz. offices tablosunun zaten RLS policy'si olmadığı
için (bkz. 0005) bunun için auth.py'deki gibi ayrı bir BYPASSRLS rolüne
gerek yok; normal portfoyai_app rolüyle sorgulanabilir.

whatsapp_inbound_events, Meta'nın en-az-bir-kez teslimat garantisine karşı
idempotency sağlar: aynı external_message_id ikinci kez işlenmez.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.add_column("offices", sa.Column("whatsapp_phone_number_id", sa.String(64), nullable=True))
    op.create_unique_constraint(
        "uq_offices_whatsapp_phone_number_id", "offices", ["whatsapp_phone_number_id"]
    )

    op.create_table(
        "whatsapp_inbound_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("office_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offices.id"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("external_message_id", sa.String(128), nullable=False, unique=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE whatsapp_inbound_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE whatsapp_inbound_events FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY office_isolation ON whatsapp_inbound_events
        USING (office_id = NULLIF(current_setting('app.current_office_id', true), '')::uuid)
        WITH CHECK (office_id = NULLIF(current_setting('app.current_office_id', true), '')::uuid)
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON whatsapp_inbound_events TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL PRIVILEGES ON whatsapp_inbound_events FROM {APP_ROLE}")
    op.execute("DROP POLICY IF EXISTS office_isolation ON whatsapp_inbound_events")
    op.drop_table("whatsapp_inbound_events")
    op.drop_constraint("uq_offices_whatsapp_phone_number_id", "offices", type_="unique")
    op.drop_column("offices", "whatsapp_phone_number_id")
