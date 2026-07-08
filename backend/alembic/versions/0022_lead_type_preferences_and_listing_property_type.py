"""lead kiralık/satılık + emlak tipi tercihi, listings.property_type

Gerçek prod hatası (kullanıcı bildirdi): bir aday "kiralık iş yeri" ararken
sistem kiralık/satılık ayrımını hiç bilmiyordu (Lead'de bu tercihi tutan alan
yoktu) ve oda sayısı filtresi ticari ilanlar için anlamsızdı. Bu migration
üç kolon ekliyor: listings.property_type (konut/iş yeri/arsa — mevcut
listing_type/0020 ile aynı desen, geriye dönük "residential" varsayılan) ve
leads.listing_type_preference + leads.property_type_preference (ikisi de
nullable — belirtilmemiş demek "fark etmez", eşleştirmede filtre uygulanmaz).

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-08
"""
import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column("property_type", sa.String(20), nullable=False, server_default="residential"),
    )
    op.add_column("leads", sa.Column("listing_type_preference", sa.String(10), nullable=True))
    op.add_column("leads", sa.Column("property_type_preference", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "property_type_preference")
    op.drop_column("leads", "listing_type_preference")
    op.drop_column("listings", "property_type")
