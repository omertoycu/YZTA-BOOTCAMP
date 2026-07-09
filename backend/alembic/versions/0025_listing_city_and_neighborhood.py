"""listings.city + listings.neighborhood — yapılandırılmış konum

İlan ekleme artık şehir→ilçe→mahalle sıralı otomatik tamamlamayla yapılıyor
(statik Türkiye sözlüğü, bkz. app/core/geo.py). district zorunlu kalır
(Matching Agent ve raporlar onun üzerinden çalışmaya devam eder); city ve
neighborhood eski kayıtlar için nullable. Portal kaynağı aktarımında şehir
gelmese bile ilçe+mahalle eşleşmesinden çıkarılıp doldurulur (infer_city).

Grant notu: migration 0002 listings'e TABLO seviyesinde SELECT/INSERT/UPDATE/
DELETE verdi — yeni kolonlar otomatik kapsanır, ayrıca grant gerekmez
(offices'teki kolon-seviyeli grant deseninin aksine).

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-09
"""
import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("city", sa.String(120), nullable=True))
    op.add_column("listings", sa.Column("neighborhood", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("listings", "neighborhood")
    op.drop_column("listings", "city")
