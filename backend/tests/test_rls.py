def _register_and_create_listing(client, office_name, email, title, district):
    register_resp = client.post(
        "/auth/register",
        json={"office_name": office_name, "owner_email": email, "owner_password": "Supersecret123!"},
    )
    token = register_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/listings",
        json={"title": title, "district": district, "price": 15000, "room_count": "2+1"},
        headers=headers,
    )
    return headers


def test_office_cannot_see_other_offices_listings(client):
    """RLS'in en kritik garantisi: bir ofis, diğerinin portföyünü asla göremez."""
    headers_a = _register_and_create_listing(
        client, "Ofis A", "ownerA@rls-test.com", "A'nın İlanı", "Kadıköy"
    )
    headers_b = _register_and_create_listing(
        client, "Ofis B", "ownerB@rls-test.com", "B'nin İlanı", "Beşiktaş"
    )

    listings_a = client.get("/listings", headers=headers_a).json()
    listings_b = client.get("/listings", headers=headers_b).json()

    titles_a = {listing["title"] for listing in listings_a}
    titles_b = {listing["title"] for listing in listings_b}

    assert "A'nın İlanı" in titles_a
    assert "B'nin İlanı" not in titles_a

    assert "B'nin İlanı" in titles_b
    assert "A'nın İlanı" not in titles_b
