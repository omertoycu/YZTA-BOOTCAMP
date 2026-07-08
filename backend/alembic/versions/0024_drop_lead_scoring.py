"""aday skorlama (Skorla) özelliği tamamen kaldırıldı

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-08

Ürün kararı: kural bazlı 0-100 lead skoru işlevsel bulunmadı, kaldırıldı.
message_count/last_contacted_at (migration 0006) skorlamadan bağımsız
olarak takip zinciri ve panelde hâlâ kullanıldığı için dokunulmuyor —
sadece lead_scores tablosu ve buna bağlı FK/policy/grant kaldırılıyor.
"""
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.execute(f"REVOKE ALL PRIVILEGES ON lead_scores FROM {APP_ROLE}")
    op.execute("DROP POLICY IF EXISTS office_isolation ON lead_scores")
    op.drop_table("lead_scores")


def downgrade() -> None:
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql

    op.create_table(
        "lead_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("office_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offices.id"), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
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
