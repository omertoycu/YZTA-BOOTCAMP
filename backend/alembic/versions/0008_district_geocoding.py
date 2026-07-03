"""district geocoding cache + lead search radius

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-03

Konum bazlı eşleştirme için: bir bölge adının (district) koordinatı, o bölge
kaç kez kullanılırsa kullanılsın sadece bir kere geocode edilip
geocoded_districts'te önbelleğe alınır (bkz. app/agents/geocoding.py).
Bu tablo tenant verisi değil, offices gibi paylaşılan/global bir coğrafi
gerçek — bu yüzden RLS policy'si yok (bkz. migration 0005'in gerekçesi).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.add_column("leads", sa.Column("radius_km", sa.Numeric(6, 2), nullable=True))

    op.create_table(
        "geocoded_districts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("district_name", sa.String(120), nullable=False, unique=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("geocoded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute(f"GRANT SELECT, INSERT ON geocoded_districts TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL PRIVILEGES ON geocoded_districts FROM {APP_ROLE}")
    op.drop_table("geocoded_districts")
    op.drop_column("leads", "radius_km")
