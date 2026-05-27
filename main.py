"""
Smart Attendance & Health Check Agent
Entry point — starts the scheduler and Telegram bot concurrently.
"""

import asyncio
import logging
from agent.scheduler import AttendanceScheduler
from agent.bot import TelegramBot
from config.settings import load_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    config = load_config()
    logger.info("Starting Attendance Agent...")

    bot = TelegramBot(config)
    scheduler = AttendanceScheduler(config, bot)

    # Wire them together so bot can talk to scheduler
    bot.set_scheduler(scheduler)

    # Run both concurrently
    await asyncio.gather(
        bot.run(),
        scheduler.run()
    )


if __name__ == "__main__":
    asyncio.run(main())
