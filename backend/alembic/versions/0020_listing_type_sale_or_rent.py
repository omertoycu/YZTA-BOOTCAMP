"""listings.listing_type (satılık/kiralık ayrımı)

Fiyat önerisi (Pricing Agent) emsalleri sadece bölge+oda sayısına göre
seçiyordu — aynı "2+1" için hem satılık (₺3.000.000'lar) hem kiralık
(₺10.000'ler) ilanlar aynı k-NN havuzuna girince aralık anlamsız çıkıyordu
(ör. ortalama-stdev negatife düşüyordu, gerçek bir prod hatası, kullanıcı
ekran görüntüsüyle bildirdi). Bu migration listings'e "satılık"/"kiralık"
ayrımını ekliyor; mevcut portföyler geriye dönük olarak "sale" kabul edilir
(danışman panelden düzeltebilir).

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-06
"""
import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column("listing_type", sa.String(10), nullable=False, server_default="sale"),
    )


def downgrade() -> None:
    op.drop_column("listings", "listing_type")
