import json
import re

import google.generativeai as genai

from app.core.ai_limits import MAX_TOKENS_RERANK
from app.core.config import settings

MODEL_NAME = "gemini-2.5-flash"

PROMPT_TEMPLATE = """Sen bir emlak ofisinin eşleştirme sistemisin. Kural bazlı filtreden zaten \
geçmiş (bölge/bütçe/tip uygunluğu) aşağıdaki portföyleri, adayın ORİJİNAL mesajını ve \
başlıklarındaki nüansları (eş anlamlılar, yazım farkları, örtük bilgi) dikkate alarak \
yeniden değerlendireceksin.

Adayın orijinal mesajı: "{original_message}"
Yapılandırılmış kriterler: {criteria_block}

Her portföy için 0-100 arası bir uygunluk skoru ve kısa bir gerekçe ver. Portföyün başlığı \
adayın gerçekte aradığıyla çelişiyorsa (ör. "iş yeri" ararken "daire" ilanı, "kiralık" ararken \
"satılık" ilan) düşük puan ver; başlık adayın mesajındaki detaylarla (ör. sokak/cadde adı, \
mahalle) örtüşüyorsa yüksek puan ver.

Portföyler:
{listings_block}

SADECE aşağıdaki JSON şemasına uygun bir dizi döndür, başka hiçbir metin/markdown ekleme:
[{{"index": <portföy numarası>, "relevance_score": <0-100 tam sayı>, "reason": "<kısa Türkçe gerekçe, en fazla 15 kelime>"}}]"""


class MatchRankingError(Exception):
    """Yeniden sıralama yapılamadı (yapılandırma eksik, LLM hatası, geçersiz yanıt)."""


def _get_model() -> "genai.GenerativeModel":
    if not settings.gemini_api_key:
        raise MatchRankingError("__not_configured__")
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(MODEL_NAME)


def _format_try(amount: float) -> str:
    return f"{amount:,.0f} TL".replace(",", ".")


def _parse_json_response(text: str) -> list:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise MatchRankingError("Model yanıtı beklenen dizi biçiminde değil")
    return data


def rerank_candidates_with_ai(
    *, original_message: str | None, criteria: dict, candidates: list[dict]
) -> list[dict]:
    """Matching Agent'ın kural-bazlı filtreden geçirdiği adayları (bkz.
    app/agents/matching.py) adayın orijinal mesajı + ilan başlıklarını
    birlikte değerlendirerek yeniden sıralar; her adaya 0-100 bir
    relevance_score + zenginleştirilmiş match_reason ekler.

    Tamamen best-effort: Gemini yapılandırılmamışsa ya da HERHANGİ bir hata
    oluşursa (ağ, geçersiz JSON, beklenmeyen şema) candidates HİÇ
    DEĞİŞTİRİLMEDEN (relevance_score=None ile, kural-bazlı sıra ve gerekçe
    korunarak) döner — bu katman hiçbir çağıran route'u kıramaz (aynı desen:
    app/agents/reply_draft.py, app/agents/whatsapp_extract.py)."""
    if not candidates:
        return candidates

    try:
        model = _get_model()
        listings_block = "\n".join(
            f"{i}. {c['title']} — {_format_try(c['price'])} ({c.get('match_reason', '')})"
            for i, c in enumerate(candidates, start=1)
        )
        criteria_block = (
            ", ".join(f"{key}={value}" for key, value in criteria.items() if value is not None)
            or "belirtilmedi"
        )
        prompt = PROMPT_TEMPLATE.format(
            original_message=original_message or "(mesaj yok)",
            criteria_block=criteria_block,
            listings_block=listings_block,
        )
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "max_output_tokens": MAX_TOKENS_RERANK,
            },
        )
        text = getattr(response, "text", None)
        if not text:
            raise MatchRankingError("Modelden yanıt alınamadı")
        scored_items = _parse_json_response(text)
    except Exception:  # best-effort: her hata türünde kural-bazlı sıraya sessizce düşülür
        return candidates

    scores_by_index = {
        item["index"]: item
        for item in scored_items
        if isinstance(item, dict) and isinstance(item.get("index"), int)
    }

    ranked = []
    for i, candidate in enumerate(candidates, start=1):
        item = scores_by_index.get(i)
        enriched = dict(candidate)
        if item:
            score = item.get("relevance_score")
            reason = item.get("reason")
            if isinstance(score, (int, float)):
                enriched["relevance_score"] = max(0, min(100, round(score)))
            if reason:
                enriched["match_reason"] = f"{candidate['match_reason']} — {reason}"
        ranked.append(enriched)

    ranked.sort(
        key=lambda c: c["relevance_score"] if c.get("relevance_score") is not None else -1,
        reverse=True,
    )
    return ranked
