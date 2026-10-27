from tests.conftest import register_verified


def _bobs_collection(client, **extra):
    """Bob creates a collection, then Ada logs back in. Returns Bob's collection."""
    client.post("/api/auth/logout")
    register_verified(client, email="bob@example.com")
    collection = client.post("/api/collections", json={"name": "Bob's letters", **extra}).json()
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "ada@example.com", "password": "correct-horse"})
    return collection


def _log_in_as_bob(client):
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "bob@example.com", "password": "correct-horse"})


def test_owner_sees_report_without_reporter(client):
    bobs = _bobs_collection(client)
    r = client.post(f"/api/collections/{bobs['id']}/reports",
                    json={"reason": "spam", "details": "  Same file 50 times  "})
    assert r.status_code == 201

    _log_in_as_bob(client)
    [report] = client.get("/api/reports/received").json()
    assert report["collection_id"] == bobs["id"]
    assert report["collection_name"] == "Bob's letters"
    assert report["reason"] == "spam"
    assert report["details"] == "Same file 50 times"
    assert report["read"] is False
    assert "reporter_id" not in report and "ada" not in str(report).lower()


def test_mark_reports_read(client):
    bobs = _bobs_collection(client)
    client.post(f"/api/collections/{bobs['id']}/reports", json={"reason": "other"})

    _log_in_as_bob(client)
    assert client.post("/api/reports/received/read").status_code == 204
    assert [r["read"] for r in client.get("/api/reports/received").json()] == [True]


def test_reports_only_go_to_the_owner(client):
    bobs = _bobs_collection(client)
    client.post(f"/api/collections/{bobs['id']}/reports", json={"reason": "spam"})
    # Ada reported it, but it is not her collection, so she gets nothing.
    assert client.get("/api/reports/received").json() == []
    client.post("/api/reports/received/read")
    _log_in_as_bob(client)
    assert [r["read"] for r in client.get("/api/reports/received").json()] == [False]


def test_cannot_report_twice(client):
    bobs = _bobs_collection(client)
    url = f"/api/collections/{bobs['id']}/reports"
    assert client.post(url, json={"reason": "spam"}).status_code == 201
    assert client.post(url, json={"reason": "copyright"}).status_code == 409


def test_cannot_report_own_collection(client, collection):
    r = client.post(f"/api/collections/{collection['id']}/reports", json={"reason": "spam"})
    assert r.status_code == 400


def test_reporting_needs_login(client):
    bobs = _bobs_collection(client)
    client.post("/api/auth/logout")
    url = f"/api/collections/{bobs['id']}/reports"
    assert client.post(url, json={"reason": "spam"}).status_code == 401
    assert client.get("/api/reports/received").status_code == 401


def test_cannot_report_hidden_or_missing_collection(client):
    private = _bobs_collection(client, is_public=False)
    missing = "00000000-0000-0000-0000-000000000000"
    for collection_id in (private["id"], missing):
        r = client.post(f"/api/collections/{collection_id}/reports", json={"reason": "spam"})
        assert r.status_code == 404


def test_invalid_report_rejected(client):
    bobs = _bobs_collection(client)
    url = f"/api/collections/{bobs['id']}/reports"
    assert client.post(url, json={"reason": "boring"}).status_code == 422
    assert client.post(url, json={"reason": "spam", "details": "x" * 1001}).status_code == 422
