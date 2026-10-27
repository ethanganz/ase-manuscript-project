"""Password hashing and login tokens."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

import config

ALGORITHM = "HS256"

# Marks a token as an email-verification link, so it cannot be used as a
# login token (and a login token cannot verify an email).
VERIFY_EMAIL_PURPOSE = "verify_email"

# bcrypt only looks at the first 72 bytes of a password.
MAX_PASSWORD_BYTES = 72

# Checked when the email is unknown, so a failed login takes the same time
# whether or not the account exists.
DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Return True if the password matches the hash."""
    data = password.encode()
    if len(data) > MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(data, password_hash.encode())


def create_token(user_id: str) -> str:
    """Return a signed token that identifies the user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=config.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    """Return the user ID in the token, or None if it is invalid or expired."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    if "purpose" in payload:  # e.g. an email-verification link
        return None
    return payload.get("sub")


def create_email_token(user_id: str, email: str) -> str:
    """Return a signed token for the link in the verification email.

    The email is included so the link stops working if the address changes.
    """
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "email": email, "purpose": VERIFY_EMAIL_PURPOSE,
               "iat": now, "exp": now + timedelta(hours=config.EMAIL_VERIFY_EXPIRE_HOURS)}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITHM)


def decode_email_token(token: str) -> Optional[tuple[str, str]]:
    """Return (user ID, email) from a verification token, or None if invalid or expired."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    if payload.get("purpose") != VERIFY_EMAIL_PURPOSE:
        return None
    return payload.get("sub"), payload.get("email")
