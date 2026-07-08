from app.agents import market_price_check
from app.models.listing import Listing


def _listing(**overrides):
    defaults = dict(
        title="BEGO GAYRİMENKULDEN ULUYOLA YAKIN 600 M2 KİRALIK İŞ YERİ",
        district="Osmangazi",
        price=30000.0,
        room_count="Belirtilmedi",
        square_meters=600,
        listing_type="rent",
        property_type="commercial",
    )
    defaults.update(overrides)
    return Listing(**defaults)


class _FakeWeb:
    def __init__(self, uri, title):
        self.uri = uri
        self.title = title


class _FakeChunk:
    def __init__(self, uri, title):
        self.web = _FakeWeb(uri, title)


class _FakeGroundingMetadata:
    def __init__(self, chunks):
        self.grounding_chunks = chunks


class _FakeCandidate:
    def __init__(self, chunks):
        self.grounding_metadata = _FakeGroundingMetadata(chunks)


class _FakeResponse:
    def __init__(self, text, chunks=None):
        self.text = text
        self.candidates = [_FakeCandidate(chunks or [])]


class _FakeModels:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error

    def generate_content(self, model=None, contents=None, config=None):
        if self._error:
            raise self._error
        return self._response


class _FakeClient:
    def __init__(self, response=None, error=None):
        self.models = _FakeModels(response=response, error=error)


def test_fetch_market_price_check_parses_range_and_sources(monkeypatch):
    monkeypatch.setattr(market_price_check.settings, "gemini_api_key", "fake-key")
    response = _FakeResponse(
        text="ALT_SINIR: 25.000\nUST_SINIR: 35.000\nOZET: Bulunan ilanlara göre bu bölgede benzer iş yerleri bu aralıkta.",
        chunks=[_FakeChunk("https://example.com/ilan-1", "Örnek Emlak Sitesi")],
    )
    monkeypatch.setattr(market_price_check.genai, "Client", lambda api_key: _FakeClient(response=response))

    result = market_price_check.fetch_market_price_check(_listing())

    assert result["has_market_data"] is True
    assert result["estimated_min"] == 25000.0
    assert result["estimated_max"] == 35000.0
    assert "bölgede" in result["summary"]
    assert result["sources"] == [{"title": "Örnek Emlak Sitesi", "url": "https://example.com/ilan-1"}]


def test_fetch_market_price_check_returns_no_data_when_not_configured(monkeypatch):
    monkeypatch.setattr(market_price_check.settings, "gemini_api_key", None)

    result = market_price_check.fetch_market_price_check(_listing())

    assert result["has_market_data"] is False
    assert result["estimated_min"] is None
    assert result["sources"] == []


def test_fetch_market_price_check_returns_no_data_on_gemini_error(monkeypatch):
    monkeypatch.setattr(market_price_check.settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr(
        market_price_check.genai, "Client", lambda api_key: _FakeClient(error=RuntimeError("boom"))
    )

    result = market_price_check.fetch_market_price_check(_listing())

    assert result["has_market_data"] is False
    assert result["summary"] == "Web'den piyasa verisi alınamadı, tekrar deneyin."


def test_fetch_market_price_check_returns_no_data_when_model_says_unknown(monkeypatch):
    monkeypatch.setattr(market_price_check.settings, "gemini_api_key", "fake-key")
    response = _FakeResponse(text="ALT_SINIR: BILINMIYOR\nUST_SINIR: BILINMIYOR\nOZET: Yeterli veri bulunamadı.")
    monkeypatch.setattr(market_price_check.genai, "Client", lambda api_key: _FakeClient(response=response))

    result = market_price_check.fetch_market_price_check(_listing())

    assert result["has_market_data"] is False
    assert result["estimated_min"] is None
    assert result["estimated_max"] is None
