"""add lead scoring fields and lead_scores table

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.add_column("leads", sa.Column("message_count", sa.Integer, nullable=False, server_default="0"))
    op.add_column("leads", sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "lead_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("office_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offices.id"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("score_breakdown", postgresql.JSONB, nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE lead_scores ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE lead_scores FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY office_isolation ON lead_scores
        USING (office_id = NULLIF(current_setting('app.current_office_id', true), '')::uuid)
        WITH CHECK (office_id = NULLIF(current_setting('app.current_office_id', true), '')::uuid)
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON lead_scores TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL PRIVILEGES ON lead_scores FROM {APP_ROLE}")
    op.execute("DROP POLICY IF EXISTS office_isolation ON lead_scores")
    op.drop_table("lead_scores")
    op.drop_column("leads", "last_contacted_at")
    op.drop_column("leads", "message_count")
