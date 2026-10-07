import io
import zipfile

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pillow_heif import register_heif_opener

from database.repository import InMemoryRepository
from deps import get_repo, get_storage
from main import app
from services.storage import InMemoryStorage

register_heif_opener()

# shared setup: a fake database, fake storage and sample-file makers):
@pytest.fixture
def repo():
    return InMemoryRepository()


@pytest.fixture
def storage():
    return InMemoryStorage()


@pytest.fixture
def client(repo, storage):
    """TestClient with an in-memory DB and in-memory object storage."""
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def collection(client):
    return client.post("/api/collections", json={"name": "Test letters"}).json()


# ---- sample-file factories -------------------------------------------------
def make_image(fmt="PNG", size=(120, 80)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, fmt)
    return buf.getvalue()


def make_heic(size=(120, 80)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, "HEIF")
    return buf.getvalue()


def make_pdf(pages=2) -> bytes:
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    data = doc.tobytes()
    doc.close()
    return data


def make_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def upload(client, collection_id, *files):
    """files: (filename, bytes) tuples."""
    return client.post(
        f"/api/collections/{collection_id}/uploads",
        files=[("files", (name, data)) for name, data in files],
    )