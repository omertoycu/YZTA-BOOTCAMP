"""lead pipeline status + lead notes table

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-04

CRM derinliği: her lead artık bir satış hunisi aşamasında (new → contacted →
viewing → negotiation → won/lost) ve danışman görüşme notları tutabiliyor.
lead_notes tenant verisidir — whatsapp_inbound_events'le (0007) birebir aynı
RLS deseni uygulanır.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
    )

    op.create_table(
        "lead_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("office_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offices.id"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_lead_notes_lead_id", "lead_notes", ["lead_id"])
    op.execute("ALTER TABLE lead_notes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE lead_notes FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY office_isolation ON lead_notes
        USING (office_id = NULLIF(current_setting('app.current_office_id', true), '')::uuid)
        WITH CHECK (office_id = NULLIF(current_setting('app.current_office_id', true), '')::uuid)
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON lead_notes TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL PRIVILEGES ON lead_notes FROM {APP_ROLE}")
    op.execute("DROP POLICY IF EXISTS office_isolation ON lead_notes")
    op.drop_index("ix_lead_notes_lead_id", table_name="lead_notes")
    op.drop_table("lead_notes")
    op.drop_column("leads", "status")
