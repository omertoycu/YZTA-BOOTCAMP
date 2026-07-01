"""create narrow auth-bootstrap role for cross-tenant email lookup

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-02

Login/registration must look up a user by email BEFORE the tenant
(office_id) is known — that is inherently a cross-tenant query and cannot
go through the RLS-scoped portfoyai_app role. Rather than granting the
whole app BYPASSRLS (which would defeat RLS everywhere), a separate,
narrowly-scoped role is used only by app/api/routes/auth.py.
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

AUTH_ROLE = "portfoyai_auth"
AUTH_ROLE_PASSWORD = "portfoyai_auth"


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{AUTH_ROLE}') THEN
                CREATE ROLE {AUTH_ROLE} LOGIN PASSWORD '{AUTH_ROLE_PASSWORD}' BYPASSRLS;
            END IF;
        END
        $$;
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {AUTH_ROLE}")
    # Sadece offices + users — listings/leads gibi asıl tenant verisine bu rolün hiç erişimi yok.
    op.execute(f"GRANT SELECT, INSERT ON offices, users TO {AUTH_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL PRIVILEGES ON offices, users FROM {AUTH_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {AUTH_ROLE}")
    op.execute(f"DROP ROLE IF EXISTS {AUTH_ROLE}")
