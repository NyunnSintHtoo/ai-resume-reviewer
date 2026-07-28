"""Authentication.

Two identity mechanisms:
- JWT bearer tokens (register/login) with stdlib PBKDF2 password hashing.
- Anonymous per-browser identities via the `X-Anon-Id` header: the frontend
  generates a UUID once, stores it in localStorage, and sends it on every
  request; the backend get-or-creates a lightweight user for it. This powers
  the frictionless demo flow — no login required in the UI, while the full
  JWT flow stays available through the API.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User

_ITERATIONS = 200_000
_bearer = HTTPBearer(auto_error=False)
_ANON_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc
    return payload["sub"]


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Strict JWT-only dependency (used by /auth/me)."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = decode_token(credentials.credentials)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    anon_id: str | None = Header(default=None, alias="X-Anon-Id"),
    db: Session = Depends(get_db),
) -> User:
    """Identity for reviews/history: a JWT user when a valid bearer token is
    present, otherwise a get-or-created anonymous user keyed by X-Anon-Id."""
    if credentials is not None:
        user_id = decode_token(credentials.credentials)
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user

    if anon_id and _ANON_ID_RE.fullmatch(anon_id):
        user = db.scalar(select(User).where(User.anon_id == anon_id))
        if user is None:
            user = User(anon_id=anon_id)
            db.add(user)
            db.commit()
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Provide a bearer token or an X-Anon-Id header (8-64 chars of A-Za-z0-9_-)",
    )
