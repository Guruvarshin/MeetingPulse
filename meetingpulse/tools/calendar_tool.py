import os
from pathlib import Path
from datetime import datetime, timedelta

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from fastmcp import FastMCP

mcp = FastMCP("calendar_tool")

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"


def _get_calendar_service():
    creds = None

    token_json_env = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json_env:
        import json
        creds = Credentials.from_authorized_user_info(json.loads(token_json_env), SCOPES)
    elif TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {CREDENTIALS_FILE}.\n"
                    "Set GOOGLE_TOKEN_JSON env variable on Railway or provide credentials.json locally."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        if not token_json_env:
            TOKEN_FILE.write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def _create_reminder(task: str, owner_email: str, deadline: str) -> tuple[str, str | None]:
    if deadline == "TBD":
        return f"Skipped calendar event for '{task}' — deadline is TBD.", None

    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
    except ValueError:
        return f"Invalid deadline format '{deadline}' — expected YYYY-MM-DD.", None

    service = _get_calendar_service()

    end_date = deadline_date + timedelta(days=1)

    event_body = {
        "summary": f"Action item due: {task}",
        "description": (
            f"This action item was created by MeetingPulse.\n\n"
            f"Task: {task}\n"
            f"Assigned to: {owner_email}\n"
            f"Deadline: {deadline}"
        ),
        "start": {"date": str(deadline_date)},
        "end":   {"date": str(end_date)},
        "attendees": [{"email": owner_email}],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 1440},
            ],
        },
    }

    created_event = (
        service.events()
        .insert(
            calendarId="primary",
            body=event_body,
            sendUpdates="all",
        )
        .execute()
    )

    event_id = created_event.get("id")
    event_link = created_event.get("htmlLink", "no link returned")
    return (
        f"Calendar event created for '{task}' on {deadline}. "
        f"Invite sent to {owner_email}. View: {event_link}"
    ), event_id


@mcp.tool()
def delete_calendar_event(event_id: str) -> str:
    """
    Delete a Google Calendar event by its event ID.

    Call this immediately after tracker_mark_done when the item has a
    calendar_event_id — the mark_done response will tell you the event ID.
    """
    try:
        service = _get_calendar_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return f"Calendar event {event_id} deleted successfully."
    except Exception as e:
        return f"Could not delete calendar event {event_id}: {e}"


@mcp.tool()
def create_calendar_reminder(
    task: str,
    owner_email: str,
    deadline: str,
    item_id: int = 0,
) -> str:
    """
    Create a Google Calendar all-day event on the deadline with a 24-hour
    email reminder. Skips silently if deadline is 'TBD'. Call after
    tracker_log_action_items, once per action item that has a real deadline.

    - item_id: the tracker DB id returned by tracker_log_action_items. Pass it
      so the calendar event can be deleted automatically when the item is marked done.
    """
    from db import update_calendar_event_id

    message, event_id = _create_reminder(task, owner_email, deadline)
    if event_id and item_id > 0:
        update_calendar_event_id(item_id, event_id)
    return message
