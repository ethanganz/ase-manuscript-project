import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, field_validator

from services.auth import MAX_PASSWORD_BYTES

"""
    This defines the shape of the data the API sends back, such as what a collection or a page looks like.

"""


EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _normalize_email(value: str) -> str:
    value = value.strip().lower()
    if not EMAIL_RE.fullmatch(value):
        raise ValueError("Enter a valid email address")
    return value


# Emails are stored lowercase so "Anna@Mail.com" and "anna@mail.com" match.
Email = Annotated[str, Field(max_length=254), AfterValidator(_normalize_email)]


# A first or last name: surrounding spaces removed, cannot be empty.
Name = Annotated[str, AfterValidator(str.strip), Field(min_length=1, max_length=100)]


# Request model for signing up.
class UserCreate(BaseModel):
    first_name: Name
    last_name: Name
    email: Email
    password: str = Field(min_length=8, max_length=MAX_PASSWORD_BYTES)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError("Password is too long")
        return value


# Request model for logging in.
class UserLogin(BaseModel):
    email: Email
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_BYTES)


# Response model for returning user data. Never includes the password hash.
class UserOut(BaseModel):
    id: UUID
    email: str
    first_name: str | None = None  # "First Last"
    last_name: str | None = None  # "First Last"
    created_at: datetime | None = None


# Request model for creating a new collection.
class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    is_public: bool = True  # False = only the owner can see it


# Request model for editing a collection. Only the fields sent are changed.
class CollectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)  # null or "" clears it


# Response model for returning collection data.
class CollectionOut(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    owner_id: UUID | None = None  # None for collections made before accounts existed
    is_public: bool = True
    created_at: datetime | None = None


# Response model for returning document metadata.
class DocumentOut(BaseModel):
    id: UUID
    collection_id: UUID
    original_filename: str
    source_archive: str | None = None
    file_type: str
    size_bytes: int
    sha256: str
    status: str
    created_at: datetime | None = None


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
    document_id: UUID | None = None
    page_count: int | None = None
    error: str | None = None


# Summary of a batch upload.
class UploadReport(BaseModel):
    collection_id: UUID
    accepted: int
    rejected: int
    results: list[FileResult]


class CountrySummary(BaseModel):
    country_code: str  # ISO 3166-1 alpha-2, e.g. "CH"
    mention_count: int
    place_count: int


class MentionOut(BaseModel):
    mention_id: UUID
    place_name: str
    snippet: str | None = None
    page_id: UUID  # the page image to open
    page_number: int
    document_id: UUID
    document_name: str
