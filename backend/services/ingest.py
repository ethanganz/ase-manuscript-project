"""Upload ingestion: validate -> make page images -> upload to Supabase Storage -> record.

Rules:
  * File type is decided by CONTENT (magic bytes), never by the extension.
  * File names from users / ZIP entries are NEVER used in storage keys.
    Keys are  <collection_id>/<document_id>/...
  * Work happens in a temporary folder that is always deleted afterwards.
  * A file either fully succeeds (objects + DB rows) or leaves nothing behind.
"""
import hashlib
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Optional
from uuid import uuid4

import pymupdf
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

import config
from database.repository import Repository
from services.storage import ObjectStorage
import logging

logger = logging.getLogger("uvicorn.error")

register_heif_opener()  # lets Pillow open .heic files

EXT = {"pdf": "pdf", "jpeg": "jpg", "png": "png", "heic": "heic"}
CONTENT_TYPE = {"pdf": "application/pdf", "jpeg": "image/jpeg",
                "png": "image/png", "heic": "image/heic"}
PAGE_CONTENT_TYPE = {"png": "image/png", "jpg": "image/jpeg"}
HEIC_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1", b"heif"}


class IngestError(Exception):
    """A user-facing reason why a file was rejected."""


@dataclass
class FileOutcome:
    filename: str
    accepted: bool
    document_id: Optional[str] = None
    page_count: Optional[int] = None
    error: Optional[str] = None


@dataclass
class _Page:
    number: int
    path: Path      # local temp file
    ext: str        # "png" or "jpg" (what gets stored as the page image)
    width: int
    height: int


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def sniff_type(path: Path) -> Optional[str]:
    """Return 'pdf' | 'jpeg' | 'png' | 'heic' | 'zip' from file content, else None."""
    with open(path, "rb") as f:
        head = f.read(12)
    if head.startswith(b"%PDF-"):
        return "pdf"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[4:8] == b"ftyp" and head[8:12] in HEIC_BRANDS:
        return "heic"
    if head.startswith((b"PK\x03\x04", b"PK\x05\x06")):
        return "zip"
    return None


def safe_filename(name: str) -> str:
    """Keep only the base name, drop control chars, cap length."""
    base = re.split(r"[\\/]", name or "")[-1]
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()
    return base[:255] or "unnamed"


def save_stream_with_limit(src: BinaryIO, dest: Path, limit: int) -> None:
    total = 0
    with open(dest, "wb") as out:
        while chunk := src.read(1024 * 1024):
            total += len(chunk)
            if total > limit:
                raise IngestError(
                    f"File is larger than the {limit // config.MB} MB limit")
            out.write(chunk)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Page extraction (all local, inside a temp folder)
# --------------------------------------------------------------------------
def _image_page(src: Path, pages_dir: Path, kind: str) -> list[_Page]:
    try:
        if kind == "heic":
            # Browsers cannot show HEIC, so the PAGE image is a JPEG.
            # The original .heic is still stored untouched.
            dest = pages_dir / "0001.jpg"
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                im.save(dest, "JPEG", quality=95)
                width, height = im.size
            return [_Page(1, dest, "jpg", width, height)]

        with Image.open(src) as im:
            im.verify()  # cheap integrity check
        with Image.open(src) as im:
            width, height = im.size
        return [_Page(1, src, EXT[kind], width, height)]
    except Exception as exc:  # corrupt, truncated, decompression bomb...
        raise IngestError("Image is corrupt or unreadable") from exc


def _pdf_pages(src: Path, pages_dir: Path) -> list[_Page]:
    try:
        pdf = pymupdf.open(src)
    except Exception as exc:
        raise IngestError("PDF is corrupt or unreadable") from exc
    with pdf:
        if pdf.needs_pass:
            raise IngestError("Password-protected PDFs are not supported")
        if pdf.page_count == 0:
            raise IngestError("PDF has no pages")
        if pdf.page_count > config.MAX_PDF_PAGES:
            raise IngestError(
                f"PDF has {pdf.page_count} pages (limit {config.MAX_PDF_PAGES})")
        zoom = config.PDF_RENDER_DPI / 72
        matrix = pymupdf.Matrix(zoom, zoom)
        pages: list[_Page] = []
        try:
            for i, page in enumerate(pdf, start=1):
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                dest = pages_dir / f"{i:04d}.png"
                pix.save(dest)
                pages.append(_Page(i, dest, "png", pix.width, pix.height))
        except Exception as exc:
            raise IngestError(f"Could not render PDF page {len(pages) + 1}") from exc
        return pages


