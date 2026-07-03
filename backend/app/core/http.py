import httpx

REQUEST_TIMEOUT_SECONDS = 10.0
USER_AGENT = "PortfoyAI/1.0 (+https://github.com/omertoycu/YZTA-BOOTCAMP)"


def get_http_client() -> httpx.Client:
    """Dış servislere (Sahibinden sayfa çekme, Nominatim geocoding) yapılan tüm
    outbound isteklerin ortak istemcisi — timeout ve User-Agent tutarlı olsun diye."""
    return httpx.Client(
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )
