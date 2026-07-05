import uuid
from datetime import datetime, timedelta, timezone


def _escape_ics_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def _format_ics_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_appointment_ics(
    summary: str,
    location: str,
    start: datetime,
    duration_minutes: int = 60,
    description: str = "",
    uid: str | None = None,
) -> bytes:
    """Tek bir VEVENT içeren minimal, standart bir .ics dosyası üretir (RFC 5545) —
    yer gösterme randevusu için harici bir kütüphaneye gerek yok, format sabit ve
    basit. Danışman ya da aday kendi takvim uygulamasına (Google Calendar, Outlook,
    Apple Calendar) tek tıkla ekleyebilir."""
    now = datetime.now(timezone.utc)
    end = start + timedelta(minutes=duration_minutes)
    event_uid = uid or f"{uuid.uuid4()}@portfoyai.app"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PortfoyAI//Appointment//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{event_uid}",
        f"DTSTAMP:{_format_ics_datetime(now)}",
        f"DTSTART:{_format_ics_datetime(start)}",
        f"DTEND:{_format_ics_datetime(end)}",
        f"SUMMARY:{_escape_ics_text(summary)}",
    ]
    if description:
        lines.append(f"DESCRIPTION:{_escape_ics_text(description)}")
    if location:
        lines.append(f"LOCATION:{_escape_ics_text(location)}")
    lines += ["END:VEVENT", "END:VCALENDAR"]

    # RFC 5545: satırlar CRLF ile ayrılır.
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")
