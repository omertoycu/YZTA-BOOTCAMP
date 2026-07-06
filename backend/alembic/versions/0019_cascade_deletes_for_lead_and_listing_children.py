"""lead/listing çocuk tablolarında ON DELETE CASCADE

Danışman artık bir aday veya ilanı kalıcı olarak silebiliyor (bkz.
DELETE /leads/{id}, DELETE /listings/{id}). Bu iki kaydın FK ile bağlı
çocukları (lead_notes, lead_scores, whatsapp_inbound_events,
whatsapp_messages, listing_views) varsayılan NO ACTION FK davranışıyla
silmeyi bir ForeignKeyViolation ile engelliyordu. Bu migration ilgili FK
constraint'lerini ON DELETE CASCADE ile yeniden oluşturur — üst kayıt
silinince çocuklar da otomatik silinir. RLS ile çakışma yok: cascade silme
aynı transaction'da aynı role (portfoyai_app) tarafından tetiklenen normal
bir DELETE gibi işler, çocuk satırların office_id'si üst kayıtla aynı olduğu
için mevcut tenant context policy'yi geçer.

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-06
"""
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

# (constraint_adı, tablo, kolon, referans_tablo)
CASCADE_FKS = [
    ("lead_notes_lead_id_fkey", "lead_notes", "lead_id", "leads"),
    ("lead_scores_lead_id_fkey", "lead_scores", "lead_id", "leads"),
    ("whatsapp_inbound_events_lead_id_fkey", "whatsapp_inbound_events", "lead_id", "leads"),
    ("whatsapp_messages_lead_id_fkey", "whatsapp_messages", "lead_id", "leads"),
    ("listing_views_listing_id_fkey", "listing_views", "listing_id", "listings"),
]


def upgrade() -> None:
    for constraint_name, table, column, ref_table in CASCADE_FKS:
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(constraint_name, table, ref_table, [column], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    for constraint_name, table, column, ref_table in CASCADE_FKS:
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(constraint_name, table, ref_table, [column], ["id"])
