"""Sends page images to the HTR service (htr/service) and stores what it reads.

Runs as a background task after an upload, so the upload answers right away:
  queued -> processing -> done | failed      (one page at a time)
Tests use a fake client, so they never need the models.
"""

import logging
import mimetypes
import threading
from datetime import datetime, timezone

import httpx

from database.repository import Repository
from services.storage import ObjectStorage

logger = logging.getLogger("uvicorn.error")

# Documents being transcribed by this process. Kept in memory on purpose: after a
# restart, pages left "queued" or "processing" can simply be started again.
_running: set[str] = set()
_running_lock = threading.Lock()


class HtrError(Exception):
    """A short reason, shown to the user, why a page could not be transcribed."""


class HtrClient:
    def transcribe(self, image: bytes, filename: str, language: str | None) -> dict: ...


class HttpHtrClient(HtrClient):
    def __init__(self, base_url: str, timeout: float) -> None:
        self._url = f"{base_url}/transcribe"
        self._timeout = timeout

    def transcribe(self, image, filename, language):
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                res = client.post(
                    self._url,
                    files={"image": (filename, image, content_type)},
                    data={"language": language or "unknown"},
                )
        except httpx.TimeoutException as exc:
            raise HtrError("Recognition timed out") from exc
        except httpx.HTTPError as exc:
            raise HtrError("Recognition service is not reachable") from exc
        if res.status_code != 200:
            raise HtrError(f"Recognition service answered {res.status_code}")
        return res.json()


def queue_pages(repo: Repository, document_id: str) -> bool:
    """Mark every page as waiting, so the viewer can show that text is coming.

    False (and nothing changes) if the document is already being transcribed.
    """
    with _running_lock:
        if document_id in _running:
            return False
        _running.add(document_id)
    for page in repo.list_pages(document_id):
        repo.update_page(page["id"], {"status": "queued", "transcription_error": None})
    return True


def transcribe_document(
    repo: Repository,
    storage: ObjectStorage,
    htr: HtrClient,
    document_id: str,
    language: str | None,
) -> None:
    """Recognize every page of a document. A failed page does not stop the others."""
    try:
        _transcribe_pages(repo, storage, htr, document_id, language)
    finally:
        with _running_lock:
            _running.discard(document_id)


def _transcribe_pages(repo, storage, htr, document_id, language):
    for page in repo.list_pages(document_id):
        repo.update_page(page["id"], {"status": "processing"})
        try:
            image = storage.download(page["image_path"])
            if image is None:
                raise HtrError("Page image is missing")
            result = htr.transcribe(image, page["image_path"].rsplit("/", 1)[-1], language)
        except HtrError as exc:
            repo.update_page(page["id"], {"status": "failed", "transcription_error": str(exc)})
            continue
        except Exception:
            logger.exception("HTR failed for page %s", page["id"])
            repo.update_page(
                page["id"],
                {"status": "failed", "transcription_error": "Unexpected error during recognition"},
            )
            continue
        repo.update_page(
            page["id"],
            {
                "status": "done",
                "transcription": result,
                "transcription_error": None,
                "transcribed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
