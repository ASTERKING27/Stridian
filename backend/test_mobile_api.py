"""
The API the phone app added: run with  python test_mobile_api.py  (no server needed).

It uses a throwaway SQLite file and upload folder, and never sends a real notification.
"""

import os
import re
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

TMP = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = f"sqlite:///{TMP / 'test.db'}"
os.environ["UPLOAD_DIR"] = str(TMP / "uploads")
os.environ["CRON_SECRET"] = "s3cret"
for key in ("STORAGE", "COACH_SIGNUP_CODE", "ADMIN_EMAILS", "SMTP_USER", "VERCEL"):
    os.environ.pop(key, None)

from fastapi.testclient import TestClient  # noqa: E402

import coach as second_coach  # noqa: E402
import main  # noqa: E402
import push  # noqa: E402
from schemas import _D, _P  # noqa: E402

SENT = []
push._send = lambda db, rows, title, body, data: SENT.append((title, [r.token for r in rows]))


def aadhaar(base11):
    inv, c = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9], 0
    for i, ch in enumerate(reversed(base11)):
        c = _D[c][_P[(i + 1) % 8][int(ch)]]
    return base11 + str(inv[c])


def ok(r, code=200):
    assert r.status_code == code, (r.request.method, r.request.url, r.status_code, r.text[:300])
    return r.json() if r.content else None


