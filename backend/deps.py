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


def get_current_user(
    token: Optional[str] = Depends(auth_cookie),
    repo: Repository = Depends(get_repo),
) -> dict:
    """FastAPI dependency. Returns the logged-in user or answers 401."""
    user_id = decode_token(token) if token else None
    user = repo.get_user(user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

