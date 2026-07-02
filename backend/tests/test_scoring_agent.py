from datetime import datetime, timedelta, timezone

from app.agents.scoring import calculate_lead_score
from app.models.lead import Lead


def _make_lead(**overrides) -> Lead:
    defaults = dict(
        contact_phone="5551234567",
        district="Kadikoy",
        budget_min=None,
        budget_max=None,
        room_count="2+1",
        message_count=0,
        last_contacted_at=None,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Lead(**defaults)


def test_never_contacted_lead_scores_low():
    lead = _make_lead()
    score, breakdown = calculate_lead_score(lead)
    assert breakdown["response_speed_score"] == 0.0
    assert score < 20


def test_fast_response_high_message_count_consistent_budget_scores_high():
    created_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    lead = _make_lead(
        created_at=created_at,
        last_contacted_at=created_at + timedelta(minutes=5),
        message_count=12,
        budget_min=10000,
        budget_max=12000,
    )
    score, breakdown = calculate_lead_score(lead)
    assert score > 90
    assert breakdown["message_count_score"] == 100.0


def test_inconsistent_budget_scores_zero_on_that_dimension():
    lead = _make_lead(budget_min=20000, budget_max=10000)
    _, breakdown = calculate_lead_score(lead)
    assert breakdown["budget_consistency_score"] == 0.0


def test_missing_budget_scores_lower_than_consistent_budget():
    lead_no_budget = _make_lead()
    lead_with_budget = _make_lead(budget_min=10000, budget_max=11000)
    _, breakdown_no_budget = calculate_lead_score(lead_no_budget)
    _, breakdown_with_budget = calculate_lead_score(lead_with_budget)
    assert breakdown_no_budget["budget_consistency_score"] < breakdown_with_budget["budget_consistency_score"]
