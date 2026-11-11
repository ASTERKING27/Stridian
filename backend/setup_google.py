"""
One-time Google setup. Run on your laptop, from the backend folder:

    python setup_google.py

Before running it, put these two lines (from Google Cloud -> Credentials -> your OAuth
client of type "Desktop app") in the .env file in the project folder:

    GOOGLE_CLIENT_ID=...
    GOOGLE_CLIENT_SECRET=...

It then:
  1. opens your browser so you can sign in with the Google account whose Drive should
     hold the videos (the 5 TB one), and asks for access to files this app creates;
  2. creates a "Stridian videos" folder in that Drive;
  3. writes GOOGLE_REFRESH_TOKEN, GOOGLE_DRIVE_FOLDER_ID and STORAGE=drive into .env and
     prints them, so you can paste the same into Vercel.

The spreadsheets (a squad file per sport, student profiles, achievements, coaches) are
made by the app itself, in the same Drive, the first time there is something to put in
them. Running this again reuses the folder already recorded in .env.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import AuthorizedSession
from google_auth_oauthlib.flow import InstalledAppFlow

from gapi import SCOPES, TOKEN_URI

ENV = Path(__file__).resolve().parent.parent / ".env"


def set_env(key, value):
    """Add or replace one KEY=value line in .env, leaving every other line alone."""
    lines = ENV.read_text(encoding="utf-8-sig").splitlines() if ENV.exists() else []
    lines = [ln for ln in lines if not ln.startswith(f"{key}=")] + [f"{key}={value}"]
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key] = value


def main():
    load_dotenv(ENV)
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit(f"Put GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in {ENV} first.")

    flow = InstalledAppFlow.from_client_config(
        {"installed": {"client_id": client_id, "client_secret": client_secret,
                       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                       "token_uri": TOKEN_URI, "redirect_uris": ["http://localhost"]}},
        SCOPES)
    # prompt=consent makes Google hand out a refresh token even on a second run
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    if not creds.refresh_token:
        sys.exit("Google did not return a refresh token. Run this again.")
    set_env("GOOGLE_REFRESH_TOKEN", creds.refresh_token)
    http = AuthorizedSession(creds)

    if not os.environ.get("GOOGLE_DRIVE_FOLDER_ID"):
        r = http.post("https://www.googleapis.com/drive/v3/files", json={
            "name": "Stridian videos", "mimeType": "application/vnd.google-apps.folder"})
        r.raise_for_status()
        set_env("GOOGLE_DRIVE_FOLDER_ID", r.json()["id"])

    set_env("STORAGE", "drive")

    print("\nDone. These are now in your .env file. Add the same three to Vercel")
    print("(Project -> Settings -> Environment Variables), plus the two you already have:\n")
    for key in ("GOOGLE_REFRESH_TOKEN", "GOOGLE_DRIVE_FOLDER_ID"):
        print(f"  {key}={os.environ[key]}")
    print("  STORAGE=drive")


if __name__ == "__main__":
    main()
