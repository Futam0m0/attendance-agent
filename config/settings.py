"""
Config loader — reads from .env and schedule.json
"""

import os
import json
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

@dataclass
class ClassSlot:
    name: str          # e.g. "Operating Systems Lab"
    day: str           # e.g. "Monday"
    time: str          # e.g. "09:00"  (24h format)
    remind_minutes: int = 10   # how many mins before class to remind


@dataclass
class DeadlineSlot:
    name: str               # e.g. "OS Assignment 1"
    day: str                # day of week it's due, e.g. "Friday"
    time: str               # due time, e.g. "23:59"
    remind_days_before: list = field(default_factory=lambda: [3, 1])
    remind_time: str = "09:00"   # what time of day to send the reminder


@dataclass
class UCheckConfig:
    enabled: bool = True
    trigger_time: str = "08:30"   # daily uCheck reminder time
    retry_count: int = 3
    retry_interval_seconds: int = 300


@dataclass
class Config:
    telegram_token: str
    chat_id: str
    schedule: List[ClassSlot] = field(default_factory=list)
    ucheck: UCheckConfig = field(default_factory=UCheckConfig)
    deadlines: List[DeadlineSlot] = field(default_factory=list)
    timezone: str = "Asia/Seoul"


def load_config() -> Config:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise EnvironmentError(
            "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env"
        )

    # Load class schedule from JSON file
    schedule = []
    schedule_path = os.path.join(os.path.dirname(__file__), "schedule.json")
    if os.path.exists(schedule_path):
        with open(schedule_path) as f:
            raw = json.load(f)
            for item in raw.get("classes", []):
                schedule.append(ClassSlot(**item))

    ucheck_raw = raw.get("ucheck", {}) if os.path.exists(schedule_path) else {}
    ucheck = UCheckConfig(**ucheck_raw) if ucheck_raw else UCheckConfig()

    # Load deadlines
    deadlines = []
    for item in raw.get("deadlines", []):
        deadlines.append(DeadlineSlot(**item))

    return Config(
        telegram_token=token,
        chat_id=chat_id,
        schedule=schedule,
        ucheck=ucheck,
        deadlines=deadlines,
        timezone=os.getenv("TIMEZONE", "Asia/Seoul")
    )
