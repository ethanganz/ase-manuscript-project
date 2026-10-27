import config
from services.auth import create_email_token, create_token
from tests.conftest import (make_image, register, register_verified, upload,
                            verification_token)


def test_register_sends_email_but_does_not_log_in(anon_client):
    r = register(anon_client, email="  Ada@Example.com ")
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "ada@example.com"
    assert body["first_name"] == "Ada"
    assert body["last_name"] == "Lovelace"
    assert body["email_verified"] is False
    assert "password_hash" not in body
    assert "set-cookie" not in r.headers

    assert anon_client.get("/api/auth/me").status_code == 401
    [mail] = anon_client.mailer.outbox
    assert mail["to"] == "ada@example.com"
    assert f"{config.APP_BASE_URL}/#verify-email/" in mail["text"]


def test_verifying_logs_in(anon_client):
    r = register_verified(anon_client)
    assert r.json()["email_verified"] is True
    me = anon_client.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["email_verified"] is True


def test_unverified_user_cannot_log_in(anon_client):
    register(anon_client)
    r = anon_client.post("/api/auth/login",
                         json={"email": "ada@example.com", "password": "correct-horse"})
    assert r.status_code == 403
    assert "verify" in r.json()["detail"]
    assert anon_client.get("/api/auth/me").status_code == 401

    # A wrong password still gets the usual answer, verified or not.
    r = anon_client.post("/api/auth/login",
                         json={"email": "ada@example.com", "password": "wrong-pass"})
    assert r.status_code == 401


def test_link_can_be_opened_twice(anon_client):
    register(anon_client)
    token = verification_token(anon_client)
    for _ in range(2):
        r = anon_client.post("/api/auth/verify-email", json={"token": token})
        assert r.status_code == 200


def test_bad_verification_tokens_rejected(anon_client, repo):
    register(anon_client)
    user = repo.get_user_by_email("ada@example.com")
    bad_tokens = [
        "not.a.token",
        create_token(user["id"]),                               # a login token
        create_email_token(user["id"], "someone@example.com"),  # for another address
        create_email_token("00000000-0000-0000-0000-000000000000", "ada@example.com"),
    ]
    for token in bad_tokens:
        r = anon_client.post("/api/auth/verify-email", json={"token": token})
        assert r.status_code == 400
    assert repo.get_user_by_email("ada@example.com")["email_verified"] is False


def test_expired_verification_link_rejected(anon_client, repo, monkeypatch):
    register(anon_client)
    user = repo.get_user_by_email("ada@example.com")
    monkeypatch.setattr(config, "EMAIL_VERIFY_EXPIRE_HOURS", -1)
    token = create_email_token(user["id"], user["email"])
    assert anon_client.post("/api/auth/verify-email", json={"token": token}).status_code == 400


def test_verification_token_cannot_be_used_as_login_cookie(anon_client, repo):
    register(anon_client)
    anon_client.cookies.set(config.AUTH_COOKIE_NAME, verification_token(anon_client))
    assert anon_client.get("/api/auth/me").status_code == 401


def test_resend_verification(anon_client):
    register(anon_client)
    r = anon_client.post("/api/auth/resend-verification", json={"email": "ADA@example.com"})
    assert r.status_code == 202
    assert len(anon_client.mailer.outbox) == 2

    # Unknown and already verified addresses get the same answer but no email.
    unknown = anon_client.post("/api/auth/resend-verification",
                               json={"email": "bob@example.com"})
    assert unknown.status_code == 202 and unknown.json() == r.json()
    anon_client.post("/api/auth/verify-email", json={"token": verification_token(anon_client)})
    anon_client.post("/api/auth/resend-verification", json={"email": "ada@example.com"})
    assert len(anon_client.mailer.outbox) == 2


def test_cookie_is_http_only(anon_client):
    r = register_verified(anon_client)
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
    register_verified(anon_client)
    anon_client.post("/api/auth/logout")
    assert anon_client.get("/api/auth/me").status_code == 401

    r = anon_client.post("/api/auth/login",
                         json={"email": "ADA@example.com", "password": "correct-horse"})
    assert r.status_code == 200
    assert anon_client.get("/api/auth/me").status_code == 200


def test_wrong_password_and_unknown_email_look_the_same(anon_client):
    register_verified(anon_client)
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
    register_verified(client, email="bob@example.com")

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
    for step in ("visitor", "bob"):
        if step == "bob":
            register_verified(client, email="bob@example.com")
        assert client.get("/api/collections").json() == []
        assert [client.get(url).status_code for url in urls] == [404] * len(urls)
