"""
The squad Google Sheet: a Pending tab and a Verified tab, rewritten on every change.

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
    "Student ID", "Name", "Email", "Sport", "Status",
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
        student.id, student.name, student.email or "", student.sport,
        "Verified" if verified else "Pending",
        student.verified_position or "", student.verified_by_name or "",
        _local(student.verified_at),
        rec.get("position", ""), rec.get("fit", ""), rec.get("confidence", ""), agrees,
        (report.get("reconciliation") or {}).get("agreement", ""),
        _list(report.get("strengths", []), reverse=True),
        _list(report.get("weaknesses", []), reverse=False),
        student.age or "", student.height_cm or "", student.weight_kg or "",
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


def push(students) -> dict:
    """Rewrite both tabs. Returns a status dict; never raises (a sheet is never worth
    failing a coach's save over)."""
    if not configured():
        return {"ok": False, "error": "Google Sheet not set up"}
    tabs = tabs_for(students)
    try:
        http = gapi.session()
        # write first, then clear whatever is left below — the sheet is never blank
        r = http.post(f"{SHEETS}/{sheet_id()}/values:batchUpdate", timeout=30, json={
            "valueInputOption": "RAW",
            "data": [{"range": f"{tab}!A1", "values": [HEADER] + rows} for tab, rows in tabs.items()],
        })
        r.raise_for_status()
        r = http.post(f"{SHEETS}/{sheet_id()}/values:batchClear", timeout=30, json={
            "ranges": [f"{tab}!A{len(rows) + 2}:AZ" for tab, rows in tabs.items()],
        })
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — reported on the AI Training page instead
        return {"ok": False, "error": str(exc)[:300]}
    return {"ok": True, "pending": len(tabs["Pending"]), "verified": len(tabs["Verified"])}
