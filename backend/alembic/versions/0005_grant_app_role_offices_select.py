"""grant portfoyai_app SELECT on offices

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-02

GET /offices/me needs the app role to read the offices table. offices has
no RLS policy (it IS the tenant root, not tenant-scoped data), but the
role still needs a table-level grant — migration 0002 only granted the
per-tenant tables (users, listings, leads).
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.execute(f"GRANT SELECT ON offices TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE SELECT ON offices FROM {APP_ROLE}")
