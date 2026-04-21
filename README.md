# Morning Briefing Bot

A starter Telegram bot built with `python-telegram-bot` that sends a compact morning briefing and can show detailed charts on demand.

## Features

- `/start` command with a quick intro
- `/briefing` command to fetch the latest snapshot
- Inline buttons for details on:
  - weather
  - forex
  - oil
  - stock index
  - extra macro metric
- PNG chart generation for `1M`, `3M`, and `1Y`
- Optional daily scheduled briefing with `JobQueue`

## Data Sources

- Weather: Open-Meteo
- Forex: Frankfurter
- Oil, stock index, extra metric: FRED

## Setup With Poetry

1. Install dependencies:

   ```bash
   poetry install
   ```

2. Copy `.env.example` to `.env` and fill in:
   - `BOT_TOKEN`
   - `FRED_API_KEY`
   - optionally `DEFAULT_CHAT_ID` for automatic morning delivery

3. Start the bot:

   ```bash
   poetry run python -m morning_briefing_bot.main
   ```

4. If you want to open a Poetry shell instead:

   ```bash
   poetry shell
   python -m morning_briefing_bot.main
   ```

## Notes

- `DEFAULT_CHAT_ID` is optional. If it is empty, the bot still works via commands, but no daily scheduled message is sent.
- FRED data is often delayed and usually reflects the latest available close rather than a live tick.
- The default extra metric is `DGS10` / 10Y Treasury yield. The old FRED gold fixing series are not reliable defaults because FRED has removed those series from the database.
- Open-Meteo and Frankfurter are free and do not require API keys.
