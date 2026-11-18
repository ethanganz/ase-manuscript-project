"""Line-by-line transcription: worker, endpoints and the hook after upload.

The real pipeline needs PyTorch and gigabytes of models, so these tests use a
tiny stand-in script that writes a page_response.json in the same shape.
"""

import sys
import time

import pytest

import config
from services import htr_worker
from tests.conftest import make_image, register_verified, upload

FAKE_PIPELINE = """
import argparse, json, sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--image"); p.add_argument("--output-dir"); p.add_argument("--page-id")
p.add_argument("--device")
a = p.parse_args()
if not Path(a.image).is_file():
    sys.exit("image missing")
if MODE == "fail":
    raise ValueError("No text lines found; inspect crops/preview.png")
out = Path(a.output_dir); out.mkdir(parents=True)
(out / "page_response.json").write_text(json.dumps({
    "page": {"page_id": a.page_id, "width": 1000, "height": 400},
    "lines": [
        {"line_id": "line_0001", "bbox": [10, 10, 990, 60], "polygon": [[10, 10], [990, 10], [990, 60], [10, 60]],
         "text": "Basileę ultimo iulii 1549.",
         "places": [{"start": 0, "end": 7, "text": "Basileę", "place_link_status": "candidate_for_review",
                     "official_place_candidates": [{"official_place_id": "l28", "canonical_name": "Basel",
                                                    "latitude": 47.55839, "longitude": 7.57327}]}]},
        {"line_id": "line_0002", "bbox": [10, 70, 990, 120], "polygon": None, "text": "Gratia et pax", "places": []},
    ],
}))
"""


@pytest.fixture
def fake_pipeline(tmp_path, monkeypatch):
    def make(mode="ok"):
        (tmp_path / "scripts").mkdir(exist_ok=True)
        (tmp_path / "scripts" / "run_page_pipeline.py").write_text(
            f"MODE = {mode!r}\n" + FAKE_PIPELINE
        )

    make()
    monkeypatch.setattr(config, "HTR_ENABLED", True)
    monkeypatch.setattr(config, "HTR_PIPELINE_DIR", tmp_path)
    monkeypatch.setattr(config, "HTR_PYTHON", sys.executable)
    monkeypatch.setattr(config, "HTR_TIMEOUT_SECONDS", 60)
    return make


def _page(client, collection_id, enabled_upload=True):
    r = upload(client, collection_id, ("letter.png", make_image("PNG")))
    assert r.status_code == 201
    doc_id = r.json()["results"][0]["document_id"]
    page = client.get(f"/api/documents/{doc_id}/pages").json()[0]
    return doc_id, page["id"]


def _wait_for(client, page_id, wanted=("complete", "failed"), seconds=20):
    deadline = time.time() + seconds
    while time.time() < deadline:
        body = client.get(f"/api/pages/{page_id}/transcription").json()
        if body["status"] in wanted:
            return body
        time.sleep(0.1)
    raise AssertionError(f"page never reached {wanted}: {body}")


# ------------------------------------------------------------ worker directly
def test_process_page_stores_every_line(fake_pipeline, client, collection, repo, storage):
    _, page_id = _page(client, collection["id"])
    htr_worker.process_page(repo, storage, page_id)

    body = client.get(f"/api/pages/{page_id}/transcription").json()
    assert body["status"] == "complete"
    assert (body["width"], body["height"]) == (1000, 400)
    assert [line["text"] for line in body["lines"]] == [
        "Basileę ultimo iulii 1549.",
        "Gratia et pax",
    ]
    assert [line["line_index"] for line in body["lines"]] == [0, 1]
    mention = body["lines"][0]["places"][0]
    assert mention["text"] == "Basileę"
    assert mention["official_place_candidates"][0]["canonical_name"] == "Basel"


def test_failed_pipeline_is_reported_not_raised(fake_pipeline, client, collection, repo, storage):
    fake_pipeline("fail")
    _, page_id = _page(client, collection["id"])
    htr_worker.process_page(repo, storage, page_id)

    body = client.get(f"/api/pages/{page_id}/transcription").json()
    assert body["status"] == "failed"
    assert "No text lines found" in body["error"]
    assert body["lines"] == []


