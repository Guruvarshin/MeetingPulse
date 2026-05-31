# MeetingPulse

A remote MCP server that turns raw meeting notes into action items, follow-up emails, and Google Calendar reminders — all triggered through a single conversation with Claude.

Deployed on Railway. Connects to Claude via the MCP streamable-HTTP transport.

---

## What it does

Paste your meeting notes into Claude. MeetingPulse automatically:

1. **Extracts and logs** every action item into a SQLite tracker
2. **Sends a follow-up email** to each owner via Gmail
3. **Creates a Google Calendar event** on the deadline with a 24-hour reminder
4. **Runs a daily overdue check** every weekday at 9 AM and emails you a digest of anything past its deadline

---

## Tools exposed to Claude

| Tool | What it does |
|---|---|
| `tracker_log_action_items` | Saves action items to the database, returns row IDs |
| `tracker_get_all_items` | Retrieves all items, optionally filtered by owner |
| `tracker_mark_done` | Marks an item complete and triggers calendar cleanup |
| `email_send_followup_email` | Sends a follow-up email to the task owner |
| `email_send_overdue_alert` | Sends an overdue digest to the organiser |
| `calendar_create_calendar_reminder` | Creates an all-day Google Calendar event with email reminder |
| `calendar_delete_calendar_event` | Deletes the calendar event when an item is marked done |

---

## Tech stack

- **[FastMCP](https://github.com/jlowin/fastmcp)** — MCP server framework
- **SQLite + SQLAlchemy** — action item persistence
- **APScheduler** — background scheduler for daily overdue checks
- **Gmail SMTP** — follow-up and alert emails
- **Google Calendar API** — calendar event creation and deletion
- **Railway** — cloud deployment with always-on HTTP transport

---

## Project structure

```
MeetingPulse/
├── Dockerfile
├── railway.toml
├── meetingpulse/
│   ├── server.py          # FastMCP server, mounts all tool modules
│   ├── db.py              # SQLite helpers (insert, query, update)
│   ├── scheduler.py       # APScheduler setup, daily overdue job
│   └── tools/
│       ├── tracker.py     # log, list, mark-done tools
│       ├── emailer.py     # follow-up and overdue alert tools
│       ├── calendar_tool.py  # Google Calendar create/delete tools
│       └── overdue.py     # scheduler-called overdue check function
```

---

## Local setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/YOUR_USERNAME/meetingpulse.git
cd meetingpulse/meetingpulse
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e .
```

### 2. Create a `.env` file

```
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
ALERT_EMAIL=you@gmail.com
```

Generate a Gmail App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

### 3. Set up Google Calendar credentials

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → enable **Google Calendar API**
3. Create an OAuth 2.0 credential (Desktop app) → download as `credentials.json`
4. Place `credentials.json` inside the `meetingpulse/` folder
5. Run the server once — a browser window will open to authorise access
6. After approval, `token.json` is created automatically. All future runs use it silently.

### 4. Run locally

```bash
python server.py
```

Server starts on `http://localhost:8000`.

---

## Deployment on Railway

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/meetingpulse.git
git push -u origin main
```

### 2. Deploy

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Select this repository — Railway detects the `Dockerfile` automatically

### 3. Add environment variables

In Railway dashboard → Variables, add:

```
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
ALERT_EMAIL=you@gmail.com
```

### 4. Generate a public domain

Railway dashboard → Settings → Networking → Generate Domain

Your server will be live at `https://meetingpulse-production.up.railway.app`.

---

## Connecting to Claude Code

Add this to your Claude Code MCP config:

```json
{
  "mcpServers": {
    "MeetingPulse": {
      "type": "http",
      "url": "https://your-railway-url.up.railway.app/mcp"
    }
  }
}
```

---

## Example usage

> "Here are my meeting notes from today's sprint planning: Arjun will finish the API integration by June 5. Meera will send the design mockups by June 3. Ravi needs to update the deployment docs — no deadline yet."

MeetingPulse will:
- Log 3 action items to the tracker
- Email Arjun, Meera, and Ravi with their tasks
- Create calendar events for Arjun (June 5) and Meera (June 3)
- Skip the calendar event for Ravi since his deadline is TBD
- Send you an overdue digest at 9 AM on any day a deadline is missed

---

## Environment variables reference

| Variable | Description |
|---|---|
| `GMAIL_ADDRESS` | Gmail account used to send emails |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not your account password) |
| `ALERT_EMAIL` | Email address to receive daily overdue digests |
| `PORT` | Server port (set automatically by Railway, defaults to 8000) |
