"""Password hashing and login tokens."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

import config

ALGORITHM = "HS256"

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
    now = datetime.now(UTC)
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
    return payload.get("sub")
