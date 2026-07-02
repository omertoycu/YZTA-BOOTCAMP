from datetime import timezone

from app.models.lead import Lead

RESPONSE_WEIGHT = 0.4
MESSAGE_COUNT_WEIGHT = 0.3
BUDGET_CONSISTENCY_WEIGHT = 0.3

MAX_RESPONSE_WINDOW_MINUTES = 24 * 60
MAX_SCORED_MESSAGES = 10
MAX_REASONABLE_BUDGET_SPREAD_RATIO = 0.5


def _response_speed_score(lead: Lead) -> float:
    """Sprint 1'de henüz gerçek konuşma geçmişi yok (WhatsApp Intake Agent Sprint 2'de
    gelecek); last_contacted_at hiç set edilmemişse lead hiç yanıtlanmamış sayılır."""
    if lead.last_contacted_at is None:
        return 0.0

    created_at = lead.created_at
    last_contacted = lead.last_contacted_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    if last_contacted.tzinfo is None:
        last_contacted = last_contacted.replace(tzinfo=timezone.utc)

    elapsed_minutes = max((last_contacted - created_at).total_seconds() / 60, 0)
    capped_minutes = min(elapsed_minutes, MAX_RESPONSE_WINDOW_MINUTES)
    return 100 * (1 - capped_minutes / MAX_RESPONSE_WINDOW_MINUTES)


def _message_count_score(lead: Lead) -> float:
    return 100 * min(lead.message_count, MAX_SCORED_MESSAGES) / MAX_SCORED_MESSAGES


def _budget_consistency_score(lead: Lead) -> float:
    """Türkiye emlak verisinde eksik/tutarsız bütçe girişi yaygın (bkz. Girişim
    Analizi Raporu Bölüm 0) — bu yüzden eksik veri de düşük puanlanır, sadece
    mantıksız (min > max) veri değil."""
    if lead.budget_min is None and lead.budget_max is None:
        return 0.0
    if lead.budget_min is None or lead.budget_max is None:
        return 40.0  # tek taraflı bütçe bilgisi: eksik ama yararlı bir sinyal
    budget_min, budget_max = float(lead.budget_min), float(lead.budget_max)
    if budget_min > budget_max or budget_max <= 0:
        return 0.0

    spread_ratio = (budget_max - budget_min) / budget_max
    if spread_ratio <= MAX_REASONABLE_BUDGET_SPREAD_RATIO:
        return 100.0
    # Aralık ne kadar genişse (belirsizse) o kadar düşük puan, ama sıfıra inmez.
    return max(100 * (1 - spread_ratio), 20.0)


def calculate_lead_score(lead: Lead) -> tuple[int, dict]:
    """Kural bazlı skor: 0 (soğuk) - 100 (sıcak). ML değil — yeterli etiketli
    (dönüşen/dönüşmeyen) veri birikmeden bir ML modeline güvenmek Girişim Analizi
    Raporu'nun uyardığı güvenilmez sonuç riskini taşır."""
    response_score = _response_speed_score(lead)
    message_score = _message_count_score(lead)
    budget_score = _budget_consistency_score(lead)

    total = (
        RESPONSE_WEIGHT * response_score
        + MESSAGE_COUNT_WEIGHT * message_score
        + BUDGET_CONSISTENCY_WEIGHT * budget_score
    )
    breakdown = {
        "response_speed_score": round(response_score, 1),
        "message_count_score": round(message_score, 1),
        "budget_consistency_score": round(budget_score, 1),
        "weights": {
            "response_speed": RESPONSE_WEIGHT,
            "message_count": MESSAGE_COUNT_WEIGHT,
            "budget_consistency": BUDGET_CONSISTENCY_WEIGHT,
        },
    }
    return round(total), breakdown
