from fastapi import APIRouter, Depends, HTTPException, Response

import config
from database.repository import Repository
from deps import get_current_user, get_repo
from schemas import UserCreate, UserLogin, UserOut
from services.auth import DUMMY_HASH, create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _start_session(response: Response, user: dict) -> None:
    """Log the user in by setting the token cookie."""
    response.set_cookie(
        config.AUTH_COOKIE_NAME,
        create_token(str(user["id"])),
        max_age=config.JWT_EXPIRE_MINUTES * 60,
        httponly=True,  # JavaScript cannot read it
        samesite="lax",  # not sent with POSTs from other sites
        secure=config.AUTH_COOKIE_SECURE,
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, response: Response, repo: Repository = Depends(get_repo)):
    """Create an account and log in."""
    if repo.get_user_by_email(payload.email) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    first_name = payload.first_name
    last_name = payload.last_name
    user = repo.create_user(payload.email, hash_password(payload.password), first_name, last_name)
    _start_session(response, user)
    return user


@router.post("/login", response_model=UserOut)
def login(payload: UserLogin, response: Response, repo: Repository = Depends(get_repo)):
    """Check email and password and log in."""
    user = repo.get_user_by_email(payload.email)
    password_ok = verify_password(payload.password, user["password_hash"] if user else DUMMY_HASH)
    if user is None or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    _start_session(response, user)
    return user


@router.post("/logout", status_code=204)
def logout():
    """Log out by removing the token cookie."""
    response = Response(status_code=204)
    response.delete_cookie(
        config.AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=config.AUTH_COOKIE_SECURE,
    )
    return response


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)):
    """Return the logged-in user."""
    return user
