from datetime import datetime, timezone

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


def _format_turkish_price(price: float) -> str:
    return f"{price:,.0f}".replace(",", ".") + " TL"


def render_report_pdf(
    office_name: str,
    listing_title: str,
    listing_district: str,
    target_label: str,
    travel_summary: list[dict],
    listing_price: float | None = None,
    listing_room_count: str | None = None,
    listing_square_meters: int | None = None,
    listing_type: str | None = None,
    logo_data_uri: str | None = None,
    generated_at: datetime | None = None,
) -> bytes:
    """Markalı ulaşım raporu. Ofisin kendi logosu varsa (base64 data URI olarak
    gömülü — WeasyPrint'in dış istek atmasına gerek kalmaz) başlıkta gösterilir;
    ilan detayları (fiyat, oda, m², satılık/kiralık) ayrı bir özet kartında yer
    alır. Tüm parametreler geriye dönük opsiyonel: eski çağıranlar sadece
    başlık+bölge verse de rapor üretmeye devam eder."""
    generated_at = generated_at or datetime.now(timezone.utc)

    rows = "".join(
        f"<tr><td>{item['label']}</td>"
        f"<td>{item['result']['duration'] if item['result'] else 'Bu güzergah için bilgi yok'}</td>"
        f"<td>{item['result']['distance'] if item['result'] else '-'}</td></tr>"
        for item in travel_summary
    )

    logo_html = (
        f'<img class="logo" src="{logo_data_uri}" alt=""/>' if logo_data_uri else ""
    )

    facts = []
    if listing_type in ("sale", "rent"):
        facts.append(("İlan Tipi", "Satılık" if listing_type == "sale" else "Kiralık"))
    if listing_price is not None:
        price_label = _format_turkish_price(listing_price)
        if listing_type == "rent":
            price_label += " / ay"
        facts.append(("Fiyat", price_label))
    if listing_room_count:
        facts.append(("Oda Sayısı", listing_room_count))
    if listing_square_meters:
        facts.append(("Metrekare", f"{listing_square_meters} m²"))
    facts_html = "".join(
        f'<div class="fact"><p class="fact-label">{label}</p><p class="fact-value">{value}</p></div>'
        for label, value in facts
    )
    facts_block = f'<div class="facts">{facts_html}</div>' if facts_html else ""

    html = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      body {{ font-family: sans-serif; color: #191c1d; padding: 48px; }}
      .header {{ display: flex; align-items: center; justify-content: space-between;
                 border-bottom: 3px solid #006875; padding-bottom: 16px; }}
      .logo {{ max-height: 56px; max-width: 180px; }}
      .eyebrow {{ font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
                  font-size: 11px; color: #64748B; margin: 0; }}
      .office-name {{ font-size: 20px; font-weight: 700; color: #006875; margin: 2px 0 0 0; }}
      h1 {{ color: #006875; margin: 28px 0 6px 0; }}
      .subtitle {{ font-size: 15px; color: #45464d; margin: 2px 0; }}
      .facts {{ display: flex; gap: 12px; margin-top: 20px; }}
      .fact {{ flex: 1; background: #f0f5f5; border-radius: 10px; padding: 12px 14px; }}
      .fact-label {{ font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase;
                     color: #64748B; margin: 0 0 4px 0; }}
      .fact-value {{ font-size: 15px; font-weight: 700; color: #191c1d; margin: 0; }}
      h2 {{ font-size: 13px; letter-spacing: 0.06em; text-transform: uppercase;
            color: #64748B; margin: 32px 0 0 0; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
      th {{ text-align: left; padding: 10px; font-size: 12px; letter-spacing: 0.05em;
            text-transform: uppercase; color: #64748B; border-bottom: 2px solid #e1e3e4; }}
      td {{ text-align: left; padding: 12px 10px; border-bottom: 1px solid #e1e3e4; font-size: 14px; }}
      .footer {{ margin-top: 48px; font-size: 11px; color: #64748B;
                 border-top: 1px solid #e1e3e4; padding-top: 12px;
                 display: flex; justify-content: space-between; }}
    </style>
    </head>
    <body>
      <div class="header">
        <div>
          <p class="eyebrow">Markalı Ulaşım Raporu</p>
          <p class="office-name">{office_name}</p>
        </div>
        {logo_html}
      </div>
      <h1>{listing_title}</h1>
      <p class="subtitle">{listing_district}</p>
      <p class="subtitle">Hedef adres: <strong>{target_label}</strong></p>
      {facts_block}
      <h2>Ulaşım Süreleri</h2>
      <table>
        <tr><th>Ulaşım Şekli</th><th>Süre</th><th>Mesafe</th></tr>
        {rows}
      </table>
      <div class="footer">
        <span>{office_name} — PortföyAI ile oluşturulmuştur.</span>
        <span>{generated_at.strftime("%d.%m.%Y")}</span>
      </div>
    </body>
    </html>
    """
    return HTML(string=html).write_pdf()
