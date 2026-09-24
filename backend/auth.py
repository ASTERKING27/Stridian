"""
Coach and student accounts: PBKDF2 password hashing, bearer-token sessions, and the
6-digit codes that prove a student owns their university email.

Stdlib only (hashlib + secrets) — no passlib, no JWT library. Tokens are random
256-bit strings; only their SHA-256 is stored, so a database dump does not hand
anyone a live session. Coach and student tokens live in separate tables, so a
student's token can never open a coach endpoint.
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
from models import Coach, CoachSession, StudentAccount, StudentSession

ITERATIONS = 240_000
SESSION_DAYS = 30

CODE_MINUTES = 15          # an emailed code works for this long
CODE_RESEND_SECONDS = 60   # and a new one can't be sent sooner than this
CODE_TRIES = 5             # wrong guesses before the code is dead
# ponytail: tries are per code, so someone hammering one account gets 5 guesses a minute
# (and floods that inbox, which is capped by Gmail's ~500 emails a day). Add a per-account
# daily cap if that ever matters.


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

def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _issue(db: Session, table, **owner) -> str:
    token = secrets.token_urlsafe(32)
    db.add(table(token_hash=_fingerprint(token),
                 expires_at=_now() + timedelta(days=SESSION_DAYS), **owner))
    db.commit()
    return token


def issue_token(db: Session, coach: Coach) -> str:
    return _issue(db, CoachSession, coach_id=coach.id)


def issue_student_token(db: Session, account: StudentAccount) -> str:
    return _issue(db, StudentSession, account_id=account.id)


def revoke_token(db: Session, token: str, table=CoachSession) -> None:
    row = db.scalar(select(table).where(table.token_hash == _fingerprint(token)))
    if row:
        db.delete(row)
        db.commit()


def _session(db: Session, table, authorization: str | None):
    """The live session row behind a bearer header, or a 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Sign in to continue", headers={"WWW-Authenticate": "Bearer"})

    token = authorization.split(" ", 1)[1].strip()
    row = db.scalar(select(table).where(table.token_hash == _fingerprint(token)))
    if row is None:
        raise HTTPException(401, "Session not recognised — sign in again")
    if row.expires_at < _now():
        db.delete(row)
        db.commit()
        raise HTTPException(401, "Session expired — sign in again")
    return row


def current_coach(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Coach:
    """FastAPI dependency — 401s unless a valid, unexpired coach token is presented."""
    row = _session(db, CoachSession, authorization)
    coach = db.get(Coach, row.coach_id)
    if coach is None:
        raise HTTPException(401, "Account no longer exists")
    return coach


def current_student(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> StudentAccount:
    """FastAPI dependency — the same, for a student's token."""
    row = _session(db, StudentSession, authorization)
    account = db.get(StudentAccount, row.account_id)
    if account is None:
        raise HTTPException(401, "Account no longer exists")
    return account


# ------------------------------ email codes -------------------------------- #

def _code_hash(email: str, code: str) -> str:
    return _fingerprint(f"{email}:{code}")


def code_cooling_down(account: StudentAccount) -> bool:
    """True while the last code is too fresh to send another (stops inbox flooding)."""
    sent = account.code_sent_at
    return sent is not None and (_now() - sent).total_seconds() < CODE_RESEND_SECONDS


def new_code(account: StudentAccount) -> str:
    """Make a fresh 6-digit code for this account (caller commits once it is sent).
    Any earlier code stops working."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    account.code_hash = _code_hash(account.email, code)
    account.code_sent_at = _now()
    account.code_attempts = 0
    return code


def use_code(account: StudentAccount, code: str) -> bool:
    """Check a typed code (caller commits). A right code is used up; wrong guesses count
    towards CODE_TRIES, after which even the right code is refused."""
    if (not account.code_hash or account.code_sent_at is None
            or (_now() - account.code_sent_at).total_seconds() > CODE_MINUTES * 60
            or (account.code_attempts or 0) >= CODE_TRIES):
        return False
    if hmac.compare_digest(account.code_hash, _code_hash(account.email, code)):
        account.code_hash = None
        return True
    account.code_attempts = (account.code_attempts or 0) + 1
    return False


def require_own_sport(coach: Coach, sport_name: str) -> None:
    """A coach only ever touches their own sport."""
    if coach.sport != sport_name:
        raise HTTPException(403, f"You coach {coach.sport}, not {sport_name}")
