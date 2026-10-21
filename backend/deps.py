from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyCookie

import config
from database.repository import Repository, SupabaseRepository
from services.auth import decode_token
from services.storage import ObjectStorage, SupabaseStorage

# Reads the login cookie. Also shows the lock icon in the API docs.
auth_cookie = APIKeyCookie(name=config.AUTH_COOKIE_NAME, auto_error=False)


def get_repo() -> Repository:
    """FastAPI dependency. Tests override this with an in-memory repository."""
    return SupabaseRepository()


def get_storage() -> ObjectStorage:
    """FastAPI dependency. Tests override this with in-memory storage."""
    return SupabaseStorage()


def get_optional_user(
    token: Optional[str] = Depends(auth_cookie),
    repo: Repository = Depends(get_repo),
) -> Optional[dict]:
    """FastAPI dependency. Returns the logged-in user, or None for visitors."""
    user_id = decode_token(token) if token else None
    return repo.get_user(user_id) if user_id else None


def get_current_user(user: Optional[dict] = Depends(get_optional_user)) -> dict:
    """FastAPI dependency. Returns the logged-in user or answers 401."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def can_view(collection: dict, user: Optional[dict]) -> bool:
    """Public collections are for everyone; private ones only for their owner."""
    if collection.get("is_public", True):
        return True
    return user is not None and collection.get("owner_id") == user["id"]


def require_visible_collection(repo: Repository, collection_id: str,
                               user: Optional[dict]) -> dict:
    """Return the collection, or answer 404 if it is missing or private to someone else.

    404 (not 403) so visitors cannot tell that a private collection exists.
    """
    collection = repo.get_collection(collection_id) if collection_id else None
    if collection is None or not can_view(collection, user):
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection

