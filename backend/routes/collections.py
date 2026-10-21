from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from database.repository import Repository
from services.storage import ObjectStorage
from deps import (can_view, get_current_user, get_optional_user, get_repo,
                  get_storage, require_visible_collection)
from schemas import (CollectionCreate, CollectionOut, CollectionUpdate, DocumentOut,
                     FileResult, UploadReport)
from services.ingest import ingest_upload

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.post("", response_model=CollectionOut, status_code=201)
def create_collection(payload: CollectionCreate, repo: Repository = Depends(get_repo),
                      user: dict = Depends(get_current_user)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    return repo.create_collection(name, payload.description, user["id"], payload.is_public)


@router.get("", response_model=list[CollectionOut])
def list_collections(repo: Repository = Depends(get_repo),
                     user: Optional[dict] = Depends(get_optional_user)):
    """Public collections, plus the logged-in user's own private ones."""
    return [c for c in repo.list_collections() if can_view(c, user)]


@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: UUID, repo: Repository = Depends(get_repo),
                   user: Optional[dict] = Depends(get_optional_user)):
    return require_visible_collection(repo, str(collection_id), user)


@router.patch("/{collection_id}", response_model=CollectionOut)
def update_collection(collection_id: UUID, payload: CollectionUpdate,
                      repo: Repository = Depends(get_repo),
                      user: dict = Depends(get_current_user)):
    """Rename a collection or change its description. Only the owner may do this."""
    collection = require_visible_collection(repo, str(collection_id), user)
    if collection.get("owner_id") != user["id"]:
        raise HTTPException(status_code=403,
                            detail="You can only edit your own collections")

    fields = {}
    if "name" in payload.model_fields_set:
        name = (payload.name or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="Name cannot be empty")
        fields["name"] = name
    if "description" in payload.model_fields_set:
        fields["description"] = (payload.description or "").strip() or None

    if not fields:
        return collection
    return repo.update_collection(str(collection_id), fields)


@router.get("/{collection_id}/documents", response_model=list[DocumentOut])
def list_documents(collection_id: UUID, repo: Repository = Depends(get_repo),
                   user: Optional[dict] = Depends(get_optional_user)):
    require_visible_collection(repo, str(collection_id), user)
    return repo.list_documents(str(collection_id))


# Plain `def` (not async): FastAPI runs it in a worker thread, so slow PDF
# rendering does not block other requests.
@router.post("/{collection_id}/uploads", response_model=UploadReport)
def upload_files(
    collection_id: UUID,
    files: list[UploadFile] = File(...),
    repo: Repository = Depends(get_repo),
    storage: ObjectStorage = Depends(get_storage),
    user: dict = Depends(get_current_user),
):
    """Bulk upload: PDF, JPG/JPEG, PNG, heic or ZIP of those. Multiple files allowed.

    Only the owner of the collection may upload. Returns a per-file report.
    Status 201 if at least one file was accepted, 422 if every file was rejected.
    """
    collection = require_visible_collection(repo, str(collection_id), user)
    if collection.get("owner_id") != user["id"]:
        raise HTTPException(status_code=403,
                            detail="You can only upload to your own collections")

    results: list[FileResult] = []
    for upload in files:
        outcomes = ingest_upload(
            repo, storage, str(collection_id), upload.filename or "unnamed", upload.file)
        
        for o in outcomes:
            results.append(FileResult(
                filename=o.filename,
                status="accepted" if o.accepted else "rejected",
                document_id=o.document_id,
                page_count=o.page_count,
                error=o.error,
            ))

    accepted = sum(r.status == "accepted" for r in results)
    report = UploadReport(
        collection_id=collection_id, accepted=accepted,
        rejected=len(results) - accepted, results=results)
    return JSONResponse(
        status_code=201 if accepted else 422,
        content=report.model_dump(mode="json"))