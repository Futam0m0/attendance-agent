"""
Telegram Bot -- Mei Ling codec interface for Snake.

Commands:
  /start        -- codec connection established
  /today        -- today's mission briefing
  /ucheck_done  -- confirm health check complete
  /deadlines    -- upcoming mission objectives
  /summary      -- daily debrief
  /status       -- agent status report
  /reload       -- reload schedule from HQ
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
            "📡 *CODEC CONNECTION ESTABLISHED*\n"
            "_Frequency 140.96_\n\n"
            "Snake, this is Mei Ling at HQ! 👩‍💻\n"
            "I'll be monitoring your schedule and keeping you on track.\n"
            "_\"The most important battles are the ones fought every day.\"_\n\n"
            "Available commands:\n"
            "/today — today's mission briefing\n"
            "/deadlines — upcoming objectives\n"
            "/ucheck\\_done — confirm health check\n"
            "/summary — daily debrief\n"
            "/status — system status\n"
            "/reload — sync schedule from HQ",
            parse_mode="Markdown"
        )

    async def _cmd_today(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._scheduler:
            await update.message.reply_text(
                "📡 _HQ is not online yet, Snake. Stand by..._"
            )
            return
        classes = self._scheduler.agent.get_todays_classes()
        if not classes:
            await update.message.reply_text(
                "📡 *MEI LING*\n\n"
                "No missions scheduled today, Snake! 🎉\n"
                "_\"Even the greatest soldiers need rest.\"_\n"
                "Enjoy your downtime.",
                parse_mode="Markdown"
            )
            return
        lines = ["📡 *TODAY'S MISSION BRIEFING*\n"]
        for c in classes:
            lines.append(f"🎯 *{c.name}* — `{c.time}` _(reminder {c.remind_minutes}min prior)_")
        lines.append("\n_Stay sharp, Snake._")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def _cmd_ucheck_done(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if self._scheduler:
            self._scheduler.confirm_ucheck()
        await update.message.reply_text(
            "📡 *MEI LING*\n\n"
            "✅ Health check confirmed, Snake!\n"
            "_\"Taking care of yourself is part of the mission.\"_\n"
            "Good work. I'll stop bugging you about it. 😄",
            parse_mode="Markdown"
        )

    async def _cmd_summary(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if self._scheduler:
            await self._scheduler.send_daily_summary()
        else:
            await update.message.reply_text(
                "📡 _HQ not ready yet, Snake. Try again in a moment._"
            )

    async def _cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._scheduler:
            await update.message.reply_text(
                "📡 _Systems still booting up, Snake. Stand by._"
            )
            return
        agent = self._scheduler.agent
        ucheck_status = "✅ Confirmed" if agent._ucheck_done else f"⏳ Pending _(retries: {agent._ucheck_retries})_"
        msg = (
            f"📡 *SYSTEM STATUS REPORT*\n"
            f"_Mei Ling reporting in_\n\n"
            f"🕐 Local time: `{agent.now().strftime('%H:%M')} {agent.config.timezone}`\n"
            f"🩺 uCheck: {ucheck_status}\n"
            f"🔔 Reminders sent today: {len(agent._sent_reminders)}\n"
            f"🎯 Missions today: {len(agent.get_todays_classes())}\n\n"
            f"_All systems operational, Snake._"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _cmd_deadlines(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._scheduler:
            await update.message.reply_text(
                "📡 _HQ not ready yet, Snake. Stand by._"
            )
            return
        upcoming = self._scheduler.agent.get_upcoming_deadlines()
        if not upcoming:
            await update.message.reply_text(
                "📡 *MEI LING*\n\n"
                "No upcoming submissions in the database, Snake.\n"
                "_\"A quiet battlefield is still a battlefield.\"_",
                parse_mode="Markdown"
            )
            return
        lines = ["📡 *UPCOMING MISSION OBJECTIVES*\n"]
        for deadline, days_left in upcoming:
            urgency = "🔴" if days_left <= 1 else "🟡" if days_left <= 3 else "🟢"
            day_word = "tomorrow" if days_left == 1 else f"in {days_left} days"
            lines.append(
                f"{urgency} *{deadline.name}*\n"
                f"   📅 Due: {deadline.day} @ `{deadline.time}` _({day_word})_"
            )
        lines.append("\n_Don't let HQ down, Snake._")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def _cmd_reload(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._scheduler:
            await update.message.reply_text(
                "📡 _HQ not ready yet, Snake. Stand by._"
            )
            return
        try:
            from config.settings import load_config
            new_config = load_config()
            self._scheduler.agent.config = new_config
            classes = len(new_config.schedule)
            deadlines = len(new_config.deadlines)
            await update.message.reply_text(
                f"📡 *MEI LING*\n\n"
                f"🔄 Schedule synced from HQ, Snake!\n\n"
                f"🎯 Missions loaded: {classes}\n"
                f"📝 Objectives loaded: {deadlines}\n\n"
                f"_\"New intel received. Stay adaptable.\"_",
                parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(
                f"📡 *MEI LING*\n\n"
                f"❌ Sync failed, Snake: {str(e)}\n\n"
                f"_Check your schedule.json for errors._",
                parse_mode="Markdown"
            )

    # Sending

    async def send(self, text: str):
        await self._app.bot.send_message(
            chat_id=self.chat_id,
            text=text,
            parse_mode="Markdown"
        )

    async def run(self):
        logger.info("Codec online. Mei Ling standing by...")
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()
        logger.info("Telegram bot polling.")
        await asyncio.Event().wait()

    async def stop(self):
        await self._app.updater.stop()
        await self._app.stop()

