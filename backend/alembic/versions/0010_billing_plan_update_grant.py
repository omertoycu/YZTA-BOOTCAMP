"""allow app role to update offices.subscription_plan (iyzico billing)

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-04

offices tablosu RLS'siz/global ve app rolünün üzerinde sadece SELECT yetkisi
var (bkz. migration 0005). iyzico callback'i ödemesi doğrulanan ofisin planını
güncellemek zorunda — Postgres'in kolon seviyesi GRANT'i ile yetki SADECE
subscription_plan kolonuna açılır; app rolü ofis adını, whatsapp_phone_number_id'yi
veya başka bir ofisin herhangi bir alanını hâlâ değiştiremez... kolon seviyesinde.
Satır seviyesinde hangi ofisin güncelleneceği uygulama kodunun sorumluluğunda
(office_id her zaman iyzico'nun doğruladığı conversationId'den gelir, istemciden değil
— bkz. app/core/payments.py).
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.execute(f"GRANT UPDATE (subscription_plan) ON offices TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE UPDATE (subscription_plan) ON offices FROM {APP_ROLE}")
