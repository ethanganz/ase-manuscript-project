import mimetypes
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from database.repository import Repository
from deps import get_repo, get_storage
from schemas import DocumentOut, PageOut
from services.storage import ObjectStorage

router = APIRouter(prefix="/api", tags=["documents"])
register_heif_opener()

PREVIEW_TYPES = {
    "pdf": "application/pdf",
    "jpeg": "image/jpeg",
    "png": "image/png",
}


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: UUID, repo: Repository = Depends(get_repo)):
    doc = repo.get_document(str(document_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/documents/{document_id}/pages", response_model=list[PageOut])
def list_pages(document_id: UUID, repo: Repository = Depends(get_repo)):
    if repo.get_document(str(document_id)) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return repo.list_pages(str(document_id))


@router.get("/documents/{document_id}/preview")
def preview_document(
    document_id: UUID,
    repo: Repository = Depends(get_repo),
    storage: ObjectStorage = Depends(get_storage),
):
    doc = repo.get_document(str(document_id))
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    path = doc.get("original_path")
    data = storage.download(path) if path else None
    if data is None:
        raise HTTPException(status_code=404, detail="Original file not found")

    file_type = doc["file_type"]
    if file_type == "heic":
        output = BytesIO()
        with Image.open(BytesIO(data)) as image:
            ImageOps.exif_transpose(image).convert("RGB").save(output, "JPEG", quality=90)
        data = output.getvalue()
        media_type = "image/jpeg"
    else:
        media_type = PREVIEW_TYPES.get(file_type)
        if media_type is None:
            raise HTTPException(status_code=415, detail="Preview not supported for this file")

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": "inline", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/pages/{page_id}/image")
def get_page_image(
    page_id: UUID,
    repo: Repository = Depends(get_repo),
    storage: ObjectStorage = Depends(get_storage),
):
    page = repo.get_page(str(page_id))
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    data = storage.download(page["image_path"])
    if data is None:
        raise HTTPException(status_code=404, detail="Image file missing")
    media_type = mimetypes.guess_type(page["image_path"])[0] or "application/octet-stream"
    return Response(content=data, media_type=media_type)
