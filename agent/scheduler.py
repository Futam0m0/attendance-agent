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
                    f"📡 *CODEC INCOMING — MEI LING*\n\n"
                    f"Snake! *{cls.name}* begins in {cls.remind_minutes} minutes!\n"
                    f"⏰ Rendezvous time: `{cls.time}`\n\n"
                    f"_\"A strong man doesn't need to read the future. "
                    f"He makes his own.\"_ Now move out! 🐍"
                )
                await self.bot.send(msg)
                logger.info(f"Sent class reminder: {cls.name}")

            elif atype == "ucheck_reminder":
                cls = action["class"]
                msg = (
                    f"📡 *CODEC INCOMING — MEI LING*\n\n"
                    f"Snake, uCheck required before *{cls.name}*!\n\n"
                    f"Open the uCheck app and submit your status now.\n"
                    f"Class starts in 5 minutes — don't miss it! 🛰️\n\n"
                    f"_\"The wisest thing to do is to act on the information "
                    f"you have right now.\"_\n\n"
                    f"Reply /ucheck\\_done when finished ✅"
                )
                await self.bot.send(msg)
                logger.info(f"Sent uCheck reminder for {cls.name}")

            elif atype == "ucheck_retry":
                cls = action["class"]
                attempt = action["attempt"]
                urgency_lines = [
                    f"Snake, you still haven't submitted uCheck for *{cls.name}*. Don't make me worry! 😤",
                    f"Snake! Second reminder — uCheck for *{cls.name}* is still pending. Get it done! 📢",
                    f"SNAKE! Final warning. Submit uCheck for *{cls.name}* immediately! 🚨"
                ]
                line = urgency_lines[min(attempt - 1, 2)]
                msg = (
                    f"📡 *CODEC — MEI LING* _(attempt {attempt})_\n\n"
                    f"{line}\n\n"
                    f"Reply /ucheck\\_done when finished ✅"
                )
                await self.bot.send(msg)
                logger.info(f"Sent uCheck retry #{attempt} for {cls.name}")

            elif atype == "deadline_reminder":
                deadline = action["deadline"]
                days_left = action["days_left"]
                if days_left == 1:
                    urgency = "🔴 CRITICAL MISSION"
                    closing = "_\"There's no such thing as luck on the battlefield.\"_ Submit today, Snake!"
                elif days_left <= 3:
                    urgency = "🟡 MISSION BRIEFING"
                    closing = "_\"The trick to staying alive is knowing when to act.\"_ Don't wait too long!"
                else:
                    urgency = "🟢 INTEL RECEIVED"
                    closing = "_\"Prepare yourself, Snake. A good soldier always plans ahead.\"_"
                day_word = "tomorrow" if days_left == 1 else f"in {days_left} days"
                msg = (
                    f"📡 *CODEC INCOMING — MEI LING*\n"
                    f"_{urgency}_\n\n"
                    f"Snake! *{deadline.name}* is due {day_word}.\n"
                    f"📅 Deadline: {deadline.day} at `{deadline.time}`\n\n"
                    f"{closing}"
                )
                await self.bot.send(msg)
                logger.info(f"Sent deadline reminder: {deadline.name} ({days_left}d away)")

    async def send_daily_summary(self):
        summary = self.agent.daily_summary()
        await self.bot.send(summary)

    def confirm_ucheck(self):
        self.agent.confirm_ucheck()