def main_test():
    codes = []
    main.mailer.send_code = lambda to, code: codes.append(code)
    with TestClient(main.app) as c:
        coach = ok(c.post("/api/auth/signup", json={"name": "R. Krishnan", "employee_id": "E1", "phone": "9444012345",
                                                    "email": "coach@x.in", "password": "coachpass1", "sport": "Football"}), 201)
        CH = {"Authorization": f"Bearer {coach['token']}"}
        enrol = ok(c.get("/api/enrol-code", headers=CH))["code"]

        ok(c.post("/api/student/code", json={"email": "a.m@srmist.edu.in"}), 202)
        tok = ok(c.post("/api/student/verify", json={"email": "a.m@srmist.edu.in", "code": codes[-1], "password": "studentpass1"}))["token"]
        SH = {"Authorization": f"Bearer {tok}"}
        ok(c.post("/api/push/token", headers=CH, json={"token": "ExponentPushToken[coach]", "prefs": {"coach": True}}), 204)
        me = ok(c.post("/api/student/enrol", headers=SH, json={
            "enrol_code": enrol, "sport": "Football", "name": "Aarav Menon", "ra_number": "RA2211003010214",
            "dob": "2005-03-14", "phone": "9876543210", "father_name": "R", "mother_name": "L",
            "father_phone": "9876500000", "aadhaar": aadhaar("48211234567"), "blood_group": "B+", "category": "M",
            "height_cm": 172, "weight_kg": 66}), 201)
        sid = me["student"]["id"]
        assert ("New in the squad", ["ExponentPushToken[coach]"]) in SENT, SENT

        # notifications: the student's phone, with one kind switched off
        ok(c.post("/api/push/token", headers=SH, json={"token": "ExponentPushToken[student]", "prefs": {"coach": True, "video": False}}), 204)
        ok(c.put(f"/api/students/{sid}/results", headers=CH, json={"results": {"sprint30m": 4.38, "cmj": 36, "agilityTtest": 9.95, "yoyoLevel": 18.9}}))
        ok(c.post(f"/api/students/{sid}/verify", headers=CH, json={"position": "Winger"}))
        assert ("You're verified", ["ExponentPushToken[student]"]) in SENT, SENT

        # the full "why": every measure behind every fit, adding back up to the fit
        report = ok(c.get("/api/student/report", headers=SH))
        winger = next(p for p in report["positions"] if p["position"] == "Winger")
        rows = winger["contributions"]
        assert len(rows) >= 4 and {"key", "weight", "score", "impact"} <= set(rows[0])
        total = sum(r["weight"] for r in rows)
        assert abs(sum(r["score"] * r["weight"] for r in rows) / total - winger["fit"]) < 0.11

        # the focus streak: history, best, and a session the coach logs late
        focus = ok(c.get("/api/student/coach", headers=SH))["focus"]
        assert len(focus["history"]) == 8 and focus["best"] == 0 and focus["restored"] is None
        today = second_coach.today_ist(main.utcnow())
        monday = today - timedelta(days=today.weekday())
        ok(c.post("/api/student/focus/tick", headers=SH))
        days = [d for d in (monday + timedelta(days=i) for i in range(7)) if d < today][:2]
        for d in days:
            ok(c.post(f"/api/students/{sid}/focus/log", headers=CH, json={"day": d.isoformat()}))
        focus = ok(c.get("/api/student/coach", headers=SH))["focus"]
        if len(days) == 2:      # on a Monday or Tuesday there aren't two earlier days this week
            assert focus["complete"] and focus["restored"]["by"] == "R. Krishnan", focus
            assert ("Streak restored", ["ExponentPushToken[student]"]) in SENT
        ok(c.post(f"/api/students/{sid}/focus/log", headers=CH, json={"day": (today + timedelta(days=1)).isoformat()}), 400)

        # a drill clip from the phone: announced, sent in pieces, queued, listed
        clip = b"\0" * (300 * 1024)
        up = ok(c.post("/api/student/videos", headers=SH, json={"filename": "cmj.mp4", "size": len(clip), "label": "Countermovement jump"}), 201)
        first = 256 * 1024
        r = ok(c.put(f"/api/student/videos/{up['id']}/upload", headers={**SH, "X-Chunk-Range": f"bytes 0-{first - 1}/{len(clip)}"},
                     content=clip[:first]))
        assert r == {"received": first, "done": False, "status": "uploading"}, r
        r = ok(c.put(f"/api/student/videos/{up['id']}/upload", headers={**SH, "X-Chunk-Range": f"bytes {first}-{len(clip) - 1}/{len(clip)}"},
                     content=clip[first:]))
        assert r["done"] and r["status"] == "queued", r
        videos = ok(c.get("/api/student/videos", headers=SH))
        assert videos[0]["uploaded_by"] == "student" and videos[0]["has_pose"] is False and videos[0]["label"] == "Countermovement jump"
        ok(c.get(f"/api/student/videos/{up['id']}/pose", headers=SH), 404)
        ok(c.get(f"/api/videos/{up['id']}/pose", headers=CH), 404)
        # once the worker has saved a pose track, both can read it
        with main.SessionLocal() as db:
            v = db.get(main.VideoAnalysis, up["id"])
            v.pose_key = main.storage.save_bytes("video-pose.json", b'{"frames":[]}', "application/json")
            db.commit()
        assert ok(c.get(f"/api/student/videos/{up['id']}/pose", headers=SH)) == {"frames": []}
        assert ok(c.get(f"/api/videos/{up['id']}/pose", headers=CH)) == {"frames": []}
        ok(c.delete(f"/api/student/videos/{up['id']}", headers=SH), 204)

        # the weekly nudge only answers Vercel's cron
        ok(c.get("/api/cron/weekly-nudge"), 401)
        ok(c.get("/api/cron/weekly-nudge", headers={"Authorization": "Bearer s3cret"}))

        # deleting accounts: the password is checked, then the student and their record go
        ok(c.request("DELETE", "/api/student/me", headers=SH, json={"password": "wrong"}), 403)
        ok(c.request("DELETE", "/api/student/me", headers=SH, json={"password": "studentpass1"}), 204)
        ok(c.get("/api/student/me", headers=SH), 401)
        ok(c.get(f"/api/students/{sid}", headers=CH), 404)
        ok(c.request("DELETE", "/api/auth/me", headers=CH, json={"password": "coachpass1"}), 204)
        ok(c.get("/api/auth/me", headers=CH), 401)
        with main.SessionLocal() as db:
            assert not db.scalars(main.select(main.PushToken)).all()
    print("mobile api: ok")


if __name__ == "__main__":
    sys.exit(main_test())
