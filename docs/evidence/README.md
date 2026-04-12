# Evidence (VE-30 — Google Calendar)

This folder is for **verifiable proof** that a live Google Calendar call succeeded (coursework / review), without committing secrets.

## What to capture

1. Run the API with a valid `.env` (no `GOOGLE_CALENDAR_USE_STUB`, full OAuth vars set).
2. Trigger a weekday `check_surgical_availability` call (e.g. via `POST /chat` asking for theatre availability on a specific Tuesday).
3. Copy from server logs a line that mentions **`calendar.googleapis.com`** (emitted by `google_calendar_tool` before `events.list`).

## Example log line (illustrative)

See [sample-log-google-calendar.txt](sample-log-google-calendar.txt) for a redacted template. Replace placeholders with your local run; do not paste refresh tokens or client secrets.

You may also add a short screen recording or screenshot to your PR description instead of a file in this directory.
