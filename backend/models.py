"""Database tables."""

from datetime import datetime, timezone

from sqlalchemy import (JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String,
                        Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base


def _now():
    # naive UTC — the DateTime columns are naive, so everything compares cleanly
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Coach(Base):
    """One coach, locked to one sport. Their views only ever show that sport."""

    __tablename__ = "coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    sport: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    sessions: Mapped[list["CoachSession"]] = relationship(
        back_populates="coach", cascade="all, delete-orphan"
    )


class CoachSession(Base):
    """A live login. Only the hash of the token is stored."""

    __tablename__ = "coach_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[int] = mapped_column(ForeignKey("coaches.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    coach: Mapped["Coach"] = relationship(back_populates="sessions")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sport: Mapped[str] = mapped_column(String(60), nullable=False, index=True)

    age: Mapped[int | None] = mapped_column(Integer)
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    blood_group: Mapped[str | None] = mapped_column(String(8))
    declared_position: Mapped[str | None] = mapped_column(String(60))
    student_notes: Mapped[str | None] = mapped_column(Text)

    # nutrition inputs
    diet_preference: Mapped[str] = mapped_column(String(20), default="nonveg")
    allergies: Mapped[str | None] = mapped_column(String(255))  # comma-separated keys
    training_hours_per_day: Mapped[float | None] = mapped_column(Float)

    coach_notes: Mapped[str | None] = mapped_column(Text)
    sessions_observed: Mapped[int | None] = mapped_column(Integer)

    # A coach confirming where this student actually plays. It moves them from the
    # Pending tab of the sheet to Verified, and it is the label the trainer learns from.
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    verified_position: Mapped[str | None] = mapped_column(String(60))
    verified_by_id: Mapped[int | None] = mapped_column(ForeignKey("coaches.id", ondelete="SET NULL"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)

    # this student's line in the Google Sheet, recomputed whenever their data changes,
    # so pushing the whole sheet never has to rebuild every report
    sheet_row: Mapped[list | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    verified_by: Mapped["Coach | None"] = relationship()
    # the login that enrolled this student; None for a student a coach added by hand.
    # Deleting the student unlinks the account, so they can enrol again.
    account: Mapped["StudentAccount | None"] = relationship(back_populates="student")

    results: Mapped[list["TestResult"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    videos: Mapped[list["VideoAnalysis"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    match_assignments: Mapped[list["MatchAssignment"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )

    @property
    def verified_by_name(self):
        return self.verified_by.name if self.verified_by else None

    @property
    def email(self):
        return self.account.email if self.account else None


class StudentAccount(Base):
    """A student's sign-in: their university email and a password chosen for Stridian
    (never their university one).

    The password is only ever set together with a code emailed to that address, so an
    account with a password is one whose owner has proved the inbox is theirs. That
    also makes "forgot password" the same flow as signing up.
    """

    __tablename__ = "student_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"), unique=True)
    # the latest emailed code: only its hash, when it went out, and wrong guesses so far
    code_hash: Mapped[str | None] = mapped_column(String(64))
    code_sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    code_attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    student: Mapped["Student | None"] = relationship(back_populates="account")
    sessions: Mapped[list["StudentSession"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class StudentSession(Base):
    """A student's live login. Only the hash of the token is stored."""

    __tablename__ = "student_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("student_accounts.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    account: Mapped["StudentAccount"] = relationship(back_populates="sessions")


class TestResult(Base):
    """One measurement. Kept as history: the newest row per metric_key is the current value."""

    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    metric_key: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    student: Mapped["Student"] = relationship(back_populates="results")


class PositionWeight(Base):
    """Editable weight of one metric inside one position profile, for one sport.

    Seeded from sports_config.py on first run; the app edits rows here, never that file.
    """

    __tablename__ = "position_weights"
    __table_args__ = (UniqueConstraint("sport", "position", "metric_key", name="uq_weight"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sport: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    position: Mapped[str] = mapped_column(String(60), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(60), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class UploadJob:
    """What a video needs on its way from the coach's browser to the worker.

    uploading -> queued -> processing -> done | failed. The file arrives in chunks
    (bytes_received tracks them), the worker claims it by stamping claimed_at, and a
    claim older than the lease is handed back to the queue — that is what lets the
    laptop be shut mid-job and pick up where it left off next time.
    """

    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    bytes_received: Mapped[int] = mapped_column(BigInteger, default=0)
    upload_session: Mapped[str | None] = mapped_column(Text)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    # the video itself is deleted 30 days after upload; every measurement stays
    video_deleted_at: Mapped[datetime | None] = mapped_column(DateTime)


class MatchClip(UploadJob, Base):
    """A multi-player clip run through the YOLO lane. Belongs to a sport, not a student —
    a coach assigns individual tracks to students after looking at the keyframe."""

    __tablename__ = "match_clips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sport: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    coach_id: Mapped[int | None] = mapped_column(ForeignKey("coaches.id", ondelete="SET NULL"))

    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255))
    label: Mapped[str | None] = mapped_column(String(160))
    attack_direction: Mapped[str] = mapped_column(String(8), default="right")

    status: Mapped[str] = mapped_column(String(20), default="uploading", index=True)
    message: Mapped[str | None] = mapped_column(Text)
    duration_sec: Mapped[float | None] = mapped_column(Float)
    fps: Mapped[float | None] = mapped_column(Float)
    frames_sampled: Mapped[int | None] = mapped_column(Integer)

    tracks: Mapped[list | None] = mapped_column(JSON)          # per-player metrics + raw samples
    keyframe_boxes: Mapped[list | None] = mapped_column(JSON)  # clickable boxes on the keyframe
    keyframe_key: Mapped[str | None] = mapped_column(String(255))
    # four image points + the real-world metres they correspond to; set once a coach
    # marks out the pitch, and enough to re-derive every metric without re-reading video
    calibration: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    assignments: Mapped[list["MatchAssignment"]] = relationship(
        back_populates="clip", cascade="all, delete-orphan"
    )


class MatchAssignment(Base):
    """'Track 7 in this clip is Arun.' One row per student identified in one clip."""

    __tablename__ = "match_assignments"
    __table_args__ = (UniqueConstraint("clip_id", "track_id", name="uq_clip_track"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clip_id: Mapped[int] = mapped_column(ForeignKey("match_clips.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSON)   # snapshot of that track's metrics
    context: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    clip: Mapped["MatchClip"] = relationship(back_populates="assignments")
    student: Mapped["Student"] = relationship(back_populates="match_assignments")


class VideoAnalysis(UploadJob, Base):
    """One uploaded clip plus whatever the pose pipeline measured from it."""

    __tablename__ = "video_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)

    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="uploading", index=True)
    message: Mapped[str | None] = mapped_column(Text)

    duration_sec: Mapped[float | None] = mapped_column(Float)
    fps: Mapped[float | None] = mapped_column(Float)
    frames_total: Mapped[int | None] = mapped_column(Integer)
    frames_detected: Mapped[int | None] = mapped_column(Integer)

    metrics: Mapped[dict | None] = mapped_column(JSON)
    thumb_key: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    student: Mapped["Student"] = relationship(back_populates="videos")

    @property
    def has_thumbnail(self):
        # rows from before chunked uploads (no size recorded) kept theirs by filename
        return bool(self.thumb_key) or (self.size_bytes is None and self.status == "done")


class ModelVersion(Base):
    """One snapshot of a sport's position weights — the thing the trainer learns.

    `baseline` rows are weights a person chose (the defaults, a coach's edit, a reset)
    and are what training starts from. `trained` rows are what the trainer produced;
    `deployed` says whether it passed the accuracy check and went live. The newest
    deployed row for a sport is the live model, and rolling back means copying an
    older row forward, so history is never rewritten.
    """

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sport: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)       # baseline | trained
    weights: Mapped[dict] = mapped_column(JSON, nullable=False)
    deployed: Mapped[bool] = mapped_column(Boolean, default=False)
    labels: Mapped[int] = mapped_column(Integer, default=0)            # verified students used
    accuracy: Mapped[float | None] = mapped_column(Float)              # this model, held-out
    live_accuracy: Mapped[float | None] = mapped_column(Float)         # the model it was up against
    signature: Mapped[str | None] = mapped_column(String(40))          # hash of the data it saw
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AppState(Base):
    """Tiny key-value store: worker heartbeat, last sheet sync."""

    __tablename__ = "app_state"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
