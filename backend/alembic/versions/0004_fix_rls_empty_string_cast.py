"""fix RLS policies: unset app.current_office_id casts as '' not NULL

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-02

Postgres custom GUCs (like app.current_office_id) that have been used at
least once via SET LOCAL in a session revert to an empty string '' — not
NULL — once the transaction that set them commits. The original 0001
policy did `current_setting(..., true)::uuid`, which raises
`invalid input syntax for type uuid: ""` the moment any request reuses a
pooled connection after a commit. NULLIF(...,'') converts that empty
string to NULL first, so the cast succeeds and the policy correctly
denies access instead of erroring.
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

TENANT_TABLES = ["users", "listings", "leads"]


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS office_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY office_isolation ON {table}
            USING (office_id = NULLIF(current_setting('app.current_office_id', true), '')::uuid)
            WITH CHECK (office_id = NULLIF(current_setting('app.current_office_id', true), '')::uuid)
            """
        )


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS office_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY office_isolation ON {table}
            USING (office_id = current_setting('app.current_office_id', true)::uuid)
            WITH CHECK (office_id = current_setting('app.current_office_id', true)::uuid)
            """
        )
