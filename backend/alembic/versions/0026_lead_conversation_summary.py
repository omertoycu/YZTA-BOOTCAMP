"""leads.conversation_summary + conversation_summary_at — hibrit konuşma özeti

Yanıt taslağı (reply_draft) prompt'una sohbet geçmişi yerine TEK CÜMLELİK bir
aday özeti enjekte edilir (token tasarrufu). Özet öncelikle yapısal alanlardan
deterministik üretilir (sıfır Gemini maliyeti, bkz. app/agents/lead_summary.py);
yapısal alanlar boş ama konuşma uzunsa Gemini ile bir kez üretilip bu kolonlara
önbelleklenir — her çağrıda yeniden üretilmez.

Grant notu: migration 0002 leads'e TABLO seviyesinde SELECT/INSERT/UPDATE/
DELETE verdi — yeni kolonlar otomatik kapsanır, ayrıca grant gerekmez
(0025'teki listings notuyla aynı durum).

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-12
"""
import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("conversation_summary", sa.Text(), nullable=True))
    op.add_column(
        "leads", sa.Column("conversation_summary_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("leads", "conversation_summary_at")
    op.drop_column("leads", "conversation_summary")