def test_missing_pipeline_script_is_reported(
    fake_pipeline, client, collection, repo, storage, monkeypatch, tmp_path
):
    monkeypatch.setattr(config, "HTR_PIPELINE_DIR", tmp_path / "nowhere")
    _, page_id = _page(client, collection["id"])
    htr_worker.process_page(repo, storage, page_id)
    body = client.get(f"/api/pages/{page_id}/transcription").json()
    assert body["status"] == "failed" and "not found" in body["error"]


def test_retry_replaces_old_lines(fake_pipeline, client, collection, repo, storage):
    _, page_id = _page(client, collection["id"])
    htr_worker.process_page(repo, storage, page_id)
    htr_worker.process_page(repo, storage, page_id)
    assert len(client.get(f"/api/pages/{page_id}/transcription").json()["lines"]) == 2


# ------------------------------------------------------------------ endpoints
def test_pending_page_has_no_lines(client, collection):
    # HTR is off by default, so the upload leaves the page pending.
    _, page_id = _page(client, collection["id"])
    body = client.get(f"/api/pages/{page_id}/transcription").json()
    assert body["status"] == "pending" and body["lines"] == []


def test_upload_starts_transcription_in_background(fake_pipeline, client, collection):
    _, page_id = _page(client, collection["id"])
    body = _wait_for(client, page_id)
    assert body["status"] == "complete"
    assert body["lines"][1]["text"] == "Gratia et pax"


def test_transcribe_endpoint_needs_login_and_ownership(fake_pipeline, client, collection):
    doc_id, page_id = _page(client, collection["id"])
    _wait_for(client, page_id)

    client.post("/api/auth/logout")
    assert client.post(f"/api/pages/{page_id}/transcribe").status_code == 401

    register_verified(client, email="eve@example.com")
    assert client.post(f"/api/pages/{page_id}/transcribe").status_code == 403
    assert client.post(f"/api/documents/{doc_id}/transcribe").status_code == 403


def test_owner_can_retry_a_failed_page(fake_pipeline, client, collection):
    fake_pipeline("fail")
    doc_id, page_id = _page(client, collection["id"])
    assert _wait_for(client, page_id)["status"] == "failed"

    fake_pipeline("ok")
    r = client.post(f"/api/documents/{doc_id}/transcribe")
    assert r.status_code == 202 and r.json()["queued_pages"] == 1
    assert _wait_for(client, page_id)["status"] == "complete"


def test_transcribe_is_503_when_disabled(client, collection):
    doc_id, page_id = _page(client, collection["id"])
    assert client.post(f"/api/pages/{page_id}/transcribe").status_code == 503
    assert client.post(f"/api/documents/{doc_id}/transcribe").status_code == 503


def test_private_collection_hides_transcription(fake_pipeline, client):
    private = client.post("/api/collections", json={"name": "Secret", "is_public": False}).json()
    _, page_id = _page(client, private["id"])
    _wait_for(client, page_id)

    client.post("/api/auth/logout")
    assert client.get(f"/api/pages/{page_id}/transcription").status_code == 404


def test_unknown_page_is_404(client):
    r = client.get("/api/pages/00000000-0000-0000-0000-000000000000/transcription")
    assert r.status_code == 404


# ------------------------------------------------------------------ the map
def test_transcribed_places_reach_the_country_map(fake_pipeline, client, collection, repo, storage):
    _, page_id = _page(client, collection["id"])
    htr_worker.process_page(repo, storage, page_id)

    countries = client.get(f"/api/collections/{collection['id']}/map/countries").json()
    assert countries == [{"country_code": "CH", "mention_count": 1, "place_count": 1}]

    mentions = client.get(f"/api/collections/{collection['id']}/map/countries/CH/mentions").json()
    assert mentions[0]["place_name"] == "Basel"
    assert mentions[0]["page_id"] == page_id
    assert mentions[0]["snippet"] == "Basileę ultimo iulii 1549."


