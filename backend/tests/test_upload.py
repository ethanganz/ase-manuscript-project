import config
from tests.conftest import make_heic, make_image, make_pdf, make_zip, upload


# ---------------------------------------------------------------- happy paths
def test_upload_png(client, collection):
    r = upload(client, collection["id"], ("letter_001.png", make_image("PNG")))
    assert r.status_code == 201
    body = r.json()
    assert body["accepted"] == 1 and body["rejected"] == 0
    assert body["results"][0]["page_count"] == 1

    docs = client.get(f"/api/collections/{collection['id']}/documents").json()
    assert len(docs) == 1
    assert docs[0]["file_type"] == "png"
    assert docs[0]["original_filename"] == "letter_001.png"
    assert docs[0]["status"] == "uploaded"

    pages = client.get(f"/api/documents/{docs[0]['id']}/pages").json()
    assert [p["page_number"] for p in pages] == [1]
    assert (pages[0]["width"], pages[0]["height"]) == (120, 80)

    img = client.get(f"/api/pages/{pages[0]['id']}/image")
    assert img.status_code == 200 and img.content.startswith(b"\x89PNG")


def test_upload_jpeg(client, collection):
    r = upload(client, collection["id"], ("scan.jpeg", make_image("JPEG")))
    assert r.status_code == 201
    doc = client.get(f"/api/collections/{collection['id']}/documents").json()[0]
    assert doc["file_type"] == "jpeg"


def test_upload_pdf_is_split_into_pages(client, collection):
    r = upload(client, collection["id"], ("letter_002.pdf", make_pdf(3)))
    assert r.status_code == 201
    assert r.json()["results"][0]["page_count"] == 3

    doc = client.get(f"/api/collections/{collection['id']}/documents").json()[0]
    pages = client.get(f"/api/documents/{doc['id']}/pages").json()
    assert [p["page_number"] for p in pages] == [1, 2, 3]
    img = client.get(f"/api/pages/{pages[0]['id']}/image")
    assert img.content.startswith(b"\x89PNG")  # PDF pages are rendered to PNG


def test_bulk_upload_multiple_files(client, collection):
    r = upload(client, collection["id"],
               ("a.png", make_image()), ("b.jpg", make_image("JPEG")),
               ("c.pdf", make_pdf(2)))
    assert r.status_code == 201
    assert r.json()["accepted"] == 3
    docs = client.get(f"/api/collections/{collection['id']}/documents").json()
    assert len(docs) == 3


def test_zip_of_images(client, collection):
    z = make_zip({
        "letters/p1.png": make_image(),
        "letters/p2.jpg": make_image("JPEG"),
        "letters/notes.txt": b"hello",
        "__MACOSX/letters/._p1.png": b"junk",
        "letters/.DS_Store": b"junk",
    })
    r = upload(client, collection["id"], ("batch.zip", z))
    body = r.json()
    assert r.status_code == 201
    assert body["accepted"] == 2
    assert body["rejected"] == 1                     # notes.txt only; junk ignored
    rejected = [x for x in body["results"] if x["status"] == "rejected"][0]
    assert "notes.txt" in rejected["filename"]

    docs = client.get(f"/api/collections/{collection['id']}/documents").json()
    assert {d["source_archive"] for d in docs} == {"batch.zip"}


# ------------------------------------------------------------------ rejection
def test_text_file_renamed_to_jpg_is_rejected(client, collection):
    r = upload(client, collection["id"], ("fake.jpg", b"this is not an image"))
    assert r.status_code == 422
    assert r.json()["results"][0]["status"] == "rejected"
    assert client.get(f"/api/collections/{collection['id']}/documents").json() == []


def test_type_is_detected_by_content_not_extension(client, collection):
    # A real JPEG called .png is accepted and stored as a JPEG.
    r = upload(client, collection["id"], ("odd.png", make_image("JPEG")))
    assert r.status_code == 201
    doc = client.get(f"/api/collections/{collection['id']}/documents").json()[0]
    assert doc["file_type"] == "jpeg"


def test_corrupt_pdf_rejected_and_nothing_left_behind(client, collection, repo, storage):
    r = upload(client, collection["id"], ("bad.pdf", b"%PDF-1.4 garbage garbage"))
    assert r.status_code == 422
    assert repo.documents == {} and repo.pages == {}
    assert storage.objects == {}


def test_truncated_image_rejected(client, collection):
    r = upload(client, collection["id"], ("cut.png", make_image("PNG")[:40]))
    assert r.status_code == 422


def test_empty_file_rejected(client, collection):
    r = upload(client, collection["id"], ("empty.png", b""))
    assert r.status_code == 422
    assert "empty" in r.json()["results"][0]["error"].lower()


def test_file_too_large(client, collection, monkeypatch):
    monkeypatch.setattr(config, "MAX_FILE_BYTES", 100)
    r = upload(client, collection["id"], ("big.png", make_image(size=(300, 300))))
    assert r.status_code == 422
    assert "limit" in r.json()["results"][0]["error"]


