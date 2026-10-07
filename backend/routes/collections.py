from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from database.repository import Repository
from services.storage import ObjectStorage
from deps import get_repo, get_storage
from schemas import (CollectionCreate, CollectionOut, DocumentOut, FileResult,
                     UploadReport)
from services.ingest import ingest_upload

router = APIRouter(prefix="/api/collections", tags=["collections"])


def _require_collection(repo: Repository, collection_id: UUID) -> dict:
    collection = repo.get_collection(str(collection_id))
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@router.post("", response_model=CollectionOut, status_code=201)
def create_collection(payload: CollectionCreate, repo: Repository = Depends(get_repo)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be empty")
    return repo.create_collection(name, payload.description)


@router.get("", response_model=list[CollectionOut])
def list_collections(repo: Repository = Depends(get_repo)):
    return repo.list_collections()


@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: UUID, repo: Repository = Depends(get_repo)):
    return _require_collection(repo, collection_id)


@router.get("/{collection_id}/documents", response_model=list[DocumentOut])
def list_documents(collection_id: UUID, repo: Repository = Depends(get_repo)):
    _require_collection(repo, collection_id)
    return repo.list_documents(str(collection_id))


# Plain `def` (not async): FastAPI runs it in a worker thread, so slow PDF
# rendering does not block other requests.
@router.post("/{collection_id}/uploads", response_model=UploadReport)
def upload_files(
    collection_id: UUID,
    files: list[UploadFile] = File(...),
    repo: Repository = Depends(get_repo),
    storage: ObjectStorage = Depends(get_storage),
):
    """Bulk upload: PDF, JPG/JPEG, PNG, heic or ZIP of those. Multiple files allowed.

    Returns a per-file report. Status 201 if at least one file was accepted,
    422 if every file was rejected.
    """
    _require_collection(repo, collection_id)

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