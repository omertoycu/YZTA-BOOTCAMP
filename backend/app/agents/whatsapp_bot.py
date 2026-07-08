"""WhatsApp otomatik yanıt katmanı (opt-in, offices.auto_reply_enabled).

İki amaç bir arada:

1. **Maliyet kalkanı / yönlendirme:** Gelen hattı serbest sohbete bırakmak yerine
   adaya net komutlar öğretilir (MENÜ / İLANLAR / DURUM / DANIŞMAN). Komutlar
   TAMAMEN deterministik yanıtlanır — Gemini'ye hiç gidilmez, saçma/İlgisiz
   mesajlar da sessizce yoksayılır (yanıt yok = maliyet yok).
2. **Emlakçı uyurken satış:** Aday kriterlerini yazdığında (extraction bir alanı
   doldurduğunda) Matching Agent'ın bulduğu GERÇEK portföyler otomatik olarak
   adaya gönderilir — kişisel metin için Gemini denenir (reply_draft), hata/
   yapılandırma eksikliğinde deterministik listeye düşülür.

Bu katman yalnızca app/agents/intake.py'den, ofis auto_reply_enabled ise
çağrılır; her hata best-effort yutulur, webhook her koşulda 200 döner.
"""

from sqlalchemy.orm import Session

from app.agents.graph import build_matching_graph
from app.agents.reply_draft import ReplyDraftError, draft_reply
from app.core.text import fold_turkish_i
from app.models.lead import Lead
from app.models.office import Office

MAX_AUTO_MATCHES = 3

# Komut adları fold_turkish_i ile normalize edilmiş halde tutulur (ı/İ/I → i);
# adayın ASCII ("danisman") ya da Türkçe ("DANIŞMAN") yazması fark etmez.
COMMAND_ALIASES: dict[str, set[str]] = {
    "menu": {"menu", "menü", "yardim", "komutlar", "komut", "help"},
    "listings": {"ilanlar", "ilan", "portfoy", "portföy", "eslesme", "eşleşme", "eşleşmeler", "eslesmeler"},
    "status": {"durum", "bilgilerim", "kriterlerim"},
    "agent": {"danişman", "danisman", "temsilci", "yetkili"},
}


def _normalize(text: str) -> str:
    folded = fold_turkish_i(text)
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in folded)
    return " ".join(cleaned.split())


def detect_command(text: str | None) -> str | None:
    """Mesaj tek başına bir komutsa komut adını döner. Tam eşleşme aranır —
    "ilanlar hakkında bir sorum var" gibi gerçek içerikli bir mesaj komut
    sayılmaz, normal akışa (extraction) devam eder."""
    if not text:
        return None
    normalized = _normalize(text)
    for command, aliases in COMMAND_ALIASES.items():
        if normalized in aliases:
            return command
    return None


def _greeting(lead: Lead) -> str:
    return f"Merhaba {lead.contact_name}," if lead.contact_name else "Merhaba,"


def build_usage_message(office: Office, lead: Lead) -> str:
    return (
        f"{_greeting(lead)} {office.name} dijital asistanına hoş geldiniz. 👋\n\n"
        "Aradığınız portföyü tek mesajda yazmanız yeterli — bölge, oda sayısı, "
        "bütçe ve satılık/kiralık bilgisini ekleyin. Örnek:\n"
        "\"Kadıköy'de satılık 3+1 arıyorum, bütçem 5 milyon TL\"\n\n"
        "Kısayollar:\n"
        "• İLANLAR — kriterlerinize uyan portföyleri görün\n"
        "• DURUM — kayıtlı arama kriterlerinizi görün\n"
        "• DANIŞMAN — danışmanımız sizinle iletişime geçsin\n"
        "• MENÜ — bu mesajı tekrar görün"
    )


def _format_try(amount: float) -> str:
    return f"{amount:,.0f} TL".replace(",", ".")


def _has_criteria(lead: Lead) -> bool:
    return any(
        value is not None and value != ""
        for value in (
            lead.district,
            lead.budget_max,
            lead.room_count,
            lead.listing_type_preference,
            lead.property_type_preference,
        )
    )


def _criteria_summary(lead: Lead) -> str:
    listing_type_labels = {"sale": "satılık", "rent": "kiralık"}
    property_type_labels = {"residential": "konut", "commercial": "iş yeri", "land": "arsa"}
    parts = []
    if lead.district:
        parts.append(f"bölge: {lead.district}")
    if lead.room_count:
        parts.append(f"oda: {lead.room_count}")
    if lead.budget_max:
        parts.append(f"bütçe: {_format_try(float(lead.budget_max))}'ye kadar")
    if lead.listing_type_preference:
        parts.append(listing_type_labels.get(lead.listing_type_preference, lead.listing_type_preference))
    if lead.property_type_preference:
        parts.append(property_type_labels.get(lead.property_type_preference, lead.property_type_preference))
    return ", ".join(parts)


def _lead_to_match_state(lead: Lead) -> dict:
    # app/api/routes/leads.py: _lead_to_match_state ile aynı — route modülünü
    # import etmek döngüsel bağımlılık yaratacağı için elle senkron tutuluyor
    # (LEAD_STATUSES'taki desenle aynı gerekçe, bkz. CLAUDE.md).
    return {
        "office_id": str(lead.office_id),
        "lead_id": str(lead.id),
        "budget_min": float(lead.budget_min) if lead.budget_min else None,
        "budget_max": float(lead.budget_max) if lead.budget_max else None,
        "room_count": lead.room_count,
        "district": lead.district,
        "radius_km": float(lead.radius_km) if lead.radius_km else None,
        "listing_type_preference": lead.listing_type_preference,
        "property_type_preference": lead.property_type_preference,
    }


