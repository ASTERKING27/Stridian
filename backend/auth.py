"""
Coach accounts: PBKDF2 password hashing and bearer-token sessions.

Stdlib only (hashlib + secrets) — no passlib, no JWT library. Tokens are random
256-bit strings; only their SHA-256 is stored, so a database dump does not hand
anyone a live session.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import Coach, CoachSession

ITERATIONS = 240_000
SESSION_DAYS = 30


# ------------------------------ passwords ---------------------------------- #

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"{ITERATIONS}${salt.hex()}${digest.hex()}"


@lru_cache(maxsize=1)
def dummy_hash() -> str:
    """Something to check a wrong email's password against, so it takes as long."""
    return hash_password(secrets.token_hex(16))


def verify_password(password: str, stored: str) -> bool:
    try:
        iterations, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


# ------------------------------- sessions ---------------------------------- #

def _fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(db: Session, coach: Coach) -> str:
    token = secrets.token_urlsafe(32)
    db.add(CoachSession(
        coach_id=coach.id,
        token_hash=_fingerprint(token),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=SESSION_DAYS),
    ))
    db.commit()
    return token


def revoke_token(db: Session, token: str) -> None:
    row = db.scalar(select(CoachSession).where(CoachSession.token_hash == _fingerprint(token)))
    if row:
        db.delete(row)
        db.commit()


def current_coach(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Coach:
    """FastAPI dependency — 401s unless a valid, unexpired bearer token is presented."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in to continue", headers={"WWW-Authenticate": "Bearer"})

    token = authorization.split(" ", 1)[1].strip()
    row = db.scalar(select(CoachSession).where(CoachSession.token_hash == _fingerprint(token)))
    if row is None:
        raise HTTPException(401, "Session not recognised — sign in again")
    if row.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        db.delete(row)
        db.commit()
        raise HTTPException(401, "Session expired — sign in again")

    coach = db.get(Coach, row.coach_id)
    if coach is None:
        raise HTTPException(401, "Account no longer exists")
    return coach


def require_own_sport(coach: Coach, sport_name: str) -> None:
    """A coach only ever touches their own sport."""
    if coach.sport != sport_name:
        raise HTTPException(403, f"You coach {coach.sport}, not {sport_name}")
