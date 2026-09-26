"""Request / response shapes. Pydantic validates these before anything touches the DB."""

import re
from datetime import date, datetime
from typing import Literal

from pydantic import (AliasChoices, BaseModel, ConfigDict, Field, field_validator,
                      model_validator)

from models import years_since

DietPreference = Literal["vegan", "veg", "egg", "nonveg"]
BloodGroup = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
Level = Literal["university", "zonal", "state", "national", "international"]

# The email is only a login identifier here, so a shape check beats pulling in
# email-validator for RFC-correctness nobody needs.
EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
Email = Field(min_length=5, max_length=180, pattern=EMAIL_RE)


# ------------------------------ field checks ------------------------------- #

def indian_mobile(value: str | None) -> str | None:
    """'+91 98765-43210', '098765 43210' and '9876543210' all become '9876543210'."""
    if value is None:
        return None
    digits = re.sub(r"\D", "", value)
    if digits.startswith("00"):                              # 0091 …
        digits = digits[2:]
    if len(digits) in (12, 13) and digits.startswith("91"):  # 91 …, and +91 0 …
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise ValueError("should be a 10-digit Indian mobile number")
    return digits


_D = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
      [2, 3, 4, 0, 1, 7, 8, 9, 5, 6], [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
      [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
      [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
      [8, 7, 6, 5, 9, 3, 2, 1, 0, 4], [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_P = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
      [5, 8, 0, 3, 7, 9, 6, 1, 4, 2], [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
      [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
      [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]


def verhoeff_ok(number: str) -> bool:
    """The check digit every Aadhaar number carries — catches any single mistyped digit
    and any two swapped neighbours."""
    check = 0
    for i, ch in enumerate(reversed(number)):
        check = _D[check][_P[i % 8][int(ch)]]
    return check == 0


class Form(BaseModel):
    """A form field left empty arrives as "" — treat it as not given."""

    @model_validator(mode="before")
    @classmethod
    def _blank_is_none(cls, data):
        if isinstance(data, dict):
            return {k: None if isinstance(v, str) and not v.strip() else v for k, v in data.items()}
        return data


# --------------------------------- coaches --------------------------------- #

class CoachDetails(Form):
    """A coach's own details — all optional here, so the same shape serves edits."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    employee_id: str | None = Field(default=None, min_length=1, max_length=40)
    phone: str | None = None
    designation: str | None = Field(default=None, max_length=80)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        return indian_mobile(v)

    @field_validator("name", "employee_id", "designation")
    @classmethod
    def _trim(cls, v):
        return v.strip() if v else v


class CoachSignup(CoachDetails):
    name: str = Field(min_length=1, max_length=120)
    employee_id: str = Field(min_length=1, max_length=40)
    phone: str
    email: str = Email
    password: str = Field(min_length=8, max_length=128)
    sport: str
    # required only when the server has COACH_SIGNUP_CODE set — on the public internet
    # it should be, or anyone could make a coach account and read a squad's details
    signup_code: str | None = Field(default=None, max_length=120)
    # an ADMIN_EMAILS address also needs the code emailed to it (see main.prove_admin_email)
    email_code: str | None = Field(default=None, max_length=12)


class CoachLogin(BaseModel):
    email: str = Email
    password: str


class CoachOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    sport: str
    employee_id: str | None = None
    phone: str | None = None
    designation: str | None = None
    is_admin: bool = False


class SportIn(BaseModel):
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

class Profile(Form):
    """The university's record of a student, checked field by field. Everything is
    optional here; the forms that need a field make it required."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    ra_number: str | None = None
    dob: date | None = None
    phone: str | None = None
    personal_email: str | None = Field(default=None, max_length=180, pattern=EMAIL_RE)
    father_name: str | None = Field(default=None, max_length=120)
    father_phone: str | None = None
    mother_name: str | None = Field(default=None, max_length=120)
    mother_phone: str | None = None
    aadhaar: str | None = None
    passport: str | None = None
    id_mark: str | None = Field(default=None, max_length=200)
    blood_group: BloodGroup | None = None
    highest_level: Level | None = None
    highest_level_details: str | None = Field(default=None, max_length=2000)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=200)
    declared_position: str | None = Field(default=None, max_length=60)
    student_notes: str | None = Field(default=None, max_length=4000)
    diet_preference: DietPreference | None = None
    allergies: str | None = Field(default=None, max_length=255)
    training_hours_per_day: float | None = Field(default=None, ge=0, le=8)

    @field_validator("name", "father_name", "mother_name", "id_mark")
    @classmethod
    def _trim(cls, v):
        return " ".join(v.split()) if v else v

    @field_validator("personal_email")
    @classmethod
    def _lower(cls, v):
        return v.strip().lower() if v else v

    @field_validator("ra_number")
    @classmethod
    def _ra(cls, v):
        if v is None:
            return v
        v = re.sub(r"\s", "", v).upper()
        if not re.fullmatch(r"RA\d{13}", v):
            raise ValueError("should be RA followed by 13 digits, like RA2311003010123")
        return v

    @field_validator("dob")
    @classmethod
    def _dob(cls, v):
        if v is not None and not 14 <= (years_since(v) or 0) <= 60:
            raise ValueError("gives an age outside 14–60 — check the year")
        return v

    @field_validator("phone", "father_phone", "mother_phone")
    @classmethod
    def _phone(cls, v):
        return indian_mobile(v)

    @field_validator("aadhaar")
    @classmethod
    def _aadhaar(cls, v):
        if v is None:
            return v
        v = re.sub(r"[\s-]", "", v)
        if not re.fullmatch(r"[2-9]\d{11}", v) or not verhoeff_ok(v):
            raise ValueError("isn't a valid Aadhaar number — check the 12 digits")
        return v

    @field_validator("passport")
    @classmethod
    def _passport(cls, v):
        if v is None:
            return v
        v = re.sub(r"\s", "", v).upper()
        if not re.fullmatch(r"[A-Z]\d{7}", v):
            raise ValueError("should be a letter and 7 digits, like K1234567")
        return v


# what only an admin may change about a student once they exist
ADMIN_ONLY = {"sport", "ra_number", "dob", "phone", "personal_email", "father_name",
              "father_phone", "mother_name", "mother_phone", "aadhaar", "passport", "id_mark",
              "highest_level", "highest_level_details"}
# what a student can fill in once but never change (an admin can)
STUDENT_ONCE = {"ra_number", "dob"}
# what can't be emptied once given
REQUIRED = {"name", "phone", "father_name", "mother_name", "aadhaar", "blood_group"}


class StudentCreate(Profile):
    """An admin adding a student by hand: everything but the name and sport can wait."""

    name: str = Field(min_length=1, max_length=120)
    sport: str
    age: int | None = Field(default=None, ge=8, le=60)
    diet_preference: DietPreference = "nonveg"


class StudentEnrol(StudentCreate):
    """What a signed-in student sends: their full details plus their coach's enrolment code."""

    enrol_code: str = Field(min_length=1, max_length=20)
    ra_number: str
    dob: date
    phone: str
    father_name: str = Field(min_length=1, max_length=120)
    mother_name: str = Field(min_length=1, max_length=120)
    aadhaar: str
    blood_group: BloodGroup

    @model_validator(mode="after")
    def _a_parent_phone(self):
        if not (self.father_phone or self.mother_phone):
            raise ValueError("Give at least one parent's mobile number")
        return self


class StudentSelfUpdate(Profile):
    """A student editing their own details. Their sport isn't in here, and their RA number
    and date of birth can only be filled in if missing — an admin changes those."""

    @model_validator(mode="after")
    def _keep_required(self):
        emptied = sorted(f for f in REQUIRED & self.model_fields_set if getattr(self, f) is None)
        if emptied:
            raise ValueError(f"These can't be left empty: {', '.join(emptied)}")
        return self

    @model_validator(mode="before")
    @classmethod
    def _no_sport(cls, data):
        if isinstance(data, dict) and "sport" in data:
            raise ValueError("Only an admin can move you to another sport")
        return data


class StudentUpdate(StudentSelfUpdate):
    """A coach (their own sport's usual fields) or an admin (everything)."""

    sport: str | None = None
    age: int | None = Field(default=None, ge=8, le=60)
    coach_notes: str | None = None
    sessions_observed: int | None = Field(default=None, ge=0, le=10000)

    @model_validator(mode="before")
    @classmethod
    def _no_sport(cls, data):
        return data     # who may change what is decided in the endpoint


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None = None
    sport: str
    # worked out from the date of birth when there is one
    age: int | None = Field(default=None, validation_alias=AliasChoices("age_now", "age"))
    ra_number: str | None = None
    dob: date | None = None
    phone: str | None = None
    personal_email: str | None = None
    father_name: str | None = None
    father_phone: str | None = None
    mother_name: str | None = None
    mother_phone: str | None = None
    aadhaar: str | None = None
    passport: str | None = None
    id_mark: str | None = None
    highest_level: str | None = None
    highest_level_details: str | None = None
    photo_version: str | None = None
    top_verified_level: str | None = None
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
    achievements_verified: int = 0
    achievements_pending: int = 0


# ------------------------------- achievements ------------------------------ #

class AchievementIn(Form):
    """A student filling in (or correcting) what the AI read off a certificate."""

    level: Level | None = None
    title: str | None = Field(default=None, max_length=200)
    year: int | None = Field(default=None, ge=1990, le=2100)
    result: str | None = Field(default=None, max_length=80)
    details: str | None = Field(default=None, max_length=2000)
    submit: bool = False     # true sends it to the coach


class ReviewIn(Form):
    decision: Literal["verified", "rejected"]
    note: str | None = Field(default=None, max_length=500)
    # the version the coach was looking at; if the student has changed it since, the
    # verdict is refused rather than applied to details the coach never saw
    version: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def _say_why(self):
        if self.decision == "rejected" and not self.note:
            raise ValueError("Say why it's rejected, so the student can fix it")
        return self


class AchievementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    level: str | None
    title: str | None
    year: int | None
    result: str | None
    details: str | None
    cert_name: str | None
    cert_mime: str | None
    status: str
    review_note: str | None
    reviewed_by_name: str | None
    reviewed_at: datetime | None
    ai_read: dict | None
    version: str
    created_at: datetime


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
