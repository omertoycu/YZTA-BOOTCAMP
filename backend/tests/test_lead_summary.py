"""Hibrit aday özeti (app/agents/lead_summary.py) birim testleri — DB'siz,
Lead nesnesi elle kurulur (mapped_column default'ları flush'ta uygulanır,
testte alanlar açıkça set edilir)."""

from datetime import datetime, timedelta, timezone

from app.agents.lead_summary import (
    LLM_SUMMARY_MIN_MESSAGES,
    build_structured_summary,
    fresh_cached_summary,
    should_generate_llm_summary,
)
from app.models.lead import Lead

NOW = datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc)


def _lead(**overrides) -> Lead:
    lead = Lead(contact_phone="5550000000")
    defaults = {
        "district": None,
        "budget_max": None,
        "room_count": None,
        "listing_type_preference": None,
        "property_type_preference": None,
        "message_count": 0,
        "conversation_summary": None,
        "conversation_summary_at": None,
        "llm_extraction_count": 0,
        "last_llm_extraction_at": None,
    }
    defaults.update(overrides)
    for field, value in defaults.items():
        setattr(lead, field, value)
    return lead


def test_structured_summary_composes_single_sentence():
    lead = _lead(district="Nilüfer", budget_max=20_000, room_count="3+1", listing_type_preference="rent")
    summary = build_structured_summary(lead)
    assert summary == "Müşteri Nilüfer'de 20.000 TL'ye kadar 3+1 kiralık arıyor."


def test_structured_summary_partial_fields():
    lead = _lead(district="Kadıköy")
    assert build_structured_summary(lead) == "Müşteri Kadıköy'de arıyor."


def test_structured_summary_none_when_no_fields():
    assert build_structured_summary(_lead()) is None


def test_llm_summary_not_needed_when_structured_exists():
    lead = _lead(district="Moda", message_count=20)
    assert should_generate_llm_summary(lead, now=NOW) is False


def test_llm_summary_requires_long_conversation():
    lead = _lead(message_count=LLM_SUMMARY_MIN_MESSAGES - 1)
    assert should_generate_llm_summary(lead, now=NOW) is False
    lead.message_count = LLM_SUMMARY_MIN_MESSAGES
    assert should_generate_llm_summary(lead, now=NOW) is True


def test_llm_summary_skipped_when_cache_fresh():
    lead = _lead(
        message_count=10,
        conversation_summary="Müşteri deniz manzaralı bir şey arıyor.",
        conversation_summary_at=NOW - timedelta(hours=1),
    )
    assert should_generate_llm_summary(lead, now=NOW) is False
    assert fresh_cached_summary(lead, now=NOW) == "Müşteri deniz manzaralı bir şey arıyor."


def test_llm_summary_regenerated_when_cache_stale():
    lead = _lead(
        message_count=10,
        conversation_summary="Eski özet",
        conversation_summary_at=NOW - timedelta(hours=48),
    )
    assert fresh_cached_summary(lead, now=NOW) is None
    assert should_generate_llm_summary(lead, now=NOW) is True


def test_llm_summary_respects_shared_extraction_budget():
    lead = _lead(message_count=10, llm_extraction_count=5, last_llm_extraction_at=NOW - timedelta(hours=1))
    assert should_generate_llm_summary(lead, now=NOW) is False
    # Pencere dolmuşsa (24 saatten eski) sayaç sıfırdan sayılır.
    lead.last_llm_extraction_at = NOW - timedelta(hours=30)
    assert should_generate_llm_summary(lead, now=NOW) is True
