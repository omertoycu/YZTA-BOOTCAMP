"""create least-privilege app role for RLS enforcement

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-02

Postgres superusers (and the default POSTGRES_USER created by the official
postgres image) always bypass Row-Level Security, regardless of
FORCE ROW LEVEL SECURITY. The application must connect as a separate,
non-superuser role for tenant isolation to actually be enforced.
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"
APP_ROLE_PASSWORD = "portfoyai_app"
TENANT_TABLES = ["offices", "users", "listings", "leads"]


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{APP_ROLE}') THEN
                CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{APP_ROLE_PASSWORD}';
            END IF;
        END
        $$;
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {', '.join(TENANT_TABLES)} TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL PRIVILEGES ON {', '.join(TENANT_TABLES)} FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {APP_ROLE}")
    op.execute(f"DROP ROLE IF EXISTS {APP_ROLE}")
