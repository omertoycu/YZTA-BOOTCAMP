"""danışmanın kendi WhatsApp Phone Number ID'sini ayarlayabilmesi

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-06

whatsapp_phone_number_id (migration 0007) şimdiye kadar sadece elle/DB
üzerinden set edilebiliyordu. WhatsApp Business kurulumunu self-servis
yapılabilir kılmak için PATCH /offices/me artık bu alanı da kabul ediyor —
app rolüne kolon seviyesinde UPDATE yetkisi gerekiyor (bkz. migration
0010/0015 ile aynı desen, offices RLS'siz/global bkz. migration 0005).
"""
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.execute(f"GRANT UPDATE (whatsapp_phone_number_id) ON offices TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE UPDATE (whatsapp_phone_number_id) ON offices FROM {APP_ROLE}")
