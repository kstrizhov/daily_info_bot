from __future__ import annotations

import logging

from morning_briefing_bot.bot import build_application
from morning_briefing_bot.config import Settings


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
    )

    settings = Settings.from_env()
    application = build_application(settings)
    application.run_polling()


if __name__ == "__main__":
    main()
