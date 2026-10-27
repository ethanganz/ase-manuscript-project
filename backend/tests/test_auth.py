import config
from tests.conftest import make_image, register, upload


def test_register_logs_in(anon_client):
    r = register(anon_client, email="  Ada@Example.com ")
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "ada@example.com"
    assert body["first_name"] == "Ada"
    assert body["last_name"] == "Lovelace"
    assert "password_hash" not in body

    me = anon_client.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["id"] == body["id"]


def test_cookie_is_http_only(anon_client):
    r = register(anon_client)
    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{config.AUTH_COOKIE_NAME}=")
    assert "HttpOnly" in cookie and "samesite=lax" in cookie.lower()


def test_duplicate_email_rejected(anon_client):
    register(anon_client)
    assert register(anon_client, email="ADA@example.com").status_code == 409


def test_invalid_registration_rejected(anon_client):
    assert register(anon_client, email="not-an-email").status_code == 422
    assert register(anon_client, password="short").status_code == 422
    blank_name = anon_client.post("/api/auth/register", json={
        "first_name": "  ", "last_name": "Lovelace",
        "email": "ada@example.com", "password": "correct-horse"})
    assert blank_name.status_code == 422
    # 60 characters but 120 bytes, over bcrypt's limit.
    assert register(anon_client, password="é" * 60).status_code == 422


def test_login_and_logout(anon_client):
    register(anon_client)
    anon_client.post("/api/auth/logout")
    assert anon_client.get("/api/auth/me").status_code == 401

    r = anon_client.post("/api/auth/login",
                         json={"email": "ADA@example.com", "password": "correct-horse"})
    assert r.status_code == 200
    assert anon_client.get("/api/auth/me").status_code == 200


def test_wrong_password_and_unknown_email_look_the_same(anon_client):
    register(anon_client)
    anon_client.post("/api/auth/logout")
    wrong = anon_client.post("/api/auth/login",
                             json={"email": "ada@example.com", "password": "wrong-pass"})
    unknown = anon_client.post("/api/auth/login",
                               json={"email": "bob@example.com", "password": "wrong-pass"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_tampered_token_rejected(anon_client):
    anon_client.cookies.set(config.AUTH_COOKIE_NAME, "not.a.token")
    assert anon_client.get("/api/auth/me").status_code == 401


def test_browsing_is_public_but_creating_needs_login(anon_client, repo):
    owner = repo.create_user("ada@example.com", "x", "Ada", "Lovelace")
    collection = repo.create_collection("Letters", None, owner["id"])

    assert anon_client.get("/api/collections").status_code == 200
    assert anon_client.get(f"/api/collections/{collection['id']}").status_code == 200
    assert anon_client.post("/api/collections", json={"name": "x"}).status_code == 401
    assert upload(anon_client, collection["id"],
                  ("x.png", make_image("PNG"))).status_code == 401


def test_only_the_owner_can_upload(client):
    mine = client.post("/api/collections", json={"name": "Ada's letters"}).json()
    assert upload(client, mine["id"], ("a.png", make_image("PNG"))).status_code == 201

    client.post("/api/auth/logout")
    register(client, email="bob@example.com")

    # Bob can look at Ada's collection but not add to it.
    assert [c["id"] for c in client.get("/api/collections").json()] == [mine["id"]]
    assert len(client.get(f"/api/collections/{mine['id']}/documents").json()) == 1
    r = upload(client, mine["id"], ("b.png", make_image("PNG")))
    assert r.status_code == 403


def test_collections_are_public_by_default(client):
    created = client.post("/api/collections", json={"name": "Open letters"}).json()
    assert created["is_public"] is True

    client.post("/api/auth/logout")
    assert [c["id"] for c in client.get("/api/collections").json()] == [created["id"]]


def test_private_collection_is_only_visible_to_its_owner(client):
    private = client.post("/api/collections",
                          json={"name": "Diary", "is_public": False}).json()
    assert private["is_public"] is False
    r = upload(client, private["id"], ("a.png", make_image("PNG")))
    document_id = r.json()["results"][0]["document_id"]
    page_id = client.get(f"/api/documents/{document_id}/pages").json()[0]["id"]

    urls = [
        f"/api/collections/{private['id']}",
        f"/api/collections/{private['id']}/documents",
        f"/api/collections/{private['id']}/map/countries",
        f"/api/documents/{document_id}",
        f"/api/documents/{document_id}/pages",
        f"/api/pages/{page_id}/image",
    ]

    # The owner sees everything.
    assert [c["id"] for c in client.get("/api/collections").json()] == [private["id"]]
    assert all(client.get(url).status_code == 200 for url in urls)

    # A visitor and another user see nothing, and cannot tell it exists.
    client.post("/api/auth/logout")
    for _ in range(2):
        assert client.get("/api/collections").json() == []
        assert [client.get(url).status_code for url in urls] == [404] * len(urls)
        register(client, email="bob@example.com")
