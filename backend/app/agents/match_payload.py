"""Eşleşme sonuçlarının WhatsApp'a giden temiz/tek biçimli payload'ı.

"Payload stripping": Matching Agent'ın aday dict'lerinden mesaja/prompt'a
sadece gerekli alanlar (fiyat, oda sayısı, konum, ilan linki) süzülür — üç
gönderim noktası (whatsapp_bot._matches_message, leads.send_matches_via_whatsapp,
LLM taslak sonrası link ekleme) aynı yardımcıları kullanır, format tek yerden
değişir.

İlan linki, login gerektirmeyen mevcut vitrin sayfasıdır (/p/{listing_id},
bkz. app/api/routes/public.py) — adayın tıklaması görüntülenme sinyali olarak
da sayılır. Linkler LLM prompt'una BİLİNÇLİ olarak sokulmaz (model URL'i
bozabilir); taslak metnin SONUNA deterministik eklenir (append_match_links).
"""

from app.core.config import settings


def public_listing_url(listing_id: str) -> str:
    """Login'siz ilan vitrini linki — frontend'in /p/[id] sayfası."""
    return f"{settings.frontend_base_url.rstrip('/')}/p/{listing_id}"


def _format_try(amount: float) -> str:
    return f"{amount:,.0f} TL".replace(",", ".")


def _location_label(candidate: dict) -> str | None:
    district = candidate.get("district")
    city = candidate.get("city")
    if district and city:
        return f"{district}/{city}"
    return district or city


def strip_match_payload(candidate: dict) -> dict:
    """Aday dict'ini mesaj üretiminde kullanılan temiz şemaya indirger —
    açıklama/başlık dışındaki ham DB alanları asla dışarı sızmaz."""
    return {
        "listing_id": candidate["listing_id"],
        "title": candidate.get("title"),
        "price": candidate.get("price"),
        "room_count": candidate.get("room_count"),
        "location": _location_label(candidate),
        "link": public_listing_url(candidate["listing_id"]),
        "match_reason": candidate.get("match_reason"),
    }


def format_match_lines(matches: list[dict]) -> list[str]:
    """Deterministik, numaralı ilan satırları (her ilan iki satır: özet + link).
    WhatsApp bare URL'leri otomatik linkler — URL kendi satırında durur ki
    noktalama işaretine yapışıp bozulmasın."""
    lines: list[str] = []
    for i, candidate in enumerate(matches, start=1):
        payload = strip_match_payload(candidate)
        details = [d for d in (payload["room_count"], payload["location"]) if d]
        summary = f"{i}) {payload['title']} — {_format_try(payload['price'])}"
        if details:
            summary += f" ({', '.join(details)})"
        lines.append(summary)
        lines.append(payload["link"])
    return lines


def append_match_links(draft: str, matches: list[dict]) -> str:
    """LLM taslağının sonuna ilan linklerini deterministik ekler — linkler
    prompt'a hiç girmediği için modelin URL bozma riski sıfır."""
    if not matches:
        return draft
    link_lines = [
        f"{i}) {public_listing_url(m['listing_id'])}" for i, m in enumerate(matches, start=1)
    ]
    return draft + "\n\nİlan detayları:\n" + "\n".join(link_lines)
