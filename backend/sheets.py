"""
The Google Sheets, all owned by the account that ran setup_google.py (the admin's):

  Squad             Pending and Verified tabs — each student's analysis, one row each
  Student profiles  the university's record of every student
  Achievements      every achievement and whether it has been verified
  Coaches           every coach account

Each is rewritten completely on every change to what it holds.

Each student's row is computed when their data changes and cached on the student
(`sheet_row`), so a push is one query plus two Sheets API calls however big the squad
gets. Every push rewrites both tabs completely, which means a push that fails (Google
down, no network) is simply repaired by the next one — there is no partial state to
reconcile.

Values are written RAW, never USER_ENTERED: a student who types "=IMPORTXML(...)" as
their name gets that text in a cell, not a formula.
"""

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import gapi

SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
TABS = ("Pending", "Verified")

HEADER = [
    "Student ID", "RA number", "Name", "Email", "Sport", "Status",
    "Verified position", "Verified by", "Verified on",
    "Recommended position", "Fit /100", "Confidence", "Coach agrees with system",
    "Tests vs match footage", "Strengths", "Weak links",
    "Age", "Height (cm)", "Weight (kg)", "Blood group", "Position they gave",
    "Diet", "Allergies", "Daily kcal", "Protein (g)", "Carbs (g)", "Fat (g)",
    "Tests recorded", "Match clips", "Drill clips",
    "Student notes", "Coach notes", "Enrolled on", "Row updated",
]


def sheet_id():
    return os.environ.get("GOOGLE_SHEET_ID", "").strip()


def configured():
    return gapi.configured() and bool(sheet_id())


def sheet_url():
    return f"https://docs.google.com/spreadsheets/d/{sheet_id()}" if sheet_id() else None


def _local(dt):
    """Sheet dates in the university's own timezone (the database keeps naive UTC)."""
    if dt is None:
        return ""
    zone = ZoneInfo(os.environ.get("TIMEZONE", "Asia/Kolkata"))
    return dt.replace(tzinfo=timezone.utc).astimezone(zone).strftime("%Y-%m-%d %H:%M")


def _list(items, reverse):
    ranked = sorted(items, key=lambda s: s["score"], reverse=reverse)[:4]
    return ", ".join(f"{s['label']} ({s['score']:.0f})" for s in ranked)


def row_for(report: dict, student) -> list:
    """One student as one sheet row, in HEADER order. Pure: report in, cells out."""
    rec = report.get("recommended") or {}
    diet = report.get("diet") or {}
    targets = diet.get("targets") or {}
    verified = student.status == "verified"

    agrees = ""
    if verified and rec:
        agrees = "Yes" if rec.get("position") == student.verified_position else "No"

    row = [
        student.id, student.ra_number or "", student.name, student.email or "", student.sport,
        "Verified" if verified else "Pending",
        student.verified_position or "", student.verified_by_name or "",
        _local(student.verified_at),
        rec.get("position", ""), rec.get("fit", ""), rec.get("confidence", ""), agrees,
        (report.get("reconciliation") or {}).get("agreement", ""),
        _list(report.get("strengths", []), reverse=True),
        _list(report.get("weaknesses", []), reverse=False),
        student.age_now or "", student.height_cm or "", student.weight_kg or "",
        student.blood_group or "", student.declared_position or "",
        diet.get("dietPreference", ""), ", ".join(diet.get("allergies", [])),
        targets.get("kcal", ""), targets.get("protein_g", ""),
        targets.get("carbs_g", ""), targets.get("fat_g", ""),
        sum(1 for m in report.get("metrics", [])
            if m["source"] == "test" and m["value"] is not None),
        len(report.get("matchClips", [])),
        sum(1 for v in report.get("videos", []) if v["status"] == "done"),
        student.student_notes or "", student.coach_notes or "",
        _local(student.created_at),
        _local(datetime.now(timezone.utc).replace(tzinfo=None)),
    ]
    assert len(row) == len(HEADER)
    return row


def tabs_for(students) -> dict:
    """{tab name: rows} — newest enrolment first on Pending, newest verification first
    on Verified. Students whose row hasn't been computed yet are left out until it is."""
    pending = [s for s in students if s.status != "verified" and s.sheet_row]
    verified = [s for s in students if s.status == "verified" and s.sheet_row]
    pending.sort(key=lambda s: s.created_at, reverse=True)
    verified.sort(key=lambda s: s.verified_at or s.created_at, reverse=True)
    return {"Pending": [s.sheet_row for s in pending],
            "Verified": [s.sheet_row for s in verified]}


