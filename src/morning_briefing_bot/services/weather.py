from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from morning_briefing_bot.config import Settings
from morning_briefing_bot.models import DataPoint, MetricDetail, MetricSnapshot


class WeatherService:
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def snapshot(self) -> MetricSnapshot:
        params = {
            "latitude": self.settings.latitude,
            "longitude": self.settings.longitude,
            "current": "temperature_2m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "forecast_days": 1,
            "timezone": self.settings.timezone,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(self.FORECAST_URL, params=params)
            response.raise_for_status()
            payload = response.json()

        current = payload["current"]["temperature_2m"]
        today = payload["daily"]
        low = today["temperature_2m_min"][0]
        high = today["temperature_2m_max"][0]
        as_of = payload["current"]["time"]

        return MetricSnapshot(
            key="weather",
            label=f"Weather, {self.settings.city_name}",
            value_text=f"{current:.1f} C",
            summary_text=f"Now {current:.1f} C, low {low:.1f} C, high {high:.1f} C",
            as_of_text=as_of,
            source_name="Open-Meteo",
        )

    async def detail(self, period_label: str) -> MetricDetail:
        start_day, end_day = _archive_date_range(period_label, self.settings.timezone)

        params = {
            "latitude": self.settings.latitude,
            "longitude": self.settings.longitude,
            "start_date": start_day.isoformat(),
            "end_date": end_day.isoformat(),
            "daily": "temperature_2m_mean",
            "timezone": self.settings.timezone,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(self.ARCHIVE_URL, params=params)
            _raise_for_open_meteo_error(response)
            payload = response.json()

        days_list = payload["daily"]["time"]
        values = payload["daily"]["temperature_2m_mean"]
        points = [
            DataPoint(day=datetime.strptime(day_text, "%Y-%m-%d").date(), value=float(value))
            for day_text, value in zip(days_list, values, strict=False)
            if value is not None
        ]
        if not points:
            raise ValueError(
                f"No Open-Meteo weather history returned for {start_day} through {end_day}."
            )
        latest = points[-1]

        return MetricDetail(
            key="weather",
            label=f"Weather, {self.settings.city_name}",
            value_text=f"{latest.value:.1f} C",
            summary_text=f"Daily mean temperature across the last {period_label}",
            as_of_text=latest.day.isoformat(),
            source_name="Open-Meteo",
            period_label=period_label,
            history=points,
        )


def _period_to_days(period_label: str) -> int:
    mapping = {"1M": 30, "3M": 90, "1Y": 365}
    return mapping.get(period_label, 30)


def _archive_date_range(period_label: str, timezone_name: str) -> tuple[date, date]:
    days = _period_to_days(period_label)
    today = datetime.now(ZoneInfo(timezone_name)).date()
    end_day = today - timedelta(days=1)
    start_day = end_day - timedelta(days=days)
    return start_day, end_day


def _raise_for_open_meteo_error(response: httpx.Response) -> None:
    if response.is_success:
        return

    raise RuntimeError(
        f"Open-Meteo request failed with HTTP {response.status_code}: "
        f"{_response_error_detail(response)}"
    ) from None


def _response_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:300]

    message = (
        payload.get("reason")
        or payload.get("message")
        or payload.get("error")
        or response.text
    )
    return str(message)[:300]
