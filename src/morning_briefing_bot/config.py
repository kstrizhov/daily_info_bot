from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    fred_api_key: str
    timezone: str
    daily_time: time
    default_chat_id: int | None
    city_name: str
    latitude: float
    longitude: float
    fx_base: str
    fx_quote: str
    stock_series_id: str
    stock_label: str
    oil_series_id: str
    oil_label: str
    extra_series_id: str
    extra_label: str
    extra_format: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        bot_token = os.getenv("BOT_TOKEN", "").strip()
        fred_api_key = os.getenv("FRED_API_KEY", "").strip()

        if not bot_token:
            raise ValueError("BOT_TOKEN is required.")

        if not fred_api_key:
            raise ValueError("FRED_API_KEY is required.")

        default_chat_id_raw = os.getenv("DEFAULT_CHAT_ID", "").strip()
        default_chat_id = int(default_chat_id_raw) if default_chat_id_raw else None

        daily_time_raw = os.getenv("DAILY_TIME", "08:00").strip()

        return cls(
            bot_token=bot_token,
            fred_api_key=fred_api_key,
            timezone=os.getenv("TIMEZONE", "Europe/Moscow").strip(),
            daily_time=time.fromisoformat(daily_time_raw),
            default_chat_id=default_chat_id,
            city_name=os.getenv("CITY_NAME", "Moscow").strip(),
            latitude=float(os.getenv("LATITUDE", "55.7558").strip()),
            longitude=float(os.getenv("LONGITUDE", "37.6176").strip()),
            fx_base=os.getenv("FX_BASE", "EUR").strip().upper(),
            fx_quote=os.getenv("FX_QUOTE", "USD").strip().upper(),
            stock_series_id=os.getenv("STOCK_SERIES_ID", "SP500").strip(),
            stock_label=os.getenv("STOCK_LABEL", "S&P 500").strip(),
            oil_series_id=os.getenv("OIL_SERIES_ID", "DCOILBRENTEU").strip(),
            oil_label=os.getenv("OIL_LABEL", "Brent").strip(),
            extra_series_id=os.getenv("EXTRA_SERIES_ID", "DGS10").strip(),
            extra_label=os.getenv("EXTRA_LABEL", "10Y Treasury Yield").strip(),
            extra_format=os.getenv("EXTRA_FORMAT", "percent").strip().lower(),
        )
