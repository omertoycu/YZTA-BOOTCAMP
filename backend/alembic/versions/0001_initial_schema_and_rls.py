"""initial schema and multi-tenant RLS

Revision ID: 0001
Revises:
Create Date: 2026-07-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TENANT_TABLES = ["users", "listings", "leads"]


def upgrade() -> None:
    op.create_table(
        "offices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("subscription_plan", sa.String(50), nullable=False, server_default="starter"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("office_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offices.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="agent"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("office_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offices.id"), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("district", sa.String(120), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("room_count", sa.String(20), nullable=False),
        sa.Column("square_meters", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("photos", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("office_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offices.id"), nullable=False),
        sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("contact_phone", sa.String(30), nullable=False),
        sa.Column("district", sa.String(120), nullable=True),
        sa.Column("budget_min", sa.Numeric(12, 2), nullable=True),
        sa.Column("budget_max", sa.Numeric(12, 2), nullable=True),
        sa.Column("room_count", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Multi-tenant Row-Level Security: her tabloda office_id, oturumdaki
    # app.current_office_id ile eşleşmek zorunda. Bu ayarlanmazsa (bkz.
    # app/core/db.py:set_tenant) hiçbir satır dönmez.
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # FORCE olmadan tablo sahibi (uygulamanın bağlandığı rol dahil) policy'lerden
        # muaf tutulur ve RLS sessizce devre dışı kalmış gibi davranır.
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY office_isolation ON {table}
            USING (office_id = current_setting('app.current_office_id', true)::uuid)
            WITH CHECK (office_id = current_setting('app.current_office_id', true)::uuid)
            """
        )


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS office_isolation ON {table}")
    op.drop_table("leads")
    op.drop_table("listings")
    op.drop_table("users")
    op.drop_table("offices")
