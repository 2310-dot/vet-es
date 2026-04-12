#!/usr/bin/env python3
"""One-time OAuth desktop flow to obtain a Google Calendar refresh token (VE-30).

Run locally after creating a **Desktop** OAuth client in Google Cloud Console and
downloading its JSON (client id + secret). Scope is read-only Calendar access.

Usage::

    python scripts/get_google_token.py path/to/client_secret.apps.googleusercontent.com.json

The script prints ``GOOGLE_CALENDAR_REFRESH_TOKEN=...`` for your ``.env``. Never
commit the JSON file or the printed token.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

OAUTH_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Obtain Google Calendar OAuth refresh token (desktop flow).",
    )
    parser.add_argument(
        "client_secrets_file",
        type=Path,
        help="Path to OAuth client JSON from Google Cloud Console (Desktop app).",
    )
    args = parser.parse_args()
    path = args.client_secrets_file
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(str(path), [OAUTH_SCOPE])
    creds = flow.run_local_server(port=0, prompt="consent")
    if not creds.refresh_token:
        print(
            "No refresh_token returned. Revoke app access in Google Account "
            "security settings and retry with prompt=consent.",
            file=sys.stderr,
        )
        return 1
    print("Add to your .env (do not commit):")
    print(f"GOOGLE_CALENDAR_REFRESH_TOKEN={creds.refresh_token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
