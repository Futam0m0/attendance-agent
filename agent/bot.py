"""
Telegram Bot interface

Commands:
  /start        -- connection established
  /today        -- today's schedule
  /ucheck_done  -- confirm check complete
  /deadlines    -- upcoming deadlines
  /summary      -- daily summary
  /status       -- bot status report
  /reload       -- reload schedule
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config.settings import Config

logger = logging.getLogger(__name__)


class TelegramBot:

    def __init__(self, config: Config):
        self.config = config
        self.chat_id = config.chat_id
        self._app = Application.builder().token(config.telegram_token).build()
        self._scheduler = None
        self._register_handlers()

    def set_scheduler(self, scheduler):
        self._scheduler = scheduler

    def _register_handlers(self):
        app = self._app
        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("today", self._cmd_today))
        app.add_handler(CommandHandler("ucheck_done", self._cmd_ucheck_done))
        app.add_handler(CommandHandler("summary", self._cmd_summary))
        app.add_handler(CommandHandler("status", self._cmd_status))
        app.add_handler(CommandHandler("deadlines", self._cmd_deadlines))
        app.add_handler(CommandHandler("reload", self._cmd_reload))

    # Commands

    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Bot connected successfully.\n\n"
            "Available commands:\n"
            "/today - View today's schedule\n"
            "/deadlines - View upcoming deadlines\n"
            "/ucheck_done - Confirm health check\n"
            "/summary - Daily summary\n"
            "/status - System status\n"
            "/reload - Reload schedule"
        )

    async def _cmd_today(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._scheduler:
            await update.message.reply_text(
                "Scheduler is not ready yet."
            )
            return

        classes = self._scheduler.agent.get_todays_classes()

        if not classes:
            await update.message.reply_text(
                "No classes scheduled for today."
            )
            return

        lines = ["Today's Schedule:\n"]

        for c in classes:
            lines.append(
                f"- {c.name} | {c.time} "
                f"(Reminder: {c.remind_minutes} min before)"
            )

        await update.message.reply_text("\n".join(lines))

    async def _cmd_ucheck_done(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if self._scheduler:
            self._scheduler.confirm_ucheck()

        await update.message.reply_text(
            "Health check confirmed."
        )

    async def _cmd_summary(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if self._scheduler:
            await self._scheduler.send_daily_summary()
        else:
            await update.message.reply_text(
                "Scheduler is not ready yet."
            )

    async def _cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._scheduler:
            await update.message.reply_text(
                "System is starting up."
            )
            return

        agent = self._scheduler.agent

        ucheck_status = (
            "Confirmed"
            if agent._ucheck_done
            else f"Pending (Retries: {agent._ucheck_retries})"
        )

        msg = (
            "System Status\n\n"
            f"Time: {agent.now().strftime('%H:%M')} {agent.config.timezone}\n"
            f"Health Check: {ucheck_status}\n"
            f"Reminders Sent: {len(agent._sent_reminders)}\n"
            f"Classes Today: {len(agent.get_todays_classes())}"
        )

        await update.message.reply_text(msg)

    async def _cmd_deadlines(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._scheduler:
            await update.message.reply_text(
                "Scheduler is not ready yet."
            )
            return

        upcoming = self._scheduler.agent.get_upcoming_deadlines()

        if not upcoming:
            await update.message.reply_text(
                "No upcoming deadlines."
            )
            return

        lines = ["Upcoming Deadlines:\n"]

        for deadline, days_left in upcoming:
            if days_left == 1:
                due_text = "Tomorrow"
            else:
                due_text = f"In {days_left} days"

            lines.append(
                f"- {deadline.name}\n"
                f"  Due: {deadline.day} at {deadline.time} ({due_text})"
            )

        await update.message.reply_text("\n".join(lines))

    async def _cmd_reload(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._scheduler:
            await update.message.reply_text(
                "Scheduler is not ready yet."
            )
            return

        try:
            from config.settings import load_config

            new_config = load_config()
            self._scheduler.agent.config = new_config

            classes = len(new_config.schedule)
            deadlines = len(new_config.deadlines)

            await update.message.reply_text(
                "Schedule reloaded successfully.\n\n"
                f"Classes loaded: {classes}\n"
                f"Deadlines loaded: {deadlines}"
            )

        except Exception as e:
            await update.message.reply_text(
                f"Failed to reload schedule:\n{str(e)}"
            )

    # Sending

    async def send(self, text: str):
        await self._app.bot.send_message(
            chat_id=self.chat_id,
            text=text
        )

    async def run(self):
        logger.info("Telegram bot starting...")

        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()

        logger.info("Telegram bot polling.")

        await asyncio.Event().wait()

    async def stop(self):
        await self._app.updater.stop()
        await self._app.stop()
