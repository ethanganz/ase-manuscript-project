from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response

import config
from database.repository import Repository
from deps import get_current_user, get_mailer, get_repo
from schemas import ResendVerification, UserCreate, UserLogin, UserOut, VerifyEmail
from services.auth import (DUMMY_HASH, create_email_token, create_token, decode_email_token,
                           hash_password, verify_password)
from services.email import EmailSender, send_verification_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _start_session(response: Response, user: dict) -> None:
    """Log the user in by setting the token cookie."""
    response.set_cookie(
        config.AUTH_COOKIE_NAME,
        create_token(str(user["id"])),
        max_age=config.JWT_EXPIRE_MINUTES * 60,
        httponly=True,       # JavaScript cannot read it
        samesite="lax",      # not sent with POSTs from other sites
        secure=config.AUTH_COOKIE_SECURE,
        path="/",
    )


def _queue_verification_email(tasks: BackgroundTasks, mailer: EmailSender, user: dict) -> None:
    """Send the email after the response, so how long a request takes does not
    reveal whether an account exists. Failures are logged; the user can ask again."""
    token = create_email_token(str(user["id"]), user["email"])
    tasks.add_task(send_verification_email, mailer, user, token)


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, tasks: BackgroundTasks,
             repo: Repository = Depends(get_repo), mailer: EmailSender = Depends(get_mailer)):
    """Create an account and email a verification link. Does not log in."""
    if repo.get_user_by_email(payload.email) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    first_name = payload.first_name
    last_name = payload.last_name
    user = repo.create_user(payload.email, hash_password(payload.password), first_name, last_name)
    _queue_verification_email(tasks, mailer, user)
    return user


@router.post("/login", response_model=UserOut)
def login(payload: UserLogin, response: Response, repo: Repository = Depends(get_repo)):
    """Check email and password and log in."""
    user = repo.get_user_by_email(payload.email)
    password_ok = verify_password(
        payload.password, user["password_hash"] if user else DUMMY_HASH)
    if user is None or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    # Only said after a correct password, so it does not reveal which emails exist.
    if not user.get("email_verified"):
        raise HTTPException(status_code=403,
                            detail="Please verify your email first. Check your inbox for the link.")
    _start_session(response, user)
    return user


@router.post("/verify-email", response_model=UserOut)
def verify_email(payload: VerifyEmail, response: Response, repo: Repository = Depends(get_repo)):
    """Confirm the email with the token from the link, then log in."""
    claims = decode_email_token(payload.token)
    user = repo.get_user(claims[0]) if claims else None
    # The email must still match, so an old link stops working after a change.
    if user is None or user["email"] != claims[1]:
        raise HTTPException(status_code=400,
                            detail="This verification link is invalid or has expired")
    if not user.get("email_verified"):
        user = repo.mark_email_verified(user["id"])
    _start_session(response, user)
    return user


@router.post("/resend-verification", status_code=202)
def resend_verification(payload: ResendVerification, tasks: BackgroundTasks,
                        repo: Repository = Depends(get_repo),
                        mailer: EmailSender = Depends(get_mailer)):
    """Email a new verification link.

    Always gives the same answer, so it does not reveal which emails have an account.
    """
    user = repo.get_user_by_email(payload.email)
    if user is not None and not user.get("email_verified"):
        _queue_verification_email(tasks, mailer, user)
    return {"detail": "If this email has an unverified account, a new link has been sent."}


@router.post("/logout", status_code=204)
def logout():
    """Log out by removing the token cookie."""
    response = Response(status_code=204)
    response.delete_cookie(
        config.AUTH_COOKIE_NAME, path="/", httponly=True, samesite="lax",
        secure=config.AUTH_COOKIE_SECURE)
    return response


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)):
    """Return the logged-in user."""
    return user
