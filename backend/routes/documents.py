import mimetypes
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response

from database.repository import Repository
from deps import (
    get_current_user,
    get_htr,
    get_optional_user,
    get_repo,
    get_storage,
    require_visible_collection,
)
from schemas import DocumentOut, PageOut, PageTranscriptionOut, TranscribeRequest
from services.htr import HtrClient, queue_pages, transcribe_document
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


@router.get("/pages/{page_id}/transcription", response_model=PageTranscriptionOut)
def get_page_transcription(
    page_id: UUID,
    repo: Repository = Depends(get_repo),
    user: dict | None = Depends(get_optional_user),
):
    """The recognized lines of a page. Empty until status is "done"."""
    page = repo.get_page(str(page_id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    _require_visible_document(repo, page["document_id"], user)
    result = page.get("transcription") or {}
    return {
        "page_id": page["id"],
        "status": page["status"],
        "error": page.get("transcription_error"),
        "language": result.get("language"),
        "lines": result.get("lines", []),
    }


@router.post("/documents/{document_id}/transcribe", status_code=202)
def transcribe(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    payload: TranscribeRequest | None = None,
    repo: Repository = Depends(get_repo),
    storage: ObjectStorage = Depends(get_storage),
    htr: HtrClient | None = Depends(get_htr),
    user: dict = Depends(get_current_user),
):
    """Run handwriting recognition (again) on every page. Only the owner may do this.

    For documents uploaded before recognition was set up, or after a failure.
    """
    doc = _require_visible_document(repo, document_id, user)
    collection = repo.get_collection(doc["collection_id"])
    if collection.get("owner_id") != user["id"]:
        raise HTTPException(status_code=403, detail="You can only transcribe your own documents")
    if htr is None:
        raise HTTPException(status_code=503, detail="Handwriting recognition is not set up")

    language = doc.get("language")
    if payload and payload.language:
        language = None if payload.language == "unknown" else payload.language
    if not queue_pages(repo, doc["id"]):
        raise HTTPException(status_code=409, detail="This document is already being transcribed")
    background_tasks.add_task(transcribe_document, repo, storage, htr, doc["id"], language)
    return {"document_id": doc["id"], "status": "queued", "language": language}
