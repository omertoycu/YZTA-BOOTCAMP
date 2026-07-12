"""Eşleşme payload'ı temizleme + /p/{id} vitrin linkleri (app/agents/match_payload.py)."""

from app.agents.match_payload import (
    append_match_links,
    format_match_lines,
    public_listing_url,
    strip_match_payload,
)

CANDIDATE = {
    "listing_id": "11111111-1111-1111-1111-111111111111",
    "title": "Kadıköy'de 3+1 Daire",
    "price": 4_500_000.0,
    "room_count": "3+1",
    "district": "Kadıköy",
    "city": "İstanbul",
    "match_reason": "Kadıköy bölgesinde, bütçe ve oda sayısı kriterine uyuyor",
}


def test_public_listing_url_uses_frontend_base():
    url = public_listing_url(CANDIDATE["listing_id"])
    assert url.endswith(f"/p/{CANDIDATE['listing_id']}")
    assert "//p/" not in url.split("://", 1)[1]  # baz URL sonundaki / temizlenir


def test_strip_match_payload_reduces_to_clean_schema():
    payload = strip_match_payload(CANDIDATE)
    assert set(payload) == {"listing_id", "title", "price", "room_count", "location", "link", "match_reason"}
    assert payload["location"] == "Kadıköy/İstanbul"
    assert payload["link"].endswith(f"/p/{CANDIDATE['listing_id']}")


def test_format_match_lines_includes_details_and_link():
    lines = format_match_lines([CANDIDATE])
    assert lines[0] == "1) Kadıköy'de 3+1 Daire — 4.500.000 TL (3+1, Kadıköy/İstanbul)"
    assert lines[1].endswith(f"/p/{CANDIDATE['listing_id']}")


def test_format_match_lines_tolerates_missing_optional_fields():
    minimal = {"listing_id": "22222222-2222-2222-2222-222222222222", "title": "Arsa", "price": 900_000.0}
    lines = format_match_lines([minimal])
    assert lines[0] == "1) Arsa — 900.000 TL"
    assert "/p/2222" in lines[1]


def test_append_match_links_appends_deterministically():
    result = append_match_links("Merhaba, uygun seçeneklerimiz var.", [CANDIDATE])
    assert result.startswith("Merhaba, uygun seçeneklerimiz var.")
    assert f"/p/{CANDIDATE['listing_id']}" in result
    assert append_match_links("Taslak", []) == "Taslak"
