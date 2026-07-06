from app.core.vectorstore import get_listings_collection


def _register(client, office_name, email):
    resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_listing(client, headers, **overrides):
    payload = {"title": "Test ilan", "district": "Kadikoy", "price": 15000, "room_count": "2+1"}
    payload.update(overrides)
    resp = client.post("/listings", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_delete_listing_requires_auth(client):
    resp = client.delete("/listings/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 401


def test_delete_unknown_listing_returns_404(client):
    headers = _register(client, "Ofis Listing Delete Test 1", "owner1@listing-delete-test.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.delete(f"/listings/{fake_id}", headers=headers)
    assert resp.status_code == 404


def test_delete_listing_removes_it_and_returns_404_after(client):
    headers = _register(client, "Ofis Listing Delete Test 2", "owner2@listing-delete-test.com")
    listing_id = _create_listing(client, headers)

    resp = client.delete(f"/listings/{listing_id}", headers=headers)
    assert resp.status_code == 204

    resp = client.get(f"/listings/{listing_id}", headers=headers)
    assert resp.status_code == 404


def test_delete_listing_removes_it_from_chroma_index(client):
    headers = _register(client, "Ofis Listing Delete Test 3", "owner3@listing-delete-test.com")
    listing_id = _create_listing(client, headers)

    collection = get_listings_collection()
    assert collection.get(ids=[listing_id])["ids"] == [listing_id]

    resp = client.delete(f"/listings/{listing_id}", headers=headers)
    assert resp.status_code == 204

    assert collection.get(ids=[listing_id])["ids"] == []


def test_delete_listing_cascades_listing_views(client, db_session):
    from sqlalchemy import select

    from app.models.listing_view import ListingView

    headers = _register(client, "Ofis Listing Delete Test 4", "owner4@listing-delete-test.com")
    listing_id = _create_listing(client, headers)

    view_resp = client.get(f"/public/listings/{listing_id}")
    assert view_resp.status_code == 200

    views = db_session.execute(select(ListingView).where(ListingView.listing_id == listing_id)).scalars().all()
    assert len(views) == 1

    resp = client.delete(f"/listings/{listing_id}", headers=headers)
    assert resp.status_code == 204

    assert db_session.execute(select(ListingView).where(ListingView.listing_id == listing_id)).scalars().all() == []


def test_delete_listing_survives_chroma_failure(client, monkeypatch):
    from app.api.routes import listings as listings_route

    headers = _register(client, "Ofis Listing Delete Test 5", "owner5@listing-delete-test.com")
    listing_id = _create_listing(client, headers)

    def _raise(listing_id):
        raise RuntimeError("chroma boom")

    monkeypatch.setattr(listings_route, "remove_listing_from_index", _raise)

    resp = client.delete(f"/listings/{listing_id}", headers=headers)
    assert resp.status_code == 204

    resp = client.get(f"/listings/{listing_id}", headers=headers)
    assert resp.status_code == 404
