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
    created_at: datetime | None = None


# Response model for returning page metadata.
class PageOut(BaseModel):
    id: UUID
    document_id: UUID
    page_number: int
    width: int
    height: int
    status: str


# One handwritten line of a page, as read by the model.
class LineOut(BaseModel):
    line_index: int  # 0 = top line
    text: str
    bbox: list[int] | None = None  # [left, top, right, bottom] in pixels of the upright page
    polygon: list[list[int]] | None = None
    # Place mentions: start/end (Unicode code points, end exclusive), text,
    # place_link_status and the full list of official_place_candidates.
    places: list[dict] = []


# What the model read on one page, and how far the reading is.
class PageTranscriptionOut(BaseModel):
    page_id: UUID
    status: str  # pending | queued | running | complete | failed
    error: str | None = None  # why it failed
    width: int | None = None  # size of the upright page the line boxes refer to
    height: int | None = None
    lines: list[LineOut] = []


# Answer to "please transcribe this".
class TranscribeQueued(BaseModel):
    queued_pages: int


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


class ChatTurn(BaseModel):
    """One earlier message of the chat. The browser keeps the chat and sends it back."""

    role: Literal["user", "assistant"]
    text: str = Field(max_length=4000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    # Earlier messages, oldest first. The server uses only the last few.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)

    @field_validator("question")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be empty")
        return value


class AskSource(BaseModel):
    """One transcript line the answer is based on, with where to find the page."""

    label: int  # the number used in the answer, e.g. [1]
    id: UUID
    page_id: UUID
    document_id: UUID | None = None
    page_number: int | None = None
    line_index: int | None = None  # position on the page, to highlight the line
    language: str | None = None
    text: str


class AskResponse(BaseModel):
    answer: str
    sources: list[AskSource]
    # True only when the answer cites at least one real line.
    grounded: bool
    # The answer split by origin. None means that part is empty.
    document_answer: str | None = None
    general_answer: str | None = None
