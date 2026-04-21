from __future__ import annotations

import logging
from datetime import time
from zoneinfo import ZoneInfo

from telegram import BotCommand, InputFile, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from morning_briefing_bot.charts import render_timeseries_png
from morning_briefing_bot.config import Settings
from morning_briefing_bot.keyboards import briefing_keyboard, detail_keyboard
from morning_briefing_bot.services.briefing import BriefingService

LOGGER = logging.getLogger(__name__)


def build_application(settings: Settings) -> Application:
    briefing_service = BriefingService(settings)
    application = ApplicationBuilder().token(settings.bot_token).post_init(post_startup).build()

    application.bot_data["settings"] = settings
    application.bot_data["briefing_service"] = briefing_service

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("briefing", briefing_command))
    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_error_handler(error_handler)

    if application.job_queue and settings.default_chat_id is not None:
        application.job_queue.run_daily(
            send_daily_briefing,
            time=_scheduled_time(settings),
            data={"chat_id": settings.default_chat_id},
            name="daily-briefing",
        )

    return application


async def post_startup(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Show bot help"),
            BotCommand("briefing", "Send the current morning briefing"),
        ]
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    message = (
        "<b>Morning Briefing Bot</b>\n"
        "Use /briefing to get the latest weather and market snapshot.\n"
        "Use the inline buttons to open details and charts for 1M, 3M, or 1Y."
    )
    await update.effective_message.reply_text(message, parse_mode=ParseMode.HTML)


async def briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    service = _get_service(context)
    snapshots = await service.get_briefing()
    message = service.render_briefing_message(snapshots)
    await update.effective_message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        reply_markup=briefing_keyboard(),
    )


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None or query.message is None:
        return

    await query.answer()

    parts = query.data.split("|")
    action = parts[0]

    if action == "refresh":
        service = _get_service(context)
        snapshots = await service.get_briefing()
        message = service.render_briefing_message(snapshots)
        await query.message.reply_text(
            message,
            parse_mode=ParseMode.HTML,
            reply_markup=briefing_keyboard(),
        )
        return

    if action != "detail" or len(parts) != 3:
        return

    metric_key = parts[1]
    period_label = parts[2]

    service = _get_service(context)
    detail = await service.get_detail(metric_key, period_label)
    chart = render_timeseries_png(
        title=f"{detail.label} - {detail.period_label}",
        y_label=service.chart_y_label(metric_key),
        points=detail.history,
    )

    await query.message.reply_photo(
        photo=InputFile(chart, filename=f"{metric_key.lower()}_{period_label.lower()}.png"),
        caption=service.render_detail_caption(detail),
        parse_mode=ParseMode.HTML,
        reply_markup=detail_keyboard(metric_key),
    )


async def send_daily_briefing(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.data["chat_id"]
    service = _get_service(context)
    snapshots = await service.get_briefing()
    message = service.render_briefing_message(snapshots)
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode=ParseMode.HTML,
        reply_markup=briefing_keyboard(),
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    LOGGER.exception("Unhandled exception while processing an update", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message is not None:
        await update.effective_message.reply_text(
            "The bot could not fetch data right now. Check your API settings and try again in a moment."
        )


def _scheduled_time(settings: Settings) -> time:
    return settings.daily_time.replace(tzinfo=ZoneInfo(settings.timezone))


def _get_service(context: ContextTypes.DEFAULT_TYPE) -> BriefingService:
    return context.application.bot_data["briefing_service"]
