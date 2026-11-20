from tests.conftest import register_verified


def test_create_and_list_collection(client):
    r = client.post("/api/collections", json={"name": "Letters of Henri Dupont, 1850-1855"})
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


def test_owner_can_rename_and_change_description(client, collection):
    url = f"/api/collections/{collection['id']}"
    r = client.patch(url, json={"name": "  Renamed letters  ", "description": "From the attic"})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed letters"
    assert r.json()["description"] == "From the attic"
    assert client.get(url).json()["name"] == "Renamed letters"

    # Only the fields sent change; an empty description clears it.
    r = client.patch(url, json={"description": "   "})
    assert r.json()["name"] == "Renamed letters"
    assert r.json()["description"] is None


def test_edit_rejects_empty_name(client, collection):
    url = f"/api/collections/{collection['id']}"
    assert client.patch(url, json={"name": ""}).status_code == 422
    assert client.patch(url, json={"name": "   "}).status_code == 422
    assert client.patch(url, json={"name": None}).status_code == 422


def test_only_the_owner_can_edit(client, collection):
    url = f"/api/collections/{collection['id']}"
    client.post("/api/auth/logout")
    assert client.patch(url, json={"name": "Hijacked"}).status_code == 401

    register_verified(client, email="bob@example.com")
    assert client.patch(url, json={"name": "Hijacked"}).status_code == 403
    assert client.get(url).json()["name"] == "Test letters"


def test_edit_unknown_collection_is_404(client):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.patch(f"/api/collections/{missing}", json={"name": "x"}).status_code == 404


def test_owner_can_delete_a_collection_with_its_data(client, collection, repo, storage):
    from tests.test_ask import add_lines

    document_id, page_id = add_lines(repo, collection["id"], ["ad Zürich missi"])
    repo.documents[document_id]["original_path"] = "orig/file.pdf"
    repo.pages[page_id]["image_path"] = "pages/1.png"
    storage.objects.update({"orig/file.pdf": b"x", "pages/1.png": b"y"})
    url = f"/api/collections/{collection['id']}"

    assert client.delete(url).status_code == 204

    assert client.get(url).status_code == 404
    assert repo.documents == {} and repo.pages == {} and repo.text_lines == {}
    assert storage.objects == {}


def test_only_the_owner_can_delete(client, collection):
    url = f"/api/collections/{collection['id']}"
    client.post("/api/auth/logout")
    assert client.delete(url).status_code == 401

    register_verified(client, email="bob@example.com")
    assert client.delete(url).status_code == 403
    assert client.get(url).status_code == 200


def test_delete_unknown_collection_is_404(client):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.delete(f"/api/collections/{missing}").status_code == 404
