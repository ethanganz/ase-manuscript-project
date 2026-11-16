import mimetypes
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

import config
from database.repository import Repository
from deps import (
    get_current_user,
    get_optional_user,
    get_repo,
    get_storage,
    require_visible_collection,
)
from schemas import DocumentOut, PageOut, PageTranscriptionOut, TranscribeQueued
from services import htr_worker
from services.storage import ObjectStorage

router = APIRouter(prefix="/api", tags=["documents"])


def _require_visible_document(repo: Repository, document_id: UUID, user: dict | None) -> dict:
    """The document, or 404 if it is missing or in someone else's private collection."""
    doc = repo.get_document(str(document_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    require_visible_collection(repo, doc["collection_id"], user)
    return doc


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: UUID,
    repo: Repository = Depends(get_repo),
    user: dict | None = Depends(get_optional_user),
):
    return _require_visible_document(repo, document_id, user)


@router.get("/documents/{document_id}/pages", response_model=list[PageOut])
def list_pages(
    document_id: UUID,
    repo: Repository = Depends(get_repo),
    user: dict | None = Depends(get_optional_user),
):
    _require_visible_document(repo, document_id, user)
    return repo.list_pages(str(document_id))


@router.get("/pages/{page_id}/image")
def get_page_image(
    page_id: UUID,
    repo: Repository = Depends(get_repo),
    storage: ObjectStorage = Depends(get_storage),
    user: dict | None = Depends(get_optional_user),
):
    page = repo.get_page(str(page_id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    _require_visible_document(repo, page["document_id"], user)
    data = storage.download(page["image_path"])
    if data is None:
        raise HTTPException(status_code=404, detail="Image file missing")
    media_type = mimetypes.guess_type(page["image_path"])[0] or "application/octet-stream"
    return Response(content=data, media_type=media_type)


def _require_owner(repo: Repository, collection_id: str, user: dict) -> None:
    collection = require_visible_collection(repo, collection_id, user)
    if collection.get("owner_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the owner can start transcription")


@router.get("/pages/{page_id}/transcription", response_model=PageTranscriptionOut)
def get_page_transcription(
    page_id: UUID,
    repo: Repository = Depends(get_repo),
    user: dict | None = Depends(get_optional_user),
):
    """What the model read on this page, line by line, plus how far it is."""
    page = repo.get_page(str(page_id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    _require_visible_document(repo, page["document_id"], user)
    lines = repo.list_page_lines(str(page_id)) if page["status"] == "complete" else []
    return {
        "page_id": page["id"],
        "status": page["status"],
        "error": page.get("htr_error"),
        "width": page.get("htr_width"),
        "height": page.get("htr_height"),
        "lines": lines,
    }


@router.post("/pages/{page_id}/transcribe", response_model=TranscribeQueued, status_code=202)
def transcribe_page(
    page_id: UUID,
    repo: Repository = Depends(get_repo),
    storage: ObjectStorage = Depends(get_storage),
    user: dict = Depends(get_current_user),
):
    """Queue one page for recognition (also retries a failed page). Owner only."""
    page = repo.get_page(str(page_id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    doc = _require_visible_document(repo, page["document_id"], user)
    _require_owner(repo, doc["collection_id"], user)
    if not config.HTR_ENABLED:
        raise HTTPException(status_code=503, detail="Transcription is not enabled on this server")
    return {"queued_pages": int(htr_worker.enqueue_page(repo, storage, str(page_id)))}


@router.post(
    "/documents/{document_id}/transcribe", response_model=TranscribeQueued, status_code=202
)
def transcribe_document(
    document_id: UUID,
    repo: Repository = Depends(get_repo),
    storage: ObjectStorage = Depends(get_storage),
    user: dict = Depends(get_current_user),
):
    """Queue every page of a document that is not transcribed yet. Owner only."""
    doc = _require_visible_document(repo, document_id, user)
    _require_owner(repo, doc["collection_id"], user)
    if not config.HTR_ENABLED:
        raise HTTPException(status_code=503, detail="Transcription is not enabled on this server")
    return {"queued_pages": htr_worker.enqueue_document(repo, storage, str(document_id))}
