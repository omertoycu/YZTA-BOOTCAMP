"""ofis logosu

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-06

Her emlak ofisi kendi logosunu yükleyebilsin: sidebar/profil/dashboard'da
görünür ve markalı ulaşım raporu PDF'inde ofisin kendi logosu kullanılır
(kişiselleştirme, "logo her emlakçıya özel hissettirir"). logo_key,
listings.photos ile aynı desende bare bir S3 nesne anahtarıdır (bucket
private, sunum proxy route üzerinden — bkz. app/core/storage.py).
"""
from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.add_column("offices", sa.Column("logo_key", sa.String(255), nullable=True))
    # offices RLS'siz/global ve app rolünün üzerinde varsayılan olarak sadece
    # SELECT var (bkz. migration 0005/0010/0015) — logo yükleme route'unun
    # çalışması için kolon seviyesinde ayrıca UPDATE yetkisi gerekiyor.
    op.execute(f"GRANT UPDATE (logo_key) ON offices TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE UPDATE (logo_key) ON offices FROM {APP_ROLE}")
    op.drop_column("offices", "logo_key")
