import mimetypes
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from database.repository import Repository
from deps import get_optional_user, get_repo, get_storage, require_visible_collection
from schemas import DocumentOut, PageOut
from services.storage import ObjectStorage

router = APIRouter(prefix="/api", tags=["documents"])


def _require_visible_document(repo: Repository, document_id: UUID,
                              user: Optional[dict]) -> dict:
    """The document, or 404 if it is missing or in someone else's private collection."""
    doc = repo.get_document(str(document_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    require_visible_collection(repo, doc["collection_id"], user)
    return doc


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: UUID, repo: Repository = Depends(get_repo),
                 user: Optional[dict] = Depends(get_optional_user)):
    return _require_visible_document(repo, document_id, user)


@router.get("/documents/{document_id}/pages", response_model=list[PageOut])
def list_pages(document_id: UUID, repo: Repository = Depends(get_repo),
               user: Optional[dict] = Depends(get_optional_user)):
    _require_visible_document(repo, document_id, user)
    return repo.list_pages(str(document_id))


@router.get("/pages/{page_id}/image")
def get_page_image(
    page_id: UUID,
    repo: Repository = Depends(get_repo),
    storage: ObjectStorage = Depends(get_storage),
    user: Optional[dict] = Depends(get_optional_user),
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
