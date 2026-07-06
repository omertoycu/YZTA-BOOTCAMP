from sqlalchemy import select

from app.api.routes import billing as billing_route
from app.core.config import settings
from app.core.payments import IyzicoError
from app.models.office import Office


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _office_id(db_session, office_name):
    office = db_session.execute(select(Office).where(Office.name == office_name)).scalar_one()
    return str(office.id)


def test_plans_requires_auth(client):
    resp = client.get("/billing/plans")
    assert resp.status_code == 401


def test_plans_marks_current_plan(client):
    headers = _register(client, "Ofis Billing 1", "owner1@billing-test.com")
    resp = client.get("/billing/plans", headers=headers)
    assert resp.status_code == 200
    plans = resp.json()
    assert [p["id"] for p in plans] == ["starter", "pro", "office"]
    # Yeni kayıtlı ofis varsayılan olarak starter'dadır.
    assert [p["is_current"] for p in plans] == [True, False, False]


def test_checkout_rejects_invalid_and_free_plans(client):
    headers = _register(client, "Ofis Billing 2", "owner2@billing-test.com")
    resp = client.post("/billing/checkout", json={"plan": "yok-boyle-plan"}, headers=headers)
    assert resp.status_code == 400
    resp = client.post("/billing/checkout", json={"plan": "starter"}, headers=headers)
    assert resp.status_code == 400


def test_checkout_returns_503_when_iyzico_not_configured(client, monkeypatch):
    headers = _register(client, "Ofis Billing 3", "owner3@billing-test.com")
    monkeypatch.setattr(settings, "iyzico_api_key", None)
    resp = client.post("/billing/checkout", json={"plan": "pro"}, headers=headers)
    assert resp.status_code == 503


def test_checkout_returns_payment_page_url(client, monkeypatch):
    headers = _register(client, "Ofis Billing 4", "owner4@billing-test.com")

    captured = {}

    def _fake_initialize(**kwargs):
        captured.update(kwargs)
        return {"token": "test-token", "payment_page_url": "https://sandbox-cpp.iyzipay.com/?token=test-token"}

    monkeypatch.setattr(billing_route, "initialize_checkout_form", _fake_initialize)

    resp = client.post("/billing/checkout", json={"plan": "pro"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["payment_page_url"].startswith("https://sandbox-cpp.iyzipay.com")
    assert captured["plan_id"] == "pro"
    assert captured["buyer_email"] == "owner4@billing-test.com"
    assert captured["callback_url"].endswith("/billing/callback")


def test_callback_success_updates_plan_and_redirects(client, db_session, monkeypatch):
    headers = _register(client, "Ofis Billing 5", "owner5@billing-test.com")
    office_id = _office_id(db_session, "Ofis Billing 5")

    monkeypatch.setattr(
        billing_route,
        "retrieve_checkout_result",
        lambda token: {"paid": True, "office_id": office_id, "plan_id": "office"},
    )

    resp = client.post("/billing/callback", data={"token": "test-token"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"].endswith("/billing?status=success")

    plans = client.get("/billing/plans", headers=headers).json()
    assert next(p for p in plans if p["id"] == "office")["is_current"] is True


def test_callback_failed_payment_does_not_change_plan(client, db_session, monkeypatch):
    headers = _register(client, "Ofis Billing 6", "owner6@billing-test.com")
    office_id = _office_id(db_session, "Ofis Billing 6")

    monkeypatch.setattr(
        billing_route,
        "retrieve_checkout_result",
        lambda token: {"paid": False, "office_id": office_id, "plan_id": "pro"},
    )

    resp = client.post("/billing/callback", data={"token": "test-token"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"].endswith("/billing?status=failed")

    plans = client.get("/billing/plans", headers=headers).json()
    assert next(p for p in plans if p["id"] == "starter")["is_current"] is True


def test_callback_iyzico_error_redirects_to_error(client, monkeypatch):
    def _raise(token):
        raise IyzicoError("iyzico'ya ulaşılamadı, tekrar deneyin.")

    monkeypatch.setattr(billing_route, "retrieve_checkout_result", _raise)

    resp = client.post("/billing/callback", data={"token": "test-token"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"].endswith("/billing?status=error")
