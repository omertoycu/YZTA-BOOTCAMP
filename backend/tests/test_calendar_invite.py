from datetime import datetime, timezone

from app.agents.calendar_invite import build_appointment_ics


def test_build_appointment_ics_contains_required_fields():
    start = datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc)
    ics = build_appointment_ics(
        summary="Yer Gösterimi — 5551234567",
        location="Kadıköy, İstanbul",
        start=start,
    )
    text = ics.decode("utf-8")

    assert text.startswith("BEGIN:VCALENDAR\r\n")
    assert text.rstrip().endswith("END:VCALENDAR")
    assert "BEGIN:VEVENT" in text
    assert "DTSTART:20260710T140000Z" in text
    assert "DTEND:20260710T150000Z" in text
    assert "SUMMARY:Yer Gösterimi — 5551234567" in text
    assert "LOCATION:Kadıköy\\, İstanbul" in text


def test_build_appointment_ics_escapes_special_characters():
    start = datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc)
    ics = build_appointment_ics(
        summary="Test; özel, karakter\nyeni satır",
        location="",
        start=start,
    )
    text = ics.decode("utf-8")
    assert "Test\\; özel\\, karakter\\nyeni satır" in text
    assert "LOCATION:" not in text  # boş konum satırı hiç eklenmemeli
