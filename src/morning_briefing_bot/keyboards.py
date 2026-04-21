from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


PERIODS = ("1M", "3M", "1Y")


def briefing_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Weather details", callback_data="detail|weather|1M"),
                InlineKeyboardButton("FX details", callback_data="detail|fx|1M"),
            ],
            [
                InlineKeyboardButton("Oil details", callback_data="detail|oil|1M"),
                InlineKeyboardButton("Index details", callback_data="detail|stock|1M"),
            ],
            [
                InlineKeyboardButton("Extra details", callback_data="detail|extra|1M"),
                InlineKeyboardButton("Refresh", callback_data="refresh|briefing"),
            ],
        ]
    )


def detail_keyboard(metric_key: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(period, callback_data=f"detail|{metric_key}|{period}") for period in PERIODS]]
    rows.append([InlineKeyboardButton("Back to briefing", callback_data="refresh|briefing")])
    return InlineKeyboardMarkup(rows)
