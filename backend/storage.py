"""
Where uploaded videos and their preview images live.

STORAGE=drive  a folder in the Google Drive of the account that ran setup_google.py.
               Needed once the website runs on Vercel and the worker on another computer.
otherwise      backend/uploads on this computer — fine when the website and the worker
               run on the same machine.

Videos arrive in chunks because a Vercel function accepts at most 4.5 MB per request.
Every call takes and returns plain strings, so the database only ever stores a key.
"""

import os
import shutil
import uuid
from pathlib import Path

import gapi

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR") or Path(__file__).resolve().parent / "uploads")

GRANULE = 256 * 1024          # Drive needs every chunk but the last to be a multiple of this
CHUNK = 16 * GRANULE          # 4 MiB: under Vercel's 4.5 MB request cap

DRIVE = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"


class StorageError(Exception):
    pass


def backend() -> str:
    return "drive" if os.environ.get("STORAGE", "").strip().lower() == "drive" else "local"


def _local(key: str) -> Path:
    # keys are generated below, never typed by a user — but refuse path tricks anyway
    if not key or Path(key).name != key:
        raise StorageError(f"Bad storage key: {key!r}")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR / key


def _ok(response, what):
    if response.status_code >= 400:
        raise StorageError(f"Google Drive {what} failed: {response.status_code} {response.text[:200]}")
    return response


def _received(response) -> int:
    """Drive answers 308 with `Range: bytes=0-N` — the bytes it has kept so far."""
    header = response.headers.get("Range", "")
    return int(header.rsplit("-", 1)[1]) + 1 if "-" in header else 0


# --------------------------------------------------------------------------- #
# Chunked upload
# --------------------------------------------------------------------------- #

def begin(filename: str, size: int, mime: str = "application/octet-stream"):
    """Open an upload. Returns (session, key): the handle to send chunks to, and the
    file's key if it is already known (locally it is; Drive only names it at the end).
    """
    if backend() == "local":
        key = uuid.uuid4().hex + Path(filename).suffix.lower()
        _local(key).write_bytes(b"")
        return key, key

    meta = {"name": filename}
    if os.environ.get("GOOGLE_DRIVE_FOLDER_ID"):
        meta["parents"] = [os.environ["GOOGLE_DRIVE_FOLDER_ID"]]
    r = _ok(gapi.session().post(
        f"{DRIVE_UPLOAD}?uploadType=resumable&supportsAllDrives=true", json=meta,
        headers={"X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(size)},
        timeout=30), "upload start")
    return r.headers["Location"], None


def put_chunk(session: str, start: int, data: bytes, total: int):
    """Store one chunk. Returns (bytes kept so far, final key or None until complete).

    Always trust the returned count over what was sent: Drive may keep less than a
    full chunk, and the caller resumes from whatever it reports.
    """
    if backend() == "local":
        path = _local(session)
        have = path.stat().st_size
        if start == have:
            with path.open("ab") as out:
                out.write(data)
            have += len(data)
        return have, (session if have >= total else None)

    http = gapi.session()
    end = start + len(data) - 1
    r = http.put(session, data=data, timeout=120,
                 headers={"Content-Range": f"bytes {start}-{end}/{total}"})
    if r.status_code in (400, 416) or r.status_code >= 500:
        # our idea of the offset drifted (a lost response, a retry): ask Drive where it is
        r = http.put(session, data=b"", timeout=30, headers={"Content-Range": f"bytes */{total}"})
    if r.status_code in (200, 201):
        return total, r.json()["id"]
    if r.status_code == 308:
        return _received(r), None
    _ok(r, "chunk upload")
    raise StorageError(f"Unexpected answer from Google Drive: {r.status_code}")


# --------------------------------------------------------------------------- #
# Whole files
# --------------------------------------------------------------------------- #

def save_bytes(filename: str, data: bytes, mime: str = "image/jpeg") -> str:
    """Store a small file (a thumbnail, a keyframe) in one go and return its key."""
    session, _key = begin(filename, len(data), mime)
    _have, key = put_chunk(session, 0, data, len(data))
    if key is None:
        raise StorageError("Upload did not complete")
    return key


def read_bytes(key: str) -> bytes:
    if backend() == "local":
        path = _local(key)
        if not path.exists():
            raise FileNotFoundError(key)
        return path.read_bytes()
    r = gapi.session().get(f"{DRIVE}/{key}?alt=media&supportsAllDrives=true", timeout=60)
    if r.status_code == 404:
        raise FileNotFoundError(key)
    return _ok(r, "download").content


def download(key: str, dest: Path) -> None:
    """Copy a stored file to a local path (the worker needs a real file for OpenCV)."""
    if backend() == "local":
        path = _local(key)
        if not path.exists():
            raise FileNotFoundError(key)
        shutil.copyfile(path, dest)
        return
    with gapi.session().get(f"{DRIVE}/{key}?alt=media&supportsAllDrives=true",
                            stream=True, timeout=300) as r:
        if r.status_code == 404:
            raise FileNotFoundError(key)
        _ok(r, "download")
        with open(dest, "wb") as out:
            for block in r.iter_content(1024 * 1024):
                out.write(block)


def delete(key: str | None) -> None:
    """Remove a stored file. Already gone counts as success."""
    if not key:
        return
    if backend() == "local":
        _local(key).unlink(missing_ok=True)
        return
    r = gapi.session().delete(f"{DRIVE}/{key}?supportsAllDrives=true", timeout=30)
    if r.status_code != 404:
        _ok(r, "delete")
