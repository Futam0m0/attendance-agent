"""
Scheduler -- runs the agent tick every 60 seconds and executes actions.
"""

import asyncio
import logging
from config.settings import Config
from agent.brain import AttendanceAgent

logger = logging.getLogger(__name__)

TICK_INTERVAL = 60


class AttendanceScheduler:

    def __init__(self, config: Config, bot):
        self.config = config
        self.bot = bot
        self.agent = AttendanceAgent(config)

    async def run(self):
        logger.info("Scheduler started. Tick interval: 60s")

        while True:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Scheduler tick error: {e}", exc_info=True)

            await asyncio.sleep(TICK_INTERVAL)

    async def _tick(self):
        actions = self.agent.tick()

        for action in actions:
            atype = action["type"]

            if atype == "class_reminder":
                cls = action["class"]

                msg = (
                    f"Class Reminder\n\n"
                    f"{cls.name} starts in {cls.remind_minutes} minutes.\n"
                    f"Time: {cls.time}"
                )

                await self.bot.send(msg)
                logger.info(f"Sent class reminder: {cls.name}")

            elif atype == "ucheck_reminder":
                cls = action["class"]

                msg = (
                    f"Health Check Reminder\n\n"
                    f"Please complete your health check before {cls.name}.\n\n"
                    f"Class starts in 5 minutes.\n\n"
                    f"Reply with /ucheck_done when completed."
                )

                await self.bot.send(msg)
                logger.info(f"Sent uCheck reminder for {cls.name}")

            elif atype == "ucheck_retry":
                cls = action["class"]
                attempt = action["attempt"]

                retry_lines = [
                    f"Health check for {cls.name} is still pending.",
                    f"Second reminder: health check for {cls.name} is still pending.",
                    f"Final reminder: submit your health check for {cls.name}."
                ]

                line = retry_lines[min(attempt - 1, 2)]

                msg = (
                    f"Health Check Reminder (Attempt {attempt})\n\n"
                    f"{line}\n\n"
                    f"Reply with /ucheck_done when completed."
                )

                await self.bot.send(msg)
                logger.info(f"Sent uCheck retry #{attempt} for {cls.name}")

            elif atype == "deadline_reminder":
                deadline = action["deadline"]
                days_left = action["days_left"]

                if days_left == 1:
                    priority = "High Priority"
                elif days_left <= 3:
                    priority = "Upcoming Deadline"
                else:
                    priority = "Reminder"

                day_word = (
                    "tomorrow"
                    if days_left == 1
                    else f"in {days_left} days"
                )

                msg = (
                    f"{priority}\n\n"
                    f"{deadline.name} is due {day_word}.\n"
                    f"Due Date: {deadline.day} at {deadline.time}"
                )

                await self.bot.send(msg)

                logger.info(
                    f"Sent deadline reminder: "
                    f"{deadline.name} ({days_left}d away)"
                )

    async def send_daily_summary(self):
        summary = self.agent.daily_summary()
        await self.bot.send(summary)

    def confirm_ucheck(self):
        self.agent.confirm_ucheck()
