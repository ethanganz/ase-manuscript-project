import pytest

from deps import get_htr
from main import app
from services import htr as htr_service
from services.htr import HtrError
from tests.conftest import make_image, make_pdf, register_verified, upload

LINE = {
    "text": "Basileę ultimo iulii 1554.",
    "bbox": [0, 0, 120, 40],
    "raw_text": "Basileę ultimo iulii 1554.",
    "places": [{"start": 0, "end": 7, "text": "Basileę", "sources": ["official_source_variant"]}],
}


class FakeHtr:
    """Stands in for the HTR service: records calls, answers one line per page."""

    def __init__(self, fail_on_call: int | None = None):
        self.calls: list[tuple[str, str | None]] = []
        self.fail_on_call = fail_on_call

    def transcribe(self, image, filename, language):
        self.calls.append((filename, language))
        if len(self.calls) == self.fail_on_call:
            raise HtrError("Recognition service is not reachable")
        return {"language": language, "lines": [LINE]}


@pytest.fixture
def htr(client):
    fake = FakeHtr()
    app.dependency_overrides[get_htr] = lambda: fake
    return fake


def pages_of(client, document_id):
    return client.get(f"/api/documents/{document_id}/pages").json()


def transcription(client, page_id):
    r = client.get(f"/api/pages/{page_id}/transcription")
    assert r.status_code == 200
    return r.json()


def test_upload_is_transcribed_in_background(client, collection, htr):
    r = client.post(
        f"/api/collections/{collection['id']}/uploads",
        files=[("files", ("letter.pdf", make_pdf(2)))],
        data={"language": "la"},
    )
    assert r.status_code == 201
    doc_id = r.json()["results"][0]["document_id"]

    # TestClient runs background tasks before returning.
    assert htr.calls == [("0001.png", "la"), ("0002.png", "la")]
    pages = pages_of(client, doc_id)
    assert [p["status"] for p in pages] == ["done", "done"]
    body = transcription(client, pages[0]["id"])
    assert body["status"] == "done"
    assert body["language"] == "la"
    assert body["lines"][0]["text"] == LINE["text"]
    assert body["lines"][0]["places"][0]["text"] == "Basileę"
    assert client.get(f"/api/documents/{doc_id}").json()["language"] == "la"


def test_unknown_language_is_sent_as_none(client, collection, htr):
    upload(client, collection["id"], ("a.png", make_image()))
    assert htr.calls == [("0001.png", None)]


def test_invalid_language_rejected(client, collection, htr):
    r = client.post(
        f"/api/collections/{collection['id']}/uploads",
        files=[("files", ("a.png", make_image()))],
        data={"language": "fr"},
    )
    assert r.status_code == 422
    assert htr.calls == []


def test_failed_page_does_not_stop_the_others(client, collection):
    fake = FakeHtr(fail_on_call=1)
    app.dependency_overrides[get_htr] = lambda: fake
    doc_id = upload(client, collection["id"], ("a.pdf", make_pdf(2))).json()["results"][0][
        "document_id"
    ]
    first, second = pages_of(client, doc_id)
    assert (first["status"], second["status"]) == ("failed", "done")
    body = transcription(client, first["id"])
    assert body["error"] == "Recognition service is not reachable"
    assert body["lines"] == []


def test_without_htr_service_pages_stay_pending(client, collection):
    doc_id = upload(client, collection["id"], ("a.png", make_image())).json()["results"][0][
        "document_id"
    ]
    page = pages_of(client, doc_id)[0]
    assert page["status"] == "pending"
    assert transcription(client, page["id"])["lines"] == []
    r = client.post(f"/api/documents/{doc_id}/transcribe")
    assert r.status_code == 503


def test_owner_can_rerun_with_another_language(client, collection):
    doc_id = upload(client, collection["id"], ("a.png", make_image())).json()["results"][0][
        "document_id"
    ]
    fake = FakeHtr()
    app.dependency_overrides[get_htr] = lambda: fake
    r = client.post(f"/api/documents/{doc_id}/transcribe", json={"language": "de"})
    assert r.status_code == 202
    assert fake.calls == [("0001.png", "de")]
    assert pages_of(client, doc_id)[0]["status"] == "done"


def test_only_owner_can_rerun(client, collection, htr):
    doc_id = upload(client, collection["id"], ("a.png", make_image())).json()["results"][0][
        "document_id"
    ]
    client.post("/api/auth/logout")
    register_verified(client, email="eve@example.com")
    assert client.post(f"/api/documents/{doc_id}/transcribe").status_code == 403


def test_rerun_refused_while_running(client, collection, htr):
    doc_id = upload(client, collection["id"], ("a.png", make_image())).json()["results"][0][
        "document_id"
    ]
    htr_service._running.add(doc_id)  # as if a run were still going
    try:
        assert client.post(f"/api/documents/{doc_id}/transcribe").status_code == 409
    finally:
        htr_service._running.discard(doc_id)


def test_pages_left_queued_by_a_restart_can_be_rerun(client, collection, htr, repo):
    doc_id = upload(client, collection["id"], ("a.png", make_image())).json()["results"][0][
        "document_id"
    ]
    page = pages_of(client, doc_id)[0]
    repo.update_page(page["id"], {"status": "processing"})
    assert client.post(f"/api/documents/{doc_id}/transcribe").status_code == 202
    assert pages_of(client, doc_id)[0]["status"] == "done"


def test_private_transcription_hidden_from_others(client, htr):
    private = client.post("/api/collections", json={"name": "Mine", "is_public": False}).json()
    doc_id = upload(client, private["id"], ("a.png", make_image())).json()["results"][0][
        "document_id"
    ]
    page_id = pages_of(client, doc_id)[0]["id"]
    client.post("/api/auth/logout")
    assert client.get(f"/api/pages/{page_id}/transcription").status_code == 404