def _find_matches(db: Session, lead: Lead) -> list[dict]:
    """Kural bazlı Matching Agent sonuçları (en iyi MAX_AUTO_MATCHES). Bilinçli
    olarak AI yeniden sıralama (rerank_candidates_with_ai) YOK — otomatik akış
    her gelen mesajda çalışabildiği için Gemini maliyeti tek çağrıyla (varsa
    kişisel metin, bkz. build_auto_reply) sınırlı tutulur."""
    graph = build_matching_graph(db)
    result = graph.invoke(_lead_to_match_state(lead))
    return (result.get("candidate_listings") or [])[:MAX_AUTO_MATCHES]


def _matches_message(office: Office, lead: Lead, matches: list[dict]) -> str:
    lines = [f"{_greeting(lead)} {office.name} portföylerinden kriterlerinize uyanlar:"]
    for i, match in enumerate(matches, start=1):
        lines.append(f"{i}) {match['title']} — {_format_try(match['price'])}")
    lines.append("Detay ve yer gösterimi için DANIŞMAN yazmanız yeterli.")
    return "\n".join(lines)


def _command_reply(db: Session, office: Office, lead: Lead, command: str) -> str:
    if command == "menu":
        return build_usage_message(office, lead)

    if command == "status":
        summary = _criteria_summary(lead)
        if not summary:
            return (
                f"{_greeting(lead)} henüz kayıtlı bir arama kriteriniz yok. "
                "Bölge, oda sayısı ve bütçenizi tek mesajda yazmanız yeterli — "
                "örnek: \"Kadıköy'de satılık 3+1, bütçem 5 milyon TL\"."
            )
        return (
            f"{_greeting(lead)} kayıtlı arama kriterleriniz: {summary}.\n"
            "Güncellemek için yeni kriterlerinizi yazmanız yeterli; "
            "uygun portföyleri görmek için İLANLAR yazın."
        )

    if command == "agent":
        return (
            f"{_greeting(lead)} talebinizi danışmanımıza ilettik — en kısa sürede "
            "sizinle iletişime geçecek. İyi günler dileriz!"
        )

    # command == "listings"
    if not _has_criteria(lead):
        return (
            f"{_greeting(lead)} size uygun portföyleri bulabilmemiz için önce "
            "kriterlerinizi yazın — örnek: \"Kadıköy'de satılık 3+1, bütçem 5 milyon TL\"."
        )
    matches = _find_matches(db, lead)
    if not matches:
        return (
            f"{_greeting(lead)} şu an kriterlerinize birebir uyan bir portföyümüz yok. "
            "Kriterlerinize uygun yeni bir portföy geldiğinde danışmanımız size haber verecek."
        )
    return _matches_message(office, lead, matches)


def _match_send_reply(db: Session, office: Office, lead: Lead) -> str:
    matches = _find_matches(db, lead)
    if not matches:
        summary = _criteria_summary(lead)
        return (
            f"{_greeting(lead)} kriterlerinizi aldık ({summary}). Şu an birebir uyan "
            "portföyümüz yok; uygun bir portföy geldiğinde danışmanımız size ulaşacak. "
            "Dilerseniz DANIŞMAN yazarak hemen görüşme talep edebilirsiniz."
        )
    try:
        draft = draft_reply(
            last_message=None,
            district=lead.district,
            room_count=lead.room_count,
            budget_max=float(lead.budget_max) if lead.budget_max else None,
            candidate_listings=matches,
        )
        return f"{draft}\n\nDetay ve yer gösterimi için DANIŞMAN yazmanız yeterli."
    except ReplyDraftError:
        return _matches_message(office, lead, matches)


def build_auto_reply(
    db: Session,
    office: Office,
    lead: Lead,
    *,
    command: str | None,
    is_new_lead: bool,
    fields_updated: bool,
) -> list[str]:
    """Gönderilecek otomatik yanıt mesajlarını sırasıyla döner; boş liste =
    sessiz kal (maliyet kalkanı: tanınmayan/İlgisiz mesajlara yanıt da
    üretilmez). Çağıran taraf (intake._maybe_auto_reply) tenant context'i set
    etmiş olmalı — Matching Agent RLS'li listings tablosunu okur.

    Yeni bir adayın kullanım bilgisini HİÇBİR ZAMAN kaçırmaması için: ilk
    temas her koşulda sabit karşılama+kısayol mesajını alır — aday ilk
    mesajında zaten kriter verip doğrudan eşleşme aldığında bile (önceden bu
    durumda karşılama hiç gönderilmiyordu, aday kısayolları hiç öğrenmiyordu).
    """
    messages: list[str] = []

    if is_new_lead:
        messages.append(build_usage_message(office, lead))

    if command:
        # MENÜ zaten karşılama mesajıyla birebir aynı içerik — yeni adaya iki
        # kez göndermenin bir anlamı yok.
        if not (is_new_lead and command == "menu"):
            messages.append(_command_reply(db, office, lead, command))
    elif fields_updated and _has_criteria(lead):
        messages.append(_match_send_reply(db, office, lead))

    return messages
