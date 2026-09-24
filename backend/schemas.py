"""Request / response shapes. Pydantic validates these before anything touches the DB."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DietPreference = Literal["vegan", "veg", "egg", "nonveg"]

# The email is only a login identifier here, so a shape check beats pulling in
# email-validator for RFC-correctness nobody needs.
Email = Field(min_length=5, max_length=180, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------- coaches --------------------------------- #

class CoachSignup(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Email
    password: str = Field(min_length=8, max_length=128)
    sport: str
    # required only when the server has COACH_SIGNUP_CODE set — on the public internet
    # it should be, or anyone could make a coach account and read a squad's details
    signup_code: str | None = Field(default=None, max_length=120)


class CoachLogin(BaseModel):
    email: str = Email
    password: str


class CoachOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    sport: str


class TokenOut(BaseModel):
    token: str
    coach: CoachOut


# ----------------------------- student accounts ---------------------------- #

class StudentCodeIn(BaseModel):
    email: str = Email


class StudentVerifyIn(BaseModel):
    """The emailed code, plus the Stridian password the student is choosing."""

    email: str = Email
    code: str = Field(pattern=r"^\d{6}$")
    password: str = Field(min_length=8, max_length=128)


class StudentLogin(BaseModel):
    email: str = Email
    password: str = Field(max_length=128)


# -------------------------------- students --------------------------------- #

class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sport: str
    age: int | None = Field(default=None, ge=8, le=60)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=200)
    blood_group: str | None = Field(default=None, max_length=8)
    declared_position: str | None = Field(default=None, max_length=60)
    student_notes: str | None = None
    diet_preference: DietPreference = "nonveg"
    allergies: str | None = Field(default=None, max_length=255)
    training_hours_per_day: float | None = Field(default=None, ge=0, le=8)


class StudentEnrol(StudentCreate):
    """What a signed-in student sends: their details plus their coach's enrolment code."""

    enrol_code: str = Field(min_length=1, max_length=20)


class StudentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    age: int | None = Field(default=None, ge=8, le=60)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=200)
    blood_group: str | None = Field(default=None, max_length=8)
    declared_position: str | None = Field(default=None, max_length=60)
    student_notes: str | None = None
    coach_notes: str | None = None
    sessions_observed: int | None = Field(default=None, ge=0, le=10000)
    diet_preference: DietPreference | None = None
    allergies: str | None = Field(default=None, max_length=255)
    training_hours_per_day: float | None = Field(default=None, ge=0, le=8)


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None = None
    sport: str
    age: int | None
    height_cm: float | None
    weight_kg: float | None
    blood_group: str | None
    declared_position: str | None
    student_notes: str | None
    coach_notes: str | None
    sessions_observed: int | None
    diet_preference: str
    allergies: str | None
    training_hours_per_day: float | None
    status: str
    verified_position: str | None
    verified_by_name: str | None
    verified_at: datetime | None
    created_at: datetime


class VerifyIn(BaseModel):
    position: str = Field(min_length=1, max_length=60)


class StudentListItem(StudentOut):
    has_results: bool = False
    video_count: int = 0


# ---------------------------- results & weights ---------------------------- #

class ResultsIn(BaseModel):
    """Coach entry. Keys are metric keys; a null value is simply skipped."""

    results: dict[str, float | None] = Field(default_factory=dict)
    declared_position: str | None = Field(default=None, max_length=60)
    coach_notes: str | None = None
    sessions_observed: int | None = Field(default=None, ge=0, le=10000)


class WeightsIn(BaseModel):
    """{position: {metric_key: weight}} — partial updates are allowed."""

    weights: dict[str, dict[str, float]]


# ---------------------------------- videos --------------------------------- #

class UploadIn(BaseModel):
    """Announce a video before sending it in chunks."""

    filename: str = Field(min_length=1, max_length=255)
    size: int = Field(gt=0)
    content_type: str | None = Field(default=None, max_length=120)


class MatchUploadIn(UploadIn):
    label: str | None = Field(default=None, max_length=160)
    attack_direction: Literal["left", "right"] = "right"


class MatchAssignIn(BaseModel):
    track_id: int
    student_id: int


class Point(BaseModel):
    x: float
    y: float


class CalibrationIn(BaseModel):
    """Four clicked points and the real-world metres they correspond to."""

    image_points: list[Point] = Field(min_length=4, max_length=4)
    world_points: list[Point] = Field(min_length=4, max_length=4)
    preset: str | None = None
    label: str | None = Field(default=None, max_length=120)


class MatchClipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sport: str
    original_name: str
    label: str | None
    attack_direction: str
    status: str
    message: str | None
    duration_sec: float | None
    fps: float | None
    frames_sampled: int | None
    video_deleted_at: datetime | None
    created_at: datetime


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    original_name: str
    status: str
    message: str | None
    duration_sec: float | None
    fps: float | None
    frames_total: int | None
    frames_detected: int | None
    metrics: dict | None
    has_thumbnail: bool
    video_deleted_at: datetime | None
    created_at: datetime
