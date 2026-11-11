"""
Reads photos and PDFs of documents (certificates now, match cards later) with an AI model
and hands back the fields it found, so nobody retypes what is already on paper.

Only one provider today: Google's Gemini API, on its free tier (GEMINI_API_KEY). Every
caller goes through read(), so moving to a paid plan, AWS or a university server later
means changing this file alone.

Nothing here is ever fatal. No key, no network, a quota hit or an answer that isn't JSON
all come back as None, and the person simply fills the fields in by hand.
"""

import base64
import json
import logging
import os

import requests

log = logging.getLogger("stridian.docreader")

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# tried in order: the second takes over when the first is out of free quota
DEFAULT_MODELS = "gemini-3.5-flash,gemini-3.5-flash-lite"

READABLE = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


def configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def _models():
    return [m.strip() for m in os.environ.get("GEMINI_MODEL", DEFAULT_MODELS).split(",") if m.strip()]


def read(data: bytes, mime: str, prompt: str, schema: dict, timeout: int = 40) -> dict | None:
    """Ask the model to read one document into `schema` (Gemini's OpenAPI subset)."""
    if not configured() or mime not in READABLE:
        return None
    body = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}},
            {"text": prompt},
        ]}],
        "generationConfig": {"response_mime_type": "application/json",
                             "response_schema": schema, "temperature": 0},
    }
    headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"].strip()}
    for model in _models():
        try:
            r = requests.post(API.format(model=model), json=body, headers=headers, timeout=timeout)
            if r.status_code in (404, 429) or r.status_code >= 500:
                log.warning("document AI %s answered %s; trying the next model", model, r.status_code)
                continue
            r.raise_for_status()
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            found = json.loads(text)
            return found if isinstance(found, dict) else None
        except Exception:  # noqa: BLE001 — see the module docstring
            log.warning("document AI %s failed", model, exc_info=True)
            return None
    return None


# --------------------------------------------------------------------------- #
# Certificates
# --------------------------------------------------------------------------- #

LEVELS = ["university", "zonal", "state", "national", "international"]

CERTIFICATE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "is_certificate": {"type": "BOOLEAN",
                           "description": "true if this is a sports certificate, medal "
                                          "record or similar proof of taking part"},
        "name_on_certificate": {"type": "STRING", "nullable": True},
        "title": {"type": "STRING", "nullable": True,
                  "description": "the event or tournament, e.g. 'South Zone Inter-University "
                                 "Volleyball Championship 2024'"},
        "sport": {"type": "STRING", "nullable": True},
        "level": {"type": "STRING", "nullable": True, "enum": LEVELS},
        "year": {"type": "INTEGER", "nullable": True},
        "result": {"type": "STRING", "nullable": True,
                   "description": "position or medal, e.g. 'Gold', 'Runners-up', "
                                  "'Participation'"},
        "issued_by": {"type": "STRING", "nullable": True},
        "details": {"type": "STRING", "nullable": True,
                    "description": "one short sentence with anything else useful: venue, "
                                   "dates, age category, team or individual"},
    },
    "required": ["is_certificate", "name_on_certificate", "title", "sport", "level", "year",
                 "result", "issued_by", "details"],
}

CERTIFICATE_PROMPT = """This is a document an Indian university student uploaded as proof of a
sports achievement. Read it and fill in the fields. Use null for anything not written on it —
never guess a name, year or result.

level must be one of:
- university: inter-college or intra-university events
- zonal: inter-university zone championships (e.g. AIU South Zone) or district-level events
- state: state championships or state-level representation
- national: national championships, Khelo India, All India Inter-University
- international: any event with other countries taking part"""


def read_certificate(data: bytes, mime: str) -> dict | None:
    found = read(data, mime, CERTIFICATE_PROMPT, CERTIFICATE_SCHEMA)
    if found and found.get("level") not in LEVELS:
        found["level"] = None
    return found
