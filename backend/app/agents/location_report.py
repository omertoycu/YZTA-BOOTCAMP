import httpx
from weasyprint import HTML

from app.core.config import settings
from app.core.http import get_http_client

DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

TRAVEL_MODES = [
    ("driving", "Araçla"),
    ("walking", "Yürüyerek"),
    ("transit", "Toplu Taşıma ile"),
]


class LocationReportError(Exception):
    """Rapor üretilemedi (yapılandırma eksik, Maps API hatası)."""


def _get_directions(client: httpx.Client, origin: str, destination: str, mode: str) -> dict | None:
    response = client.get(
        DIRECTIONS_URL,
        params={
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "key": settings.google_maps_api_key,
        },
    )
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "OK" or not data.get("routes"):
        # Bu ulaşım modu için rota bulunamadı (örn. toplu taşıma seçeneği yoksa) —
        # best-effort: diğer modlar denenmeye devam eder, tüm işlem başarısız sayılmaz.
        return None

    leg = data["routes"][0]["legs"][0]
    return {"duration": leg["duration"]["text"], "distance": leg["distance"]["text"]}


def get_travel_summary(origin: str, destination: str) -> list[dict]:
    """Bir adresten (origin) hedefe (destination) araç/yürüyüş/toplu taşıma
    sürelerini döner. origin/destination serbest metin adres olabilir —
    Google Directions API kendi içinde geocode ediyor, ayrıca Nominatim'e
    gerek yok."""
    if not settings.google_maps_api_key:
        raise LocationReportError("__not_configured__")

    try:
        with get_http_client() as client:
            return [
                {"mode": mode, "label": label, "result": _get_directions(client, origin, destination, mode)}
                for mode, label in TRAVEL_MODES
            ]
    except httpx.TimeoutException as exc:
        raise LocationReportError("Google Maps zaman aşımına uğradı, tekrar deneyin.") from exc
    except httpx.HTTPStatusError as exc:
        raise LocationReportError(f"Google Maps hata döndürdü (durum kodu {exc.response.status_code}).") from exc
    except httpx.RequestError as exc:
        raise LocationReportError("Google Maps'e ulaşılamadı, tekrar deneyin.") from exc


def render_report_pdf(
    office_name: str,
    listing_title: str,
    listing_district: str,
    target_label: str,
    travel_summary: list[dict],
) -> bytes:
    rows = "".join(
        f"<tr><td>{item['label']}</td>"
        f"<td>{item['result']['duration'] if item['result'] else 'Bu güzergah için bilgi yok'}</td>"
        f"<td>{item['result']['distance'] if item['result'] else '-'}</td></tr>"
        for item in travel_summary
    )
    html = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      body {{ font-family: sans-serif; color: #191c1d; padding: 48px; }}
      .eyebrow {{ font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
                  font-size: 11px; color: #64748B; }}
      h1 {{ color: #006875; margin: 6px 0 24px 0; }}
      .subtitle {{ font-size: 15px; color: #45464d; margin-bottom: 4px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 28px; }}
      th {{ text-align: left; padding: 10px; font-size: 12px; letter-spacing: 0.05em;
            text-transform: uppercase; color: #64748B; border-bottom: 2px solid #e1e3e4; }}
      td {{ text-align: left; padding: 12px 10px; border-bottom: 1px solid #e1e3e4; font-size: 14px; }}
      .footer {{ margin-top: 48px; font-size: 11px; color: #64748B; }}
    </style>
    </head>
    <body>
      <p class="eyebrow">{office_name}</p>
      <h1>Ulaşım Raporu</h1>
      <p class="subtitle"><strong>{listing_title}</strong> — {listing_district}</p>
      <p class="subtitle">Hedef: {target_label}</p>
      <table>
        <tr><th>Ulaşım Şekli</th><th>Süre</th><th>Mesafe</th></tr>
        {rows}
      </table>
      <p class="footer">PortföyAI ile oluşturulmuştur.</p>
    </body>
    </html>
    """
    return HTML(string=html).write_pdf()
