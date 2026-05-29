# Adaptive Attendance & Submission Reminder System

An agentic automation system that autonomously monitors your class schedule and sends adaptive Telegram reminders. Built as a university Operating Systems course project.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat&logo=telegram&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-WSL%20%7C%20Linux-FCC624?style=flat&logo=linux&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

---

## What it does

The agent runs silently in the background and sends Telegram messages to:

- 🔔 Remind you before each class starts
- 🩺 Remind you to complete your attendance check-in before every class — with escalating follow-ups if ignored
- 📝 Alert you about assignment deadlines 3 days and 1 day before they are due
- 📋 Give you a full daily summary on demand

All reminders are adaptive — if you do not respond to the attendance check-in prompt, the agent retries up to 3 times at 5-minute intervals with increasing urgency. The moment you reply `/ucheck_done`, it stops.

---

## System architecture

![System Diagram](assets/system-diagram.png)

The system uses a two-bot architecture:

| Bot | Role |
|---|---|
| **Attendance Agent Bot** | Runs the autonomous reminder loop |
| **AI Assistant Bot** (optional) | Natural language interface — edit schedules by texting it |

The AI Assistant Bot edits `schedule.json` directly. You send `/reload` to the Attendance Agent Bot to apply changes instantly — no restart needed.

---

## Agent loop

Every 60 seconds the agent runs an **Observe → Decide → Act** cycle:

```
Observe  →  Read system time, today's classes, uCheck status
Decide   →  Is a class starting soon? Check-in pending? Retry overdue?
Act      →  Send Telegram message, update state, log action
```

State resets automatically at midnight. No manual intervention needed.

---

## Telegram commands

| Command | Description |
|---|---|
| `/start` | Start the bot and list available commands |
| `/today` | Show today's class schedule |
| `/deadlines` | Show upcoming submission deadlines |
| `/ucheck_done` | Confirm attendance check-in complete — stops retries |
| `/summary` | Full daily summary |
| `/status` | Live agent status |
| `/reload` | Apply schedule changes without restarting |

---

## Project structure

```
attendance_agent/
├── main.py                   ← entry point
├── agent/
│   ├── brain.py              ← observe / decide / act logic
│   ├── scheduler.py          ← 60s tick loop, executes actions
│   └── bot.py                ← Telegram bot + command handlers
├── config/
│   ├── settings.py           ← config loader
│   └── schedule.json         ← your timetable and deadlines
├── logs/                     ← agent.log written here automatically
├── tests/
│   └── test_agent.py         ← unit tests for brain logic
└── requirements.txt
```

---

## Setup

### Prerequisites

- Python 3.11+
- WSL (Ubuntu) or any Linux environment
- A Telegram account

### 1. Clone the repo

```bash
git clone https://github.com/Futam0m0/attendance-agent.git
cd attendance-agent
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create your Telegram bot

1. Open Telegram and message `@BotFather`
2. Send `/newbot` and follow the prompts
3. Copy the token it gives you

To get your chat ID, message `@userinfobot` on Telegram and copy the `id` field.

### 4. Configure your credentials

```bash
cp .env.example .env
nano .env
```

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
TIMEZONE=Asia/Seoul
```

### 5. Set your class schedule

Edit `config/schedule.json` with your real timetable:

```json
{
  "classes": [
    {
      "name": "Operating Systems",
      "day": "Monday",
      "time": "09:00",
      "remind_minutes": 15
    }
  ],
  "ucheck": {
    "enabled": true,
    "trigger_time": "08:30",
    "retry_count": 3,
    "retry_interval_seconds": 300
  },
  "deadlines": [
    {
      "name": "OS Assignment 1",
      "day": "Friday",
      "time": "23:59",
      "remind_days_before": [3, 1],
      "remind_time": "09:00"
    }
  ]
}
```

**Field reference:**

| Field | Description |
|---|---|
| `day` | Full day name: `Monday`, `Tuesday`, etc. |
| `time` | 24h format: `09:00`, `14:00` |
| `remind_minutes` | How many minutes before class to send the reminder |
| `remind_days_before` | List of days before deadline to send alerts |
| `remind_time` | Time of day to send deadline reminders |

### 6. Run

```bash
python3 main.py
```

Send `/start` to your bot on Telegram to confirm it is running.

**Optional — create a shortcut alias:**

```bash
echo "alias attendance='cd ~/attendance-agent && source venv/bin/activate && python3 main.py'" >> ~/.bashrc
source ~/.bashrc
```

Then just type `attendance` to start it.

---

## Editing your schedule via an AI assistant (optional)

If you use a second Telegram bot powered by an AI assistant, add this to its system prompt to enable natural language schedule editing:

> "You have access to my schedule file at `~/attendance-agent/config/schedule.json`. When I ask you to add or remove a class or deadline, edit the file directly and remind me to send /reload to the attendance bot."

Then just text the assistant:
```
Add Linear Algebra every Friday at 2pm, remind me 10 minutes before
```

And send `/reload` to the attendance bot to apply the change instantly.

---

## Personalisation

All reminder message text is defined in `agent/bot.py` and `agent/scheduler.py`. Edit the message strings in those files to change the tone, language, or style to suit your preference.

---

## Running tests

```bash
pytest tests/ -v
```

---

## OS concepts demonstrated

This project was built as a university Operating Systems course project. Concepts demonstrated:

- **Process scheduling** — 60-second tick loop with `asyncio`
- **Background service behaviour** — runs indefinitely without user input
- **Event-driven programming** — Telegram commands trigger state changes
- **Timer-based execution** — `asyncio.sleep()` for polling interval
- **Fault recovery** — retry logic with escalation, error handling on every tick
- **Concurrency** — bot and scheduler run concurrently via `asyncio.gather()`
- **File-based IPC** — two bots communicate through a shared JSON config file

---

## Built with

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
- Python `asyncio`, `zoneinfo`, `logging`
