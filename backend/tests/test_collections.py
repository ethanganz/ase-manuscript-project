def test_create_and_list_collection(client):
    r = client.post("/api/collections",
                    json={"name": "Letters of Henri Dupont, 1850-1855"})
    assert r.status_code == 201
    created = r.json()
    assert created["name"].startswith("Letters of Henri")

    assert client.get("/api/collections").json()[0]["id"] == created["id"]
    assert client.get(f"/api/collections/{created['id']}").status_code == 200


def test_empty_name_rejected(client):
    assert client.post("/api/collections", json={"name": ""}).status_code == 422
    assert client.post("/api/collections", json={"name": "   "}).status_code == 422


def test_unknown_collection_is_404(client):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/collections/{missing}").status_code == 404
    assert client.get(f"/api/collections/{missing}/documents").status_code == 404


def test_bad_uuid_is_422(client):
    assert client.get("/api/collections/not-a-uuid").status_code == 422