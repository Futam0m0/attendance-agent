"""
Agent Brain — the decision-making core.

This is what makes it "agentic":
  OBSERVE  → what time is it? what classes are today?
  DECIDE   → should I send a class reminder? trigger uCheck? retry?
  ACT      → send Telegram message, log action, update state

uCheck behaviour:
  - Fires 5 mins before each class
  - Retries every 5 mins up to 3 times per class
  - Resets per class — so 3 classes = 3 separate uCheck cycles
  - Stops immediately when user replies /ucheck_done
  - Rearms for the next class automatically
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo
from config.settings import Config, ClassSlot, DeadlineSlot

logger = logging.getLogger(__name__)

UCHECK_TRIGGER_MINS = 5      # fire uCheck this many mins before class
UCHECK_RETRY_SECS   = 300    # retry every 5 minutes
UCHECK_MAX_RETRIES  = 3      # max retries per class


class AttendanceAgent:

    def __init__(self, config: Config):
        self.config = config
        self.tz = ZoneInfo(config.timezone)

        # Class reminder tracking
        self._sent_reminders: set = set()       # keys: "Monday-09:00"

        # uCheck tracking — per class
        self._ucheck_done: bool = False          # confirmed for current class
        self._ucheck_retries: int = 0            # retries sent for current class
        self._ucheck_last_sent: Optional[datetime] = None
        self._ucheck_current_class: Optional[str] = None  # "Monday-09:00" key

        self._last_date: str = ""

    def now(self) -> datetime:
        return datetime.now(self.tz)

    # ── DAILY RESET ──────────────────────────────────────────────────────────

    def _reset_daily_state(self):
        today = self.now().strftime("%Y-%m-%d")
        if today != self._last_date:
            logger.info(f"New day detected ({today}), resetting agent state.")
            self._sent_reminders.clear()
            self._reset_ucheck_state()
            self._last_date = today

    def _reset_ucheck_state(self):
        """Reset uCheck cycle — called at midnight and between classes."""
        self._ucheck_done = False
        self._ucheck_retries = 0
        self._ucheck_last_sent = None
        self._ucheck_current_class = None

    # ── OBSERVE ──────────────────────────────────────────────────────────────

    def get_todays_classes(self) -> list:
        today_name = self.now().strftime("%A")
        return [c for c in self.config.schedule if c.day == today_name]

    def minutes_until(self, time_str: str) -> float:
        now = self.now()
        h, m = map(int, time_str.split(":"))
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        return (target - now).total_seconds() / 60

    # ── DECIDE — CLASS REMINDERS ─────────────────────────────────────────────

    def should_remind_class(self, cls: ClassSlot) -> bool:
        key = f"{cls.day}-{cls.time}"
        if key in self._sent_reminders:
            return False
        mins = self.minutes_until(cls.time)
        return 0 <= mins <= cls.remind_minutes

    # ── DECIDE — uCHECK (per class) ──────────────────────────────────────────

    def _ucheck_key(self, cls: ClassSlot) -> str:
        return f"{cls.day}-{cls.time}"

    def should_trigger_ucheck(self, cls: ClassSlot) -> bool:
        """Fire the first uCheck reminder 5 mins before this class."""
        key = self._ucheck_key(cls)

        # Already confirmed for this class
        if self._ucheck_done and self._ucheck_current_class == key:
            return False

        # Already started a uCheck cycle for this class
        if self._ucheck_current_class == key and self._ucheck_retries > 0:
            return False

        # Only fire within the 5-min window before class
        mins = self.minutes_until(cls.time)
        return 0 <= mins <= UCHECK_TRIGGER_MINS

    def should_retry_ucheck(self, cls: ClassSlot) -> bool:
        """Retry uCheck if not confirmed and enough time has passed."""
        key = self._ucheck_key(cls)

        # Not in a uCheck cycle for this class
        if self._ucheck_current_class != key:
            return False

        # Already confirmed
        if self._ucheck_done:
            return False

        # Hit max retries (first send = attempt 1, so allow up to MAX_RETRIES total)
        if self._ucheck_retries > UCHECK_MAX_RETRIES:
            return False

        # Not sent yet
        if self._ucheck_last_sent is None:
            return False

        elapsed = (self.now() - self._ucheck_last_sent).total_seconds()
        return elapsed >= UCHECK_RETRY_SECS

    # ── ACT ──────────────────────────────────────────────────────────────────

    def mark_class_reminded(self, cls: ClassSlot):
        self._sent_reminders.add(f"{cls.day}-{cls.time}")
        logger.info(f"Class reminder sent: {cls.name} @ {cls.time}")

    def mark_ucheck_sent(self, cls: ClassSlot):
        key = self._ucheck_key(cls)
        self._ucheck_current_class = key
        self._ucheck_retries += 1
        self._ucheck_last_sent = self.now()
        logger.info(f"uCheck sent for {cls.name} (attempt {self._ucheck_retries})")

    def confirm_ucheck(self):
        """Called when user replies /ucheck_done."""
        self._ucheck_done = True
        logger.info(f"uCheck confirmed for {self._ucheck_current_class}")

    def rearm_ucheck_for_next_class(self, cls: ClassSlot):
        """Reset uCheck state when moving to a new upcoming class."""
        key = self._ucheck_key(cls)
        if self._ucheck_current_class is None or self._ucheck_current_class == key:
            return
        # Rearm if: previous class confirmed, OR previous class started >10 mins ago
        prev_time = self._ucheck_current_class.split("-", 1)[1]
        mins_since = -self.minutes_until(prev_time)  # positive = past
        if self._ucheck_done or mins_since > 10:
            logger.info(f"Rearming uCheck for new class: {cls.name}")
            self._reset_ucheck_state()

    # ── DEADLINE HELPERS ─────────────────────────────────────────────────────

    _DAYS = {"Monday":0,"Tuesday":1,"Wednesday":2,
             "Thursday":3,"Friday":4,"Saturday":5,"Sunday":6}

    def days_until_deadline(self, deadline: DeadlineSlot) -> int:
        today_weekday = self.now().weekday()
        target_weekday = self._DAYS[deadline.day]
        days = (target_weekday - today_weekday) % 7
        return days if days > 0 else 7

    def should_remind_deadline(self, deadline: DeadlineSlot) -> bool:
        days_left = self.days_until_deadline(deadline)
        if days_left not in deadline.remind_days_before:
            return False
        key = f"deadline-{deadline.name}-{days_left}d"
        if key in self._sent_reminders:
            return False
        mins = self.minutes_until(deadline.remind_time)
        return 0 <= mins <= 2

    def mark_deadline_reminded(self, deadline: DeadlineSlot, days_left: int):
        key = f"deadline-{deadline.name}-{days_left}d"
        self._sent_reminders.add(key)
        logger.info(f"Deadline reminder sent: {deadline.name} ({days_left}d away)")

    def get_upcoming_deadlines(self) -> list:
        result = []
        for d in self.config.deadlines:
            days_left = self.days_until_deadline(d)
            result.append((d, days_left))
        return sorted(result, key=lambda x: x[1])

    # ── TICK ─────────────────────────────────────────────────────────────────

    def tick(self) -> list:
        self._reset_daily_state()
        actions = []
        classes = self.get_todays_classes()

        for cls in classes:
            # Class reminder
            if self.should_remind_class(cls):
                actions.append({"type": "class_reminder", "class": cls})
                self.mark_class_reminded(cls)

            # Rearm uCheck if this is a new class
            self.rearm_ucheck_for_next_class(cls)

            # uCheck — first trigger
            if self.should_trigger_ucheck(cls):
                actions.append({"type": "ucheck_reminder", "class": cls})
                self.mark_ucheck_sent(cls)

            # uCheck — retries
            elif self.should_retry_ucheck(cls):
                actions.append({
                    "type": "ucheck_retry",
                    "class": cls,
                    "attempt": self._ucheck_retries
                })
                self.mark_ucheck_sent(cls)

        # Deadline reminders
        for deadline in self.config.deadlines:
            if self.should_remind_deadline(deadline):
                days_left = self.days_until_deadline(deadline)
                actions.append({"type": "deadline_reminder",
                                 "deadline": deadline,
                                 "days_left": days_left})
                self.mark_deadline_reminded(deadline, days_left)

        return actions

    # ── DAILY SUMMARY ────────────────────────────────────────────────────────

    def daily_summary(self) -> str:
        classes = self.get_todays_classes()
        ucheck_status = "✅ Confirmed" if self._ucheck_done else "⏳ Pending"
        reminded = len(self._sent_reminders)

        lines = ["📡 *DAILY DEBRIEF — MEI LING*", ""]
        lines.append(f"📅 {self.now().strftime('%A, %d %B %Y')}")
        lines.append(f"🎯 Missions today: {len(classes)}")
        for c in classes:
            tick = "✅" if f"{c.day}-{c.time}" in self._sent_reminders else "⏳"
            lines.append(f"  {tick} {c.name} @ {c.time}")
        lines.append(f"🩺 uCheck: {ucheck_status}")
        lines.append(f"🔔 Codec transmissions sent: {reminded}")

        upcoming = self.get_upcoming_deadlines()
        if upcoming:
            lines.append("")
            lines.append("📝 *Upcoming Objectives*")
            for deadline, days_left in upcoming[:5]:
                urgency = "🔴" if days_left <= 1 else "🟡" if days_left <= 3 else "🟢"
                lines.append(f"  {urgency} {deadline.name} — due {deadline.day} {deadline.time} ({days_left}d away)")

        lines.append("")
        lines.append("_\"Good work today, Snake. Get some rest.\"_")
        return "\n".join(lines)