def test_transcribing_again_does_not_duplicate_map_entries(
    fake_pipeline, client, collection, repo, storage
):
    _, page_id = _page(client, collection["id"])
    htr_worker.process_page(repo, storage, page_id)
    htr_worker.process_page(repo, storage, page_id)
    countries = client.get(f"/api/collections/{collection['id']}/map/countries").json()
    assert countries[0]["mention_count"] == 1


def test_unresolved_mentions_stay_off_the_map_but_in_the_lines():
    from services.place_linker import resolve_page
    from services.place_lookup import PlaceLookup

    lookup = PlaceLookup(variants={}, localities={})  # knows no place at all
    lines = [
        {
            "text": "Ad Xyzzy",
            "places": [{"start": 3, "end": 8, "text": "Xyzzy", "official_place_candidates": []}],
        }
    ]
    assert resolve_page(lines, lookup) == []


def test_a_broken_place_list_does_not_fail_the_page(
    fake_pipeline, client, collection, repo, storage, monkeypatch
):
    def boom(_repo, _page_id, _mentions):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr(repo, "replace_page_mentions", boom)
    _, page_id = _page(client, collection["id"])
    htr_worker.process_page(repo, storage, page_id)
    body = client.get(f"/api/pages/{page_id}/transcription").json()
    assert body["status"] == "complete" and len(body["lines"]) == 2


# ---------------------------------------------------- the HTTP service (HTR-NLP/service)
SERVICE_REPLY = {
    "page": {"width": 800, "height": 300},
    "lines": [
        {
            "line_id": "line_0001",
            "bbox": [0, 0, 800, 100],
            "polygon": None,
            "text": "Ad Tigurum",
            "places": [],
        },
    ],
}


@pytest.fixture
def fake_service(monkeypatch):
    """A tiny HTTP server that behaves like HTR-NLP/service."""
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    reply = {"code": 200, "body": SERVICE_REPLY}
    seen = {"requests": 0, "had_image": False}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            seen["requests"] += 1
            seen["had_image"] = self.path == "/transcribe" and b'name="image"' in body
            data = json.dumps(reply["body"]).encode()
            self.send_response(reply["code"])
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(config, "HTR_ENABLED", True)
    monkeypatch.setattr(config, "HTR_SERVICE_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setattr(config, "HTR_TIMEOUT_SECONDS", 10)
    yield reply, seen
    server.shutdown()


def test_service_mode_reads_the_page_after_upload(fake_service, client, collection):
    _, seen = fake_service
    _, page_id = _page(client, collection["id"])
    body = _wait_for(client, page_id)
    assert body["status"] == "complete"
    assert [line["text"] for line in body["lines"]] == ["Ad Tigurum"]
    assert (body["width"], body["height"]) == (800, 300)
    assert seen["requests"] == 1 and seen["had_image"]


def test_service_says_no_lines_found(fake_service, client, collection, repo, storage):
    reply, _ = fake_service
    reply.update(code=422, body={"detail": "No text lines found on this page"})
    _, page_id = _page(client, collection["id"])
    htr_worker.process_page(repo, storage, page_id)
    body = client.get(f"/api/pages/{page_id}/transcription").json()
    assert body["status"] == "failed" and body["error"] == "No text lines found on this page"


def test_service_error_is_reported(fake_service, client, collection, repo, storage):
    reply, _ = fake_service
    reply.update(code=500, body={"detail": "boom"})
    _, page_id = _page(client, collection["id"])
    htr_worker.process_page(repo, storage, page_id)
    body = client.get(f"/api/pages/{page_id}/transcription").json()
    assert body["status"] == "failed" and "500" in body["error"]


def test_service_not_running_is_reported(monkeypatch, client, collection, repo, storage):
    monkeypatch.setattr(config, "HTR_ENABLED", True)
    monkeypatch.setattr(config, "HTR_SERVICE_URL", "http://127.0.0.1:9")  # nothing listens here
    _, page_id = _page(client, collection["id"])
    htr_worker.process_page(repo, storage, page_id)
    body = client.get(f"/api/pages/{page_id}/transcription").json()
    assert body["status"] == "failed" and "not reachable" in body["error"]
