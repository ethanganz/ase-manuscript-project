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
    email_verified: bool = False
    created_at: datetime | None = None


# Request model for opening the link in the verification email.
class VerifyEmail(BaseModel):
    token: str = Field(min_length=1, max_length=2000)


# Request model for asking for a new verification email.
class ResendVerification(BaseModel):
    email: Email


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


ReportReason = Literal["spam", "inappropriate", "copyright", "misleading", "other"]


# Request model for reporting a collection.
class ReportCreate(BaseModel):
    reason: ReportReason
    details: str | None = Field(default=None, max_length=1000)


# A report on one of the user's own collections. Never says who reported it.
class ReceivedReportOut(BaseModel):
    id: UUID
    collection_id: UUID
    collection_name: str
    reason: ReportReason
    details: str | None = None
    created_at: datetime | None = None
    read: bool


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
    language: str | None = None  # "de" | "la" | None (unknown)
    created_at: datetime | None = None


# Response model for returning page metadata.
class PageOut(BaseModel):
    id: UUID
    document_id: UUID
    page_number: int
    width: int
    height: int
    status: str  # pending | queued | processing | done | failed


# A place the HTR service found in a line. `start`/`end` index into the line text.
class PlaceSpan(BaseModel):
    start: int
    end: int
    text: str
    sources: list[str] = []
    score: float | None = None
    identities: list[dict] = []  # possible official places, with coordinates; unverified


class TranscriptionLine(BaseModel):
    text: str
    bbox: list[int]  # left, top, right, bottom in page-image pixels
    places: list[PlaceSpan] = []


# Response model for the recognized text of one page.
class PageTranscriptionOut(BaseModel):
    page_id: UUID
    status: str
    error: str | None = None
    language: str | None = None
    lines: list[TranscriptionLine] = []


# Request model for running handwriting recognition again on a document.
class TranscribeRequest(BaseModel):
    language: Literal["de", "la", "unknown"] | None = None  # None = keep the document's


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
