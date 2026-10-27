import io
import re
import zipfile

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pillow_heif import register_heif_opener

from database.repository import InMemoryRepository
from deps import get_mailer, get_repo, get_storage
from main import app
from services.email import InMemoryEmailSender
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
def mailer():
    return InMemoryEmailSender()


@pytest.fixture
def anon_client(repo, storage, mailer):
    """TestClient with an in-memory DB, object storage and outbox, not logged in."""
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_mailer] = lambda: mailer
    with TestClient(app) as c:
        c.mailer = mailer  # lets the helpers below read the outbox
        yield c
    app.dependency_overrides.clear()


def register(client, email="ada@example.com", password="correct-horse"):
    return client.post("/api/auth/register", json={
        "first_name": "Ada", "last_name": "Lovelace", "email": email, "password": password})


def verification_token(client, email="ada@example.com"):
    """Token from the newest verification email sent to this address."""
    sent = [m for m in client.mailer.outbox if m["to"] == email]
    assert sent, f"no verification email sent to {email}"
    return re.search(r"#verify-email/([\w.-]+)", sent[-1]["text"]).group(1)


def register_verified(client, email="ada@example.com", password="correct-horse"):
    """Register, open the link from the email, and end up logged in."""
    assert register(client, email=email, password=password).status_code == 201
    r = client.post("/api/auth/verify-email", json={"token": verification_token(client, email)})
    assert r.status_code == 200
    return r


@pytest.fixture
def client(anon_client):
    """TestClient logged in as a registered, verified user."""
    register_verified(anon_client)
    return anon_client


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