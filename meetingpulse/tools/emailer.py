import os
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

mcp = FastMCP("emailer")

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.send",
]

BASE_DIR = Path(__file__).parent.parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")


def _get_gmail_service():
    creds = None

    token_json_env = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json_env:
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

    return build("gmail", "v1", credentials=creds)


def _send(to_email: str, subject: str, body: str) -> None:
    sender = GMAIL_ADDRESS or "me"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    service = _get_gmail_service()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


@mcp.tool()
def send_followup_email(
    to_email: str,
    owner_name: str,
    task: str,
    deadline: str,
    meeting_title: str,
) -> str:
    """
    Send a follow-up email to one person about their action item.
    Call after tracker_log_action_items, once per action item.
    """
    deadline_line = f"Due: {deadline}" if deadline != "TBD" else "Due date: to be confirmed"

    body = f"""Hi {owner_name},

This is a quick reminder from your recent meeting: {meeting_title}

Action item assigned to you:
  {task}

{deadline_line}

Please reach out if you have any questions or blockers.

— MeetingPulse (automated)
"""

    subject = f"Action item from {meeting_title}: {task[:60]}"

    _send(to_email, subject, body)
    return f"Follow-up email sent to {to_email} for task: {task}"


@mcp.tool()
def send_overdue_alert(to_email: str, overdue_items: list[dict]) -> str:
    """
    Send an overdue digest email listing all past-deadline action items.

    This is called by the daily scheduler (not directly by Claude).
    - to_email: your own email address (the ALERT_EMAIL from .env)
    - overdue_items: list of dicts with keys: task, owner, owner_email, deadline, meeting_title
    """
    if not overdue_items:
        return "No overdue items — nothing to send."

    lines = ["The following action items are past their deadline:\n"]

    for i, item in enumerate(overdue_items, start=1):
        lines.append(
            f"{i}. [{item.get('meeting_title', 'Unknown meeting')}]"
            f" {item['task']}"
            f"\n   Owner: {item['owner']} <{item['owner_email']}>"
            f"\n   Deadline: {item['deadline']}"
            f"\n   Status: {item.get('status', 'pending')}\n"
        )

    lines.append("\nPlease follow up with the relevant team members.")
    lines.append("\n— MeetingPulse Scheduler (automated daily digest)")

    body = "\n".join(lines)
    subject = f"MeetingPulse: {len(overdue_items)} overdue action item(s)"

    _send(to_email, subject, body)
    return f"Overdue digest sent to {to_email} covering {len(overdue_items)} item(s)."
