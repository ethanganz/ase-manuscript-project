from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

'''
    This defines the shape of the data the API sends back, such as what a collection or a page looks like.

'''


# Request model for creating a new collection.
class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)


# Response model for returning collection data.
class CollectionOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None


# Response model for returning document metadata.
class DocumentOut(BaseModel):
    id: UUID
    collection_id: UUID
    original_filename: str
    source_archive: Optional[str] = None
    file_type: str
    size_bytes: int
    sha256: str
    status: str
    created_at: Optional[datetime] = None


# Response model for returning page metadata.
class PageOut(BaseModel):
    id: UUID
    document_id: UUID
    page_number: int
    width: int
    height: int
    status: str


# Result for a single uploaded file.
class FileResult(BaseModel):
    filename: str
    status: Literal["accepted", "rejected"]
    document_id: Optional[UUID] = None
    page_count: Optional[int] = None
    error: Optional[str] = None


# Summary of a batch upload.
class UploadReport(BaseModel):
    collection_id: UUID
    accepted: int
    rejected: int
    results: list[FileResult]