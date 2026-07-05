"""public listing showcase: narrow public-read role + listing_views table

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-05

İlan vitrini hero özelliği: her portföy için login gerektirmeyen markalı bir
mikro-sayfa (/p/{listing_id}) + görüntülenme sayısı, Scoring/Reports için bir
sinyal. Login'siz bir sayfa RLS'in normal app rolüyle (portfoyai_app) hiç
çalışamaz çünkü tenant context (SET LOCAL app.current_office_id) bilinmeden
hiçbir satır görünmez ve office_id'yi bulmak için zaten bir SELECT gerekir
(tavuk-yumurta problemi).

Çözüm, auth bootstrap rolüyle (bkz. migration 0003) aynı desen ama DAHA dar:
BYPASSRLS bile gerekmiyor, sadece listings/offices için "TO portfoyai_public"
scoped ayrı bir SELECT policy'si (aynı tabloda portfoyai_app için geçerli
office_isolation policy'sine dokunmadan). Bilinçli tasarım: bu link paylaşıldığı
an okunabilir olması AMAÇLANAN bir tenant sınırı istisnası (danışman kendi
portföyünü bilerek paylaşıyor) — offices/users gibi hassas veriye bu rolün
hiç erişimi yok.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

PUBLIC_ROLE = "portfoyai_public"
PUBLIC_ROLE_PASSWORD = "portfoyai_public"
APP_ROLE = "portfoyai_app"


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{PUBLIC_ROLE}') THEN
                CREATE ROLE {PUBLIC_ROLE} LOGIN PASSWORD '{PUBLIC_ROLE_PASSWORD}';
            END IF;
        END
        $$;
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {PUBLIC_ROLE}")

    # listings zaten RLS altında (office_isolation, portfoyai_app için) — bu
    # yeni policy sadece portfoyai_public rolü için ek bir SELECT yolu açar,
    # mevcut policy'yi değiştirmez/zayıflatmaz.
    op.execute(f"GRANT SELECT ON listings TO {PUBLIC_ROLE}")
    op.execute(
        f"""
        CREATE POLICY public_showcase_read ON listings
        FOR SELECT TO {PUBLIC_ROLE}
        USING (true)
        """
    )
    # offices zaten RLS'siz/global (bkz. migration 0005) — direkt GRANT yeterli.
    op.execute(f"GRANT SELECT ON offices TO {PUBLIC_ROLE}")

    op.create_table(
        "listing_views",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("office_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("offices.id"), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("listings.id"), nullable=False),
        # Bilinçli olarak server_default YOK (bkz. app/models/listing_view.py) —
        # Python-side default kullanılıyor ki INSERT hiç RETURNING gerektirmesin
        # (portfoyai_public rolünün SELECT'i yok, RETURNING RLS'i tetikler).
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_listing_views_listing_id", "listing_views", ["listing_id"])
    op.execute("ALTER TABLE listing_views ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE listing_views FORCE ROW LEVEL SECURITY")
    # portfoyai_app: sadece kendi ofisinin görüntülenme kayıtlarını okuyabilir
    # (view-stats route'u için) — normal office_isolation deseni, INSERT gerekmez
    # (kayıtları public route atıyor).
    op.execute(
        f"""
        CREATE POLICY office_isolation ON listing_views
        FOR SELECT TO {APP_ROLE}
        USING (office_id = NULLIF(current_setting('app.current_office_id', true), '')::uuid)
        """
    )
    op.execute(f"GRANT SELECT ON listing_views TO {APP_ROLE}")
    # portfoyai_public: sadece INSERT — kendi eklediği dışında hiçbir görüntülenme
    # kaydını okuyamaz, tenant'lar arası sayaç sızıntısı olmaz. Kritik: bu tablonun
    # hiçbir sütununda server_default OLMAMALI (bkz. app/models/listing_view.py) —
    # olursa SQLAlchemy ORM INSERT'e otomatik bir RETURNING ekler, RETURNING da
    # RLS'in SELECT tarafını tetikler ve bu rol için SELECT policy'si hiç
    # olmadığından "new row violates row-level security policy" ile patlar.
    op.execute(
        f"""
        CREATE POLICY public_insert_view ON listing_views
        FOR INSERT TO {PUBLIC_ROLE}
        WITH CHECK (true)
        """
    )
    op.execute(f"GRANT INSERT ON listing_views TO {PUBLIC_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL PRIVILEGES ON listing_views FROM {PUBLIC_ROLE}")
    op.execute(f"REVOKE ALL PRIVILEGES ON listing_views FROM {APP_ROLE}")
    op.execute("DROP POLICY IF EXISTS public_insert_view ON listing_views")
    op.execute("DROP POLICY IF EXISTS office_isolation ON listing_views")
    op.drop_index("ix_listing_views_listing_id", table_name="listing_views")
    op.drop_table("listing_views")

    op.execute(f"REVOKE SELECT ON offices FROM {PUBLIC_ROLE}")
    op.execute("DROP POLICY IF EXISTS public_showcase_read ON listings")
    op.execute(f"REVOKE SELECT ON listings FROM {PUBLIC_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {PUBLIC_ROLE}")
    op.execute(f"DROP ROLE IF EXISTS {PUBLIC_ROLE}")
