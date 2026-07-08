"""aday adı (WhatsApp profili) + ofis AI otomatik yanıt ayarı

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-08

İki bağımsız ama aynı özellik dalgasına ait alan:

- leads.contact_name: Meta webhook payload'ındaki contacts[].profile.name
  (adayın WhatsApp profil adı) artık yakalanıyor; manuel aday girişinde de
  isteğe bağlı girilebiliyor. Panel telefon numarası yerine isim gösterebilsin.
- offices.auto_reply_enabled: ofis bazlı opt-in — açıkken WhatsApp Intake
  Agent gelen mesajlara ofis adına otomatik yanıt verir (karşılama/komut
  yanıtları + kriter dolunca eşleşen portföyleri gönderme, bkz.
  app/agents/whatsapp_bot.py). Varsayılan kapalı: kimse haberi olmadan
  adaylarına bot mesajı gönderilmesin.
"""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.add_column("leads", sa.Column("contact_name", sa.String(120), nullable=True))
    op.add_column(
        "offices",
        sa.Column("auto_reply_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # offices RLS'siz/global ve app rolünün üzerinde varsayılan olarak sadece
    # SELECT var (bkz. migration 0005/0010/0015) — PATCH /offices/me'nin bu
    # alanı yazabilmesi için kolon seviyesinde UPDATE yetkisi gerekiyor.
    op.execute(f"GRANT UPDATE (auto_reply_enabled) ON offices TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE UPDATE (auto_reply_enabled) ON offices FROM {APP_ROLE}")
    op.drop_column("offices", "auto_reply_enabled")
    op.drop_column("leads", "contact_name")
