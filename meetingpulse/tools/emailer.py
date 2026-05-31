import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("emailer")

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")


def _send(to_email: str, subject: str, body: str) -> None:
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise EnvironmentError(
            "GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in the .env file. "
            "Generate an App Password at https://myaccount.google.com/apppasswords"
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(
            GMAIL_ADDRESS,
            to_email,
            msg.as_string(),
        )


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