def write(spreadsheet: str, tabs: dict) -> None:
    """Replace each tab's contents with {tab: rows} (header row included). Raises."""
    http = gapi.session()
    # write first, then clear whatever is left below — the sheet is never blank
    r = http.post(f"{SHEETS}/{spreadsheet}/values:batchUpdate", timeout=30, json={
        "valueInputOption": "RAW",
        "data": [{"range": f"{tab}!A1", "values": rows} for tab, rows in tabs.items()],
    })
    r.raise_for_status()
    r = http.post(f"{SHEETS}/{spreadsheet}/values:batchClear", timeout=30, json={
        "ranges": [f"{tab}!A{len(rows) + 1}:AZ" for tab, rows in tabs.items()],
    })
    r.raise_for_status()


def push(students) -> dict:
    """Rewrite both tabs. Returns a status dict; never raises (a sheet is never worth
    failing a coach's save over)."""
    if not configured():
        return {"ok": False, "error": "Google Sheet not set up"}
    tabs = tabs_for(students)
    try:
        write(sheet_id(), {tab: [HEADER] + rows for tab, rows in tabs.items()})
    except Exception as exc:  # noqa: BLE001 — reported on the AI Training page instead
        return {"ok": False, "error": str(exc)[:300]}
    return {"ok": True, "pending": len(tabs["Pending"]), "verified": len(tabs["Verified"])}


# --------------------------------------------------------------------------- #
# People: student profiles, achievements, coaches
# --------------------------------------------------------------------------- #

LEVEL_WORDS = {"university": "University", "zonal": "Zonal", "state": "State",
               "national": "National", "international": "International"}

PROFILE_HEADER = [
    "Student ID", "RA number", "Name", "Sport", "University email", "Personal email",
    "Mobile", "Date of birth", "Age", "Blood group", "Father's name", "Father's mobile",
    "Mother's name", "Mother's mobile", "Aadhaar", "Passport", "Identification mark",
    "Highest level (student says)", "Level details", "Highest verified level",
    "Verified achievements", "Height (cm)", "Weight (kg)", "Status", "Enrolled on",
]

ACHIEVEMENT_HEADER = [
    "Achievement ID", "Student ID", "RA number", "Student", "Sport", "Level", "Event",
    "Year", "Result", "Details", "Status", "Checked by", "Checked on", "Note",
    "Name on certificate (AI)", "Uploaded on",
]

COACH_HEADER = ["Coach ID", "Name", "Email", "Employee ID", "Mobile", "Designation",
                "Sport", "Admin", "Joined on"]

# key: (spreadsheet title, tab, header)
PEOPLE = {
    "profiles": ("Stridian — Student profiles", "Profiles", PROFILE_HEADER),
    "achievements": ("Stridian — Achievements", "Achievements", ACHIEVEMENT_HEADER),
    "coaches": ("Stridian — Coaches", "Coaches", COACH_HEADER),
}


def profile_row(s) -> list:
    return [
        s.id, s.ra_number or "", s.name, s.sport, s.email or "", s.personal_email or "",
        s.phone or "", s.dob.isoformat() if s.dob else "", s.age_now or "", s.blood_group or "",
        s.father_name or "", s.father_phone or "", s.mother_name or "", s.mother_phone or "",
        s.aadhaar or "", s.passport or "", s.id_mark or "",
        LEVEL_WORDS.get(s.highest_level, ""), s.highest_level_details or "",
        LEVEL_WORDS.get(s.top_verified_level, ""), len(s.verified_achievements),
        s.height_cm or "", s.weight_kg or "",
        "Verified" if s.status == "verified" else "Pending", _local(s.created_at),
    ]


def achievement_row(a) -> list:
    s = a.student
    return [
        a.id, s.id, s.ra_number or "", s.name, s.sport, LEVEL_WORDS.get(a.level, ""),
        a.title or "", a.year or "", a.result or "", a.details or "", a.status.capitalize(),
        a.reviewed_by_name or "", _local(a.reviewed_at), a.review_note or "",
        (a.ai_read or {}).get("name_on_certificate") or "", _local(a.created_at),
    ]


def coach_row(c) -> list:
    return [c.id, c.name, c.email, c.employee_id or "", c.phone or "", c.designation or "",
            c.sport, "Yes" if c.is_admin else "", _local(c.created_at)]


def create(title: str, tab: str, header: list) -> str:
    """Make a new spreadsheet in the admin's Drive and return its id."""
    r = gapi.session().post(SHEETS, timeout=30, json={
        "properties": {"title": title},
        "sheets": [{"properties": {"title": tab, "gridProperties": {"frozenRowCount": 1}}}],
    })
    r.raise_for_status()
    return r.json()["spreadsheetId"]
