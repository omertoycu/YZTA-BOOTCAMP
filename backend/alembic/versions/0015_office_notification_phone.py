"""danışman bildirim numarası

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-06

Yeni lead anında bildirim hero özelliği: WhatsApp Intake Agent yeni bir aday
oluşturduğunda danışmanın kendi WhatsApp'ına (whatsapp_phone_number_id'nin
GÖNDERDİĞİ, offices.notification_phone'un ALDIĞI) bir bildirim gönderebilsin
diye. whatsapp_phone_number_id Meta'nın Graph API kimliği (gönderim tarafı),
notification_phone gerçek bir telefon numarası (alım tarafı) — ikisi farklı
kavramlar.
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.add_column("offices", sa.Column("notification_phone", sa.String(30), nullable=True))
    # offices RLS'siz/global ve app rolünün üzerinde varsayılan olarak sadece
    # SELECT var (bkz. migration 0005/0010) — PATCH /offices/me'nin çalışması
    # için kolon seviyesinde ayrıca UPDATE yetkisi gerekiyor.
    op.execute(f"GRANT UPDATE (notification_phone) ON offices TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE UPDATE (notification_phone) ON offices FROM {APP_ROLE}")
    op.drop_column("offices", "notification_phone")
