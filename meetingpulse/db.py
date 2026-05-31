import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "meetingpulse.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS action_items (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_title     TEXT    NOT NULL,
                task              TEXT    NOT NULL,
                owner             TEXT    NOT NULL,
                owner_email       TEXT    NOT NULL,
                deadline          TEXT    NOT NULL,
                status            TEXT    NOT NULL DEFAULT 'pending',
                created_at        TEXT    NOT NULL,
                calendar_event_id TEXT
            )
        """)
        try:
            conn.execute("ALTER TABLE action_items ADD COLUMN calendar_event_id TEXT")
        except Exception:
            pass
        conn.commit()


def insert_action_item(
    meeting_title: str,
    task: str,
    owner: str,
    owner_email: str,
    deadline: str,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO action_items
                (meeting_title, task, owner, owner_email, deadline, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (meeting_title, task, owner, owner_email, deadline, now),
        )
        conn.commit()
        return cur.lastrowid


def get_overdue_items() -> list[dict]:
    today = datetime.now(timezone.utc).date().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM action_items
            WHERE status != 'done'
              AND deadline < ?
            ORDER BY deadline ASC
            """,
            (today,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_all_items(owner: str | None = None) -> list[dict]:
    with get_conn() as conn:
        if owner:
            rows = conn.execute(
                "SELECT * FROM action_items WHERE lower(owner) = lower(?) ORDER BY deadline ASC",
                (owner,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM action_items ORDER BY deadline ASC"
            ).fetchall()
    return [dict(row) for row in rows]


def update_status(item_id: int, status: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE action_items SET status = ? WHERE id = ?",
            (status, item_id),
        )
        conn.commit()
        return cur.rowcount > 0


def get_item_by_id(item_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM action_items WHERE id = ?", (item_id,)
        ).fetchone()
    return dict(row) if row else None


def update_calendar_event_id(item_id: int, event_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE action_items SET calendar_event_id = ? WHERE id = ?",
            (event_id, item_id),
        )
        conn.commit()
