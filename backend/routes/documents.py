import hashlib
import mimetypes
import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from database.database import get_supabase

router = APIRouter(prefix="/api", tags=["documents"])
SUPPORTED_TYPES = {"pdf": "application/pdf", "jpeg": "image/jpeg", "png": "image/png", "heic": "image/heic"}


def normalize_file_type(filename: str) -> str:
    """Return a database-safe file type for a filename or extension."""
    file_type = PurePosixPath(filename).suffix.lower().lstrip(".")
    if file_type not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported file type: {filename}")
    return file_type


def sha256_hex(file_obj) -> str:
    hasher = hashlib.sha256()
    for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
        hasher.update(chunk)
    file_obj.seek(0)
    return hasher.hexdigest()


def _storage_path(collection_id: str, document_id: str, filename: str) -> str:
    safe_name = PurePosixPath(filename).name.replace("/", "_")
    return f"collections/{collection_id}/documents/{document_id}/{safe_name}"


@router.get("/collections")
def list_collections() -> list[dict]:
    try:
        result = get_supabase().table("collections").select("id, name, description").order("created_at").execute()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to load collections: {exc}") from exc

    return result.data or []


@router.post("/collections")
def create_collection(payload: dict) -> dict:
    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="Collection name is required")

    try:
        result = get_supabase().table("collections").insert({
            "name": name,
            "description": description or None,
        }).execute()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to create collection: {exc}") from exc

    data = result.data[0] if result.data else {}
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "description": data.get("description"),
    }


@router.post("/documents/upload")
async def upload_document(
    collection_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    if not collection_id:
        raise HTTPException(status_code=400, detail="collection_id is required")

    if file.size is not None and file.size > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File must be 100 MB or smaller")

    try:
        file_type = normalize_file_type(file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        supabase = get_supabase()
        collection = supabase.table("collections").select("id").eq("id", collection_id).execute()
        if not collection.data:
            raise HTTPException(status_code=404, detail="Collection not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to validate collection: {exc}") from exc

    document_id = str(uuid.uuid4())
    storage_path = _storage_path(collection_id, document_id, file.filename or "upload")

    try:
        contents = await file.read()
        file_hash = hashlib.sha256(contents).hexdigest()
        content_type = mimetypes.guess_type(file.filename or "")[0] or SUPPORTED_TYPES[file_type]
        storage_result = supabase.storage.from_("documents").upload(
            storage_path,
            contents,
            {"content-type": content_type, "upsert": "false"},
        )
        if getattr(storage_result, "error", None):
            raise RuntimeError(str(storage_result.error))

        document_result = supabase.table("documents").insert({
            "id": document_id,
            "collection_id": collection_id,
            "original_filename": file.filename,
            "source_archive": storage_path,
            "file_type": file_type,
            "size_bytes": len(contents),
            "sha256": file_hash,
            "status": "uploaded",
            "original_path": storage_path,
        }).execute()
        if not document_result.data:
            raise RuntimeError("Document insert did not return a row")
    except HTTPException:
        raise
    except Exception as exc:
        # Clean up uploaded storage object if the database insert fails.
        try:
            supabase.storage.from_("documents").remove([storage_path])
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Upload failed: {exc}") from exc

    return {
        "id": document_id,
        "collection_id": collection_id,
        "filename": file.filename,
        "storage_path": storage_path,
        "file_type": file_type,
        "size_bytes": len(contents),
        "sha256": file_hash,
        "status": "uploaded",
    }
