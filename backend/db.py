"""Database setup. Postgres (Neon) when DATABASE_URL is set, a local SQLite file otherwise.

The web server on Vercel and the worker on the lab computer both point DATABASE_URL at
the same Neon database, which is how they share one queue and one set of students
without talking to each other directly.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent

try:  # on a laptop the settings live in ../.env; on Vercel they come from the dashboard
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR.parent / ".env")
except ImportError:
    pass


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        if os.environ.get("VERCEL"):
            # a serverless disk is wiped between requests, so SQLite there would
            # silently lose every student — refuse instead
            raise RuntimeError("DATABASE_URL is not set. Add your Neon connection string "
                               "in Vercel -> Project -> Settings -> Environment Variables.")
        # the file keeps its original name so an existing local database carries on
        return f"sqlite:///{BASE_DIR / 'ppanalyzer.db'}"
    # Neon hands out postgres:// or postgresql:// URLs; point SQLAlchemy at psycopg 3
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


SQLALCHEMY_URL = database_url()

if SQLALCHEMY_URL.startswith("sqlite"):
    # check_same_thread=False because FastAPI serves requests from a threadpool
    engine = create_engine(SQLALCHEMY_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        SQLALCHEMY_URL,
        pool_pre_ping=True,   # Neon suspends when idle; don't hand out a dead connection
        pool_recycle=300,
        # Neon's pooled endpoint is PgBouncer in transaction mode, which server-side
        # prepared statements don't survive
        connect_args={"prepare_threshold": None},
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency - yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
