from fastmcp import FastMCP

from db import insert_action_item, get_all_items as _get_all, update_status, get_item_by_id

mcp = FastMCP("tracker")


@mcp.tool()
def log_action_items(action_items: list[dict]) -> str:
    """
    Save action items to the database. Always call this first — before
    email_send_followup_email or calendar_create_calendar_reminder.

    Extract action items from meeting notes yourself: for each bullet/task
    identify task (what to do), owner (name), owner_email, deadline (YYYY-MM-DD,
    convert "next Monday"/"this Friday"/"in 3 days" to absolute dates, use "TBD"
    if none mentioned), and meeting_title.

    Each dict must have: meeting_title, task, owner, owner_email, deadline.
    """
    saved = []
    failed = []

    for item in action_items:
        meeting_title = item.get("meeting_title", "")
        task          = item.get("task", "")
        owner         = item.get("owner", "")
        owner_email   = item.get("owner_email", "")
        deadline      = item.get("deadline", "TBD")

        if not task or not owner_email:
            failed.append(item)
            continue

        row_id = insert_action_item(
            meeting_title=meeting_title,
            task=task,
            owner=owner,
            owner_email=owner_email,
            deadline=deadline,
        )
        saved.append({"id": row_id, "task": task, "owner": owner})

    parts = [f"Logged {len(saved)} action item(s) to the tracker."]
    for s in saved:
        parts.append(f"  • [id={s['id']}] {s['task']} — {s['owner']}")
    if failed:
        parts.append(f"{len(failed)} item(s) skipped (missing task or email).")

    parts.append(
        "\n⚠️ YOU MUST NOW COMPLETE THESE STEPS BEFORE REPLYING TO THE USER:"
    )
    parts.append(
        "STEP 2 — call email_send_followup_email once for EACH item above."
    )

    items_with_deadline = [
        item for item in action_items
        if item.get("deadline", "TBD") != "TBD"
    ]
    if items_with_deadline:
        parts.append(
            "STEP 3 — call calendar_create_calendar_reminder once for EACH of these items "
            "(deadline is NOT TBD, so a calendar event is REQUIRED). "
            "You MUST pass the item_id from the list above so the event can be deleted when marked done:"
        )
        for item in items_with_deadline:
            matched = next((s for s in saved if s["task"] == item["task"]), None)
            id_hint = f"  item_id={matched['id']}" if matched else ""
            parts.append(
                f"  • task={item['task']!r}  owner_email={item['owner_email']!r}"
                f"  deadline={item['deadline']!r}{id_hint}"
            )
    else:
        parts.append(
            "STEP 3 — skip calendar_create_calendar_reminder (all deadlines are TBD)."
        )

    parts.append("Do NOT say 'Done' until both steps above are confirmed complete.")

    return "\n".join(parts)


@mcp.tool()
def get_all_items(owner: str = "") -> list[dict]:
    """
    Retrieve action items from the database.

    - Pass owner="" (or omit it) to get every item across all meetings.
    - Pass owner="Arjun" to filter to just that person's items.

    Use this to answer questions like:
      "What's still pending for Meera?"
      "Show me everything from last week's sprint planning."
      "Which items are overdue?"
    """
    owner_filter = owner.strip() if owner else None
    items = _get_all(owner=owner_filter)
    return items


@mcp.tool()
def mark_done(item_id: int) -> str:
    """
    Mark an action item as done by its database ID.

    Use this when the user says something like:
      "Arjun finished the API integration" or "mark item 3 as complete".

    - item_id: the integer ID shown when items were logged or listed.
    """
    item = get_item_by_id(item_id)
    if not item:
        return (
            f"No item found with id={item_id}. "
            "Use get_all_items() to see the current list with correct IDs."
        )

    success = update_status(item_id, "done")
    if not success:
        return (
            f"No item found with id={item_id}. "
            "Use get_all_items() to see the current list with correct IDs."
        )

    result = f"Item {item_id} marked as done. It will no longer appear in overdue alerts."

    event_id = item.get("calendar_event_id")
    if event_id:
        result += (
            f"\n⚠️ NEXT STEP REQUIRED: call calendar_delete_calendar_event with "
            f"event_id={event_id!r} to remove the calendar reminder."
        )

    return result
