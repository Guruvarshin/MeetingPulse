import os
from fastmcp import FastMCP

from db import init_db
from scheduler import start_scheduler
from tools.emailer import mcp as emailer_mcp
from tools.calendar_tool import mcp as calendar_mcp
from tools.tracker import mcp as tracker_mcp

mcp = FastMCP(
    "MeetingPulse",
    instructions=(
        "You are MeetingPulse, a meeting action-item assistant. "
        "When the user provides meeting notes or asks you to log action items, "
        "you MUST execute ALL of the following steps in order — skipping any step is not allowed:\n"
        "  STEP 1: Call tracker_log_action_items with every action item extracted from the notes.\n"
        "  STEP 2: Call email_send_followup_email once for EACH action item logged.\n"
        "  STEP 3: Call calendar_create_calendar_reminder once for EACH action item whose "
        "deadline is NOT 'TBD'. You MUST pass the item_id returned in Step 1. "
        "This step is MANDATORY — do NOT skip it even if you think it is optional.\n"
        "Do NOT reply to the user until all three steps are complete."
    ),
)

mcp.mount(emailer_mcp, namespace="email")
mcp.mount(calendar_mcp, namespace="calendar")
mcp.mount(tracker_mcp, namespace="tracker")

init_db()
start_scheduler()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
