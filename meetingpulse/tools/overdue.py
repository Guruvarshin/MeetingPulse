import os
import logging
from dotenv import load_dotenv

from db import get_overdue_items
from tools.emailer import _send

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

ALERT_EMAIL = os.environ.get("ALERT_EMAIL")


def check_and_alert_overdue() -> None:
    overdue = get_overdue_items()

    if not overdue:
        logger.info("Overdue check complete — no overdue items found.")
        return

    logger.info(f"Found {len(overdue)} overdue item(s). Sending digest to {ALERT_EMAIL}.")

    lines = [f"The following {len(overdue)} action item(s) are past their deadline:\n"]

    for i, item in enumerate(overdue, start=1):
        lines.append(
            f"{i}. [{item.get('meeting_title', 'Unknown meeting')}] {item['task']}\n"
            f"   Owner: {item['owner']} <{item['owner_email']}>\n"
            f"   Deadline: {item['deadline']}\n"
            f"   Status: {item.get('status', 'pending')}\n"
        )

    lines.append("Please follow up with the relevant team members.")
    lines.append("\n— MeetingPulse Scheduler (automated daily digest)")

    body = "\n".join(lines)
    subject = f"MeetingPulse: {len(overdue)} overdue action item(s)"

    if not ALERT_EMAIL:
        logger.error(
            "ALERT_EMAIL is not set in .env — cannot send overdue digest. "
            "Add ALERT_EMAIL=you@gmail.com to your .env file."
        )
        return

    try:
        _send(ALERT_EMAIL, subject, body)
        logger.info(f"Overdue digest sent successfully to {ALERT_EMAIL}.")
    except Exception as e:
        logger.error(f"Failed to send overdue digest: {e}")