def test_pdf_page_limit(client, collection, monkeypatch):
    monkeypatch.setattr(config, "MAX_PDF_PAGES", 2)
    r = upload(client, collection["id"], ("long.pdf", make_pdf(3)))
    assert r.status_code == 422
    assert "limit" in r.json()["results"][0]["error"]


def test_zip_too_many_entries(client, collection, monkeypatch):
    monkeypatch.setattr(config, "MAX_ZIP_ENTRIES", 2)
    z = make_zip({f"{i}.png": make_image() for i in range(3)})
    r = upload(client, collection["id"], ("many.zip", z))
    assert r.status_code == 422


def test_nested_zip_member_rejected(client, collection):
    inner = make_zip({"x.png": make_image()})
    z = make_zip({"ok.png": make_image(), "inner.zip": inner})
    body = upload(client, collection["id"], ("outer.zip", z)).json()
    assert body["accepted"] == 1 and body["rejected"] == 1


def test_corrupt_zip_rejected(client, collection):
    r = upload(client, collection["id"], ("broken.zip", b"PK\x03\x04 not really a zip"))
    assert r.status_code == 422


def test_mixed_batch_reports_each_file(client, collection):
    r = upload(client, collection["id"],
               ("good.png", make_image()), ("bad.txt", b"nope"))
    assert r.status_code == 201                      # at least one accepted
    statuses = {x["filename"]: x["status"] for x in r.json()["results"]}
    assert statuses == {"good.png": "accepted", "bad.txt": "rejected"}


# ------------------------------------------------------------------- security
def test_zip_slip_names_never_reach_storage_keys(client, collection, storage):
    z = make_zip({"../../../evil.png": make_image(), "..\\..\\evil2.png": make_image()})
    r = upload(client, collection["id"], ("slip.zip", z))
    assert r.status_code == 201
    for key in storage.objects:
        assert ".." not in key and "evil" not in key
        assert key.startswith(f"collections/{collection['id']}/")
    names = {d["original_filename"] for d in
             client.get(f"/api/collections/{collection['id']}/documents").json()}
    assert names == {"evil.png", "evil2.png"}        # path parts stripped


def test_malicious_filename_is_sanitised(client, collection):
    upload(client, collection["id"], ("../../etc/passwd.png", make_image()))
    doc = client.get(f"/api/collections/{collection['id']}/documents").json()[0]
    assert doc["original_filename"] == "passwd.png"


# ------------------------------------------------------------------- plumbing
def test_upload_to_unknown_collection_404(client):
    r = upload(client, "00000000-0000-0000-0000-000000000000",
               ("a.png", make_image()))
    assert r.status_code == 404


def test_upload_without_files_is_422(client, collection):
    assert client.post(f"/api/collections/{collection['id']}/uploads").status_code == 422


def test_objects_stored_under_collection_and_document(client, collection, storage):
    upload(client, collection["id"], ("a.pdf", make_pdf(2)))
    doc = client.get(f"/api/collections/{collection['id']}/documents").json()[0]
    base = f"collections/{collection['id']}/documents/{doc['id']}"
    assert set(storage.objects) == {
        f"{base}/original.pdf", f"{base}/pages/0001.png", f"{base}/pages/0002.png"}
    assert storage.objects[f"{base}/original.pdf"][1] == "application/pdf"


# ----------------------------------------------------------------------- HEIC
def test_upload_heic_keeps_original_and_makes_jpeg_page(client, collection, storage):
    r = upload(client, collection["id"], ("IMG_0001.HEIC", make_heic()))
    assert r.status_code == 201
    doc = client.get(f"/api/collections/{collection['id']}/documents").json()[0]
    assert doc["file_type"] == "heic"
    base = f"collections/{collection['id']}/documents/{doc['id']}"
    assert set(storage.objects) == {f"{base}/original.heic", f"{base}/pages/0001.jpg"}

    page = client.get(f"/api/documents/{doc['id']}/pages").json()[0]
    assert (page["width"], page["height"]) == (120, 80)
    img = client.get(f"/api/pages/{page['id']}/image")
    assert img.headers["content-type"] == "image/jpeg"
    assert img.content.startswith(b"\xff\xd8")


def test_heic_inside_zip(client, collection):
    z = make_zip({"a.heic": make_heic(), "b.png": make_image()})
    assert upload(client, collection["id"], ("phone.zip", z)).json()["accepted"] == 2


def test_corrupt_heic_rejected(client, collection, storage):
    bad = make_heic()[:60]
    r = upload(client, collection["id"], ("bad.heic", bad))
    assert r.status_code == 422 and storage.objects == {}


# ------------------------------------------------------------------- rollback
def test_db_failure_removes_uploaded_objects(client, collection, repo, storage, monkeypatch):
    def boom(pages):
        raise RuntimeError("db down")
    monkeypatch.setattr(repo, "create_pages", boom)
    r = upload(client, collection["id"], ("a.pdf", make_pdf(2)))
    assert r.status_code == 422
    assert storage.objects == {} and repo.documents == {}


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}