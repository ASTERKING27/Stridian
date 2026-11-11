"""One Google login for everything: the video folder in Drive and the squad Sheet.

It is an OAuth refresh token for the account that ran setup_google.py, limited to the
`drive.file` scope — the app can only see files it created itself, nothing else in
that Drive. (A service account would be simpler to set up, but service accounts have
no storage quota of their own, so they cannot use a personal 5 TB Drive.)
"""

import os
from functools import lru_cache

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_URI = "https://oauth2.googleapis.com/token"
KEYS = ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")


def configured() -> bool:
    return all(os.environ.get(k) for k in KEYS)


@lru_cache(maxsize=1)
def session():
    """An HTTP session that adds (and refreshes) the access token by itself."""
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2.credentials import Credentials

    if not configured():
        raise RuntimeError("Google is not set up — run backend/setup_google.py first.")
    creds = Credentials(
        None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri=TOKEN_URI,
        scopes=SCOPES,
    )
    return AuthorizedSession(creds)
