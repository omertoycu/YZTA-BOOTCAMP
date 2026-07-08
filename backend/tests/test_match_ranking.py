from app.agents import match_ranking
from app.agents.match_ranking import rerank_candidates_with_ai


def _candidates():
    return [
        {
            "listing_id": "11111111-1111-1111-1111-111111111111",
            "title": "BEGO GAYRİMENKULDEN ULUYOLA YAKIN 600 M2 KİRALIK İŞ YERİ",
            "price": 30000.0,
            "match_reason": "Osmangazi bölgesinde, bütçe ve oda sayısı kriterine uyuyor",
        },
        {
            "listing_id": "22222222-2222-2222-2222-222222222222",
            "title": "Alakasız satılık daire",
            "price": 900000.0,
            "match_reason": "Osmangazi bölgesinde, bütçe ve oda sayısı kriterine uyuyor",
        },
    ]


def test_rerank_orders_by_relevance_score_and_enriches_reason(monkeypatch):
    def _fake_generate_content(self, prompt, generation_config=None):
        class _Resp:
            text = (
                '[{"index": 1, "relevance_score": 95, "reason": "İş yeri arayışıyla tam uyuşuyor"}, '
                '{"index": 2, "relevance_score": 10, "reason": "Konut, iş yeri değil"}]'
            )

        return _Resp()

    monkeypatch.setattr(match_ranking.settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr("google.generativeai.configure", lambda **kwargs: None)
    monkeypatch.setattr("google.generativeai.GenerativeModel.generate_content", _fake_generate_content)

    ranked = rerank_candidates_with_ai(
        original_message="uluyol caddesinde kiralık bir iş yeri bakıyorum",
        criteria={"bölge": "Osmangazi", "işlem_tipi": "rent", "emlak_tipi": "commercial"},
        candidates=_candidates(),
    )

    assert [c["listing_id"] for c in ranked] == [
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    ]
    assert ranked[0]["relevance_score"] == 95
    assert "İş yeri arayışıyla tam uyuşuyor" in ranked[0]["match_reason"]


def test_rerank_returns_candidates_unchanged_when_not_configured(monkeypatch):
    monkeypatch.setattr(match_ranking.settings, "gemini_api_key", None)

    candidates = _candidates()
    ranked = rerank_candidates_with_ai(
        original_message="mesaj", criteria={}, candidates=candidates
    )

    assert ranked == candidates
    assert all(c.get("relevance_score") is None for c in ranked)


def test_rerank_returns_candidates_unchanged_on_gemini_error(monkeypatch):
    def _raise(self, prompt, generation_config=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(match_ranking.settings, "gemini_api_key", "fake-key")
    monkeypatch.setattr("google.generativeai.configure", lambda **kwargs: None)
    monkeypatch.setattr("google.generativeai.GenerativeModel.generate_content", _raise)

    candidates = _candidates()
    ranked = rerank_candidates_with_ai(
        original_message="mesaj", criteria={}, candidates=candidates
    )

    assert ranked == candidates


def test_rerank_with_empty_candidates_returns_empty_list(monkeypatch):
    assert rerank_candidates_with_ai(original_message=None, criteria={}, candidates=[]) == []
