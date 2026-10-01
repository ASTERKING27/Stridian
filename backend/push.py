"""
Phone notifications through Expo's push service — the app registers an Expo push token
(POST /api/push/token) and this sends to it.

Best-effort like the sheets: a notification that can't go out must never turn a saved
verification into an error page, so `notify` logs and carries on. Tokens Expo reports
as gone (the app was uninstalled) are deleted.

No key is needed to send through Expo's service; on Android the app's build carries the
Firebase setup (see the README, "Phone notifications").
"""

import logging

import requests
from sqlalchemy import select

from models import Coach, PushToken, StudentAccount

log = logging.getLogger("stridian.push")
EXPO_URL = "https://exp.host/--/api/v2/push/send"
BATCH = 100            # Expo takes up to 100 messages a request


def _send(db, rows, title, body, data):
    rows = [r for r in rows if r.token.startswith(("ExponentPushToken[", "ExpoPushToken["))]
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        messages = [{"to": r.token, "title": title, "body": body, "data": data or {}, "sound": "default"}
                    for r in chunk]
        try:
            res = requests.post(EXPO_URL, json=messages, timeout=4,
                                headers={"Accept": "application/json", "Content-Type": "application/json"})
            tickets = (res.json() or {}).get("data") or []
        except Exception:  # noqa: BLE001
            log.warning("push send failed", exc_info=True)
            continue
        for row, ticket in zip(chunk, tickets):
            if (ticket.get("details") or {}).get("error") == "DeviceNotRegistered":
                db.delete(row)
    db.commit()


def notify(db, kind, title, body, *, students=(), coaches=(), data=None):
    """Send to the phones of these StudentAccount ids and Coach ids that have `kind`
    ("video", "coach" or "focus") switched on. Never raises."""
    try:
        q = select(PushToken)
        rows = [r for r in db.scalars(q.where(PushToken.role == "student", PushToken.owner_id.in_(list(students))))] \
            if students else []
        if coaches:
            rows += list(db.scalars(q.where(PushToken.role == "coach", PushToken.owner_id.in_(list(coaches)))))
        rows = [r for r in rows if (r.prefs or {}).get(kind, True)]
        if rows:
            _send(db, rows, title, body, data)
    except Exception:  # noqa: BLE001
        log.warning("push notify failed", exc_info=True)


def student_account_ids(db, student):
    """The login(s) behind a student record — none for someone an admin added by hand."""
    return [a.id for a in db.scalars(select(StudentAccount).where(StudentAccount.student_id == student.id))]


def sport_coach_ids(db, sport):
    return list(db.scalars(select(Coach.id).where(Coach.sport == sport)))