# --------------------------------------------------------------------------
# One file -> one document
# --------------------------------------------------------------------------
def _ingest_single(repo: Repository, storage: ObjectStorage, collection_id: str,
                   filename: str, src: Path, kind: str,
                   source_archive: Optional[str] = None) -> FileOutcome:
    document_id = str(uuid4())   
    prefix = f"collections/{collection_id}/documents/{document_id}"
    uploaded: list[str] = []      # storage keys, so we can undo on failure
    doc_created = False

    with tempfile.TemporaryDirectory() as work:
        pages_dir = Path(work) / "pages"
        pages_dir.mkdir()
        try:
            pages = _pdf_pages(src, pages_dir) if kind == "pdf" \
                else _image_page(src, pages_dir, kind)

            original_key = f"{prefix}/original.{EXT[kind]}"
            storage.upload(original_key, src, CONTENT_TYPE[kind])
            uploaded.append(original_key)

            page_rows = []
            for p in pages:
                key = f"{prefix}/pages/{p.number:04d}.{p.ext}"
                storage.upload(key, p.path, PAGE_CONTENT_TYPE[p.ext])
                uploaded.append(key)
                page_rows.append({
                    "id": str(uuid4()),
                    "document_id": document_id,
                    "page_number": p.number,
                    "image_path": key,
                    "width": p.width,
                    "height": p.height,
                    "status": "pending",   # picked up by the image-processing stage later
                })

            repo.create_document({
                "id": document_id,
                "collection_id": collection_id,
                "original_filename": safe_filename(filename),
                "source_archive": safe_filename(source_archive) if source_archive else None,
                "file_type": kind,
                "size_bytes": src.stat().st_size,
                "sha256": _sha256(src),
                "status": "uploaded",
                "original_path": original_key,
            })
            doc_created = True
            repo.create_pages(page_rows)
            return FileOutcome(filename, True, document_id, len(pages))
        except IngestError:
            _rollback(repo, storage, uploaded, document_id, doc_created)
            raise
        except Exception as exc:
            logger.exception("Ingest failed for %s", filename)
            _rollback(repo, storage, uploaded, document_id, doc_created)
            raise IngestError("Unexpected error while processing the file") from exc


def _rollback(repo: Repository, storage: ObjectStorage, uploaded: list[str],
              document_id: str, doc_created: bool) -> None:
    try:
        storage.remove(uploaded)
    except Exception:
        pass
    if doc_created:
        try:
            repo.delete_document(document_id)
        except Exception:
            pass


# --------------------------------------------------------------------------
# ZIP handling
# --------------------------------------------------------------------------
def _is_junk(name: str) -> bool:
    parts = PurePosixPath(name.replace("\\", "/")).parts
    return (not parts or parts[0] == "__MACOSX"
            or parts[-1].startswith(".") or parts[-1].lower() == "thumbs.db")


def _ingest_zip(repo: Repository, storage: ObjectStorage, collection_id: str,
                filename: str, src: Path) -> list[FileOutcome]:
    try:
        zf = zipfile.ZipFile(src)
    except zipfile.BadZipFile:
        return [FileOutcome(filename, False, error="ZIP file is corrupt")]

    outcomes: list[FileOutcome] = []
    with zf:
        infos = sorted((i for i in zf.infolist()
                        if not i.is_dir() and not _is_junk(i.filename)),
                       key=lambda i: i.filename)
        if not infos:
            return [FileOutcome(filename, False, error="ZIP contains no files")]
        if len(infos) > config.MAX_ZIP_ENTRIES:
            return [FileOutcome(
                filename, False,
                error=f"ZIP has {len(infos)} files (limit {config.MAX_ZIP_ENTRIES})")]
        if sum(i.file_size for i in infos) > config.MAX_ZIP_UNCOMPRESSED_BYTES:
            return [FileOutcome(filename, False, error="ZIP is too large when unpacked")]

        budget = config.MAX_ZIP_UNCOMPRESSED_BYTES  # enforced on REAL bytes read
        with tempfile.TemporaryDirectory() as tmp:
            for info in infos:
                label = f"{filename}/{info.filename}"
                member = Path(tmp) / "member"
                try:
                    if info.flag_bits & 0x1:
                        raise IngestError("Encrypted ZIP entries are not supported")
                    with zf.open(info) as fh:
                        save_stream_with_limit(
                            fh, member, min(config.MAX_FILE_BYTES, budget))
                    budget -= member.stat().st_size
                    kind = sniff_type(member)
                    if kind == "zip":
                        raise IngestError("Nested ZIP files are not supported")
                    if kind is None:
                        raise IngestError(
                            "Unsupported file type (need PDF, JPG, PNG or HEIC)")
                    out = _ingest_single(
                        repo, storage, collection_id,
                        PurePosixPath(info.filename).name, member, kind,
                        source_archive=filename)
                    out.filename = label
                    outcomes.append(out)
                except IngestError as exc:
                    outcomes.append(FileOutcome(label, False, error=str(exc)))
                finally:
                    member.unlink(missing_ok=True)
    return outcomes


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------
def ingest_upload(repo: Repository, storage: ObjectStorage, collection_id: str,
                  filename: str, stream: BinaryIO) -> list[FileOutcome]:
    """Process one uploaded file. Returns one outcome per resulting document
    (a ZIP yields one outcome per file inside it)."""
    filename = safe_filename(filename)
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "upload"
        try:
            save_stream_with_limit(stream, src, config.MAX_FILE_BYTES)
        except IngestError as exc:
            return [FileOutcome(filename, False, error=str(exc))]
        if src.stat().st_size == 0:
            return [FileOutcome(filename, False, error="File is empty")]

        kind = sniff_type(src)
        if kind is None:
            return [FileOutcome(
                filename, False,
                error="Unsupported file type (need PDF, JPG, PNG, HEIC or ZIP)")]
        if kind == "zip":
            return _ingest_zip(repo, storage, collection_id, filename, src)
        try:
            return [_ingest_single(repo, storage, collection_id, filename, src, kind)]
        except IngestError as exc:
            return [FileOutcome(filename, False, error=str(exc))]