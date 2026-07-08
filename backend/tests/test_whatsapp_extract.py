from datetime import datetime, timedelta, timezone

import pytest

from app.agents import whatsapp_extract
from app.agents.whatsapp_extract import (
    MAX_EXTRACTIONS_PER_24H,
    WhatsAppExtractError,
    compute_new_extraction_counters,
    extract_lead_fields,
    is_message_trivial,
    should_run_extraction,
)

NOW = datetime(2026, 7, 6, 12, 0, 0, tzinfo=timezone.utc)


def _base_kwargs(**overrides):
    kwargs = dict(
        message_type="text",
        message_body="Kadıköy'de 3+1 arıyorum, bütçem 5 milyon TL civarı",
        district=None,
        budget_max=None,
        room_count=None,
        extraction_count=0,
        last_extraction_at=None,
        now=NOW,
    )
    kwargs.update(overrides)
    return kwargs


def test_should_run_extraction_skips_non_text_message():
    assert should_run_extraction(**_base_kwargs(message_type="image")) is False


def test_should_run_extraction_skips_short_message():
    assert should_run_extraction(**_base_kwargs(message_body="Merhaba")) is False


def test_should_run_extraction_skips_greeting_denylist_exact_match():
    assert should_run_extraction(**_base_kwargs(message_body="Teşekkürler")) is False


def test_should_run_extraction_does_not_skip_message_containing_greeting_as_substring():
    assert should_run_extraction(**_base_kwargs(message_body="merhaba, Kadıköy'de 3+1 arıyorum")) is True


def test_should_run_extraction_skips_emoji_only_message():
    assert should_run_extraction(**_base_kwargs(message_body="👍👍👍")) is False


def test_should_run_extraction_skips_when_all_three_fields_already_filled():
    assert (
        should_run_extraction(
            **_base_kwargs(district="Kadıköy", budget_max=5_000_000, room_count="3+1")
        )
        is False
    )


def test_should_run_extraction_force_bypasses_already_filled_check():
    assert (
        should_run_extraction(
            **_base_kwargs(district="Kadıköy", budget_max=5_000_000, room_count="3+1", force=True)
        )
        is True
    )


def test_should_run_extraction_force_still_respects_rate_cap():
    assert (
        should_run_extraction(
            **_base_kwargs(
                district="Kadıköy",
                budget_max=5_000_000,
                room_count="3+1",
                force=True,
                extraction_count=MAX_EXTRACTIONS_PER_24H,
                last_extraction_at=NOW,
            )
        )
        is False
    )


def test_should_run_extraction_respects_rate_cap_without_force():
    assert (
        should_run_extraction(
            **_base_kwargs(extraction_count=MAX_EXTRACTIONS_PER_24H, last_extraction_at=NOW)
        )
        is False
    )


def test_extractions_in_window_resets_after_24h():
    old = NOW - timedelta(hours=25)
    assert (
        should_run_extraction(
            **_base_kwargs(extraction_count=MAX_EXTRACTIONS_PER_24H, last_extraction_at=old)
        )
        is True
    )


def test_compute_new_extraction_counters_increments_within_window():
    count, when = compute_new_extraction_counters(2, NOW - timedelta(hours=1), now=NOW)
    assert count == 3
    assert when == NOW


def test_compute_new_extraction_counters_resets_after_window():
    count, when = compute_new_extraction_counters(5, NOW - timedelta(hours=25), now=NOW)
    assert count == 1
    assert when == NOW


def test_is_message_trivial_none_and_empty():
    assert is_message_trivial(None) is True
    assert is_message_trivial("") is True
    assert is_message_trivial("   ") is True


def test_extract_lead_fields_parses_valid_response(monkeypatch):
    def _fake_generate_content(self, prompt, generation_config=None):
        class _Resp:
            text = (
                '{"district": "Kadıköy", "budget_min": null, "budget_max": 5000000, '
                '"room_count": "3+1", "radius_km": null}'
            )

        return _Resp()

    monkeypatch.setattr(whatsapp_extract.settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr("google.generativeai.configure", lambda **kwargs: None)
    monkeypatch.setattr("google.generativeai.GenerativeModel.generate_content", _fake_generate_content)

    result = extract_lead_fields("Kadıköy'de 3+1 arıyorum, bütçem 5 milyon TL")
    assert result["district"] == "Kadıköy"
    assert result["budget_max"] == 5000000
    assert result["room_count"] == "3+1"


def test_extract_lead_fields_parses_listing_and_property_type_preference(monkeypatch):
    """Gerçek prod hatası (kullanıcı bildirdi): sistem kiralık/satılık ve
    konut/iş yeri/arsa ayrımını hiç bilmiyordu — bu iki alan artık Gemini
    şemasının bir parçası."""
    def _fake_generate_content(self, prompt, generation_config=None):
        class _Resp:
            text = (
                '{"district": "Osmangazi", "budget_min": null, "budget_max": null, '
                '"room_count": null, "radius_km": null, "listing_type_preference": "rent", '
                '"property_type_preference": "commercial"}'
            )

        return _Resp()

    monkeypatch.setattr(whatsapp_extract.settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr("google.generativeai.configure", lambda **kwargs: None)
    monkeypatch.setattr("google.generativeai.GenerativeModel.generate_content", _fake_generate_content)

    result = extract_lead_fields("Osmangazi'de kiralık bir iş yeri arıyorum")
    assert result["listing_type_preference"] == "rent"
    assert result["property_type_preference"] == "commercial"


def test_extract_lead_fields_raises_not_configured_without_api_key(monkeypatch):
    monkeypatch.setattr(whatsapp_extract.settings, "gemini_api_key", None)
    with pytest.raises(WhatsAppExtractError, match="__not_configured__"):
        extract_lead_fields("Kadıköy'de 3+1 arıyorum")


def test_extract_lead_fields_raises_on_invalid_json(monkeypatch):
    def _fake_generate_content(self, prompt, generation_config=None):
        class _Resp:
            text = "not json at all"

        return _Resp()

    monkeypatch.setattr(whatsapp_extract.settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr("google.generativeai.configure", lambda **kwargs: None)
    monkeypatch.setattr("google.generativeai.GenerativeModel.generate_content", _fake_generate_content)

    with pytest.raises(WhatsAppExtractError):
        extract_lead_fields("Kadıköy'de 3+1 arıyorum")
