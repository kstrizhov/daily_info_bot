from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable

import httpx

from morning_briefing_bot.config import Settings
from morning_briefing_bot.models import DataPoint, MetricDetail, MetricSnapshot


class FredSeriesService:
    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(
        self,
        settings: Settings,
        *,
        metric_key: str,
        label: str,
        series_id: str,
        formatter: Callable[[float], str],
        y_label: str,
    ) -> None:
        self.settings = settings
        self.metric_key = metric_key
        self.label = label
        self.series_id = series_id
        self.formatter = formatter
        self.y_label = y_label

    async def snapshot(self) -> MetricSnapshot:
        end_day = date.today()
        start_day = end_day - timedelta(days=45)

        params = {
            "series_id": self.series_id,
            "api_key": self.settings.fred_api_key,
            "file_type": "json",
            "observation_start": start_day.isoformat(),
            "observation_end": end_day.isoformat(),
            "sort_order": "desc",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            _raise_for_fred_error(response, self.series_id, self.settings.fred_api_key)
            payload = response.json()

        latest = _latest_point(payload["observations"])

        return MetricSnapshot(
            key=self.metric_key,
            label=self.label,
            value_text=self.formatter(latest.value),
            summary_text=self.formatter(latest.value),
            as_of_text=latest.day.isoformat(),
            source_name="FRED",
        )

    async def detail(self, period_label: str) -> MetricDetail:
        days = _period_to_days(period_label)
        end_day = date.today()
        start_day = end_day - timedelta(days=days)

        params = {
            "series_id": self.series_id,
            "api_key": self.settings.fred_api_key,
            "file_type": "json",
            "observation_start": start_day.isoformat(),
            "observation_end": end_day.isoformat(),
            "sort_order": "asc",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            _raise_for_fred_error(response, self.series_id, self.settings.fred_api_key)
            payload = response.json()

        points = _points_from_observations(payload["observations"])
        latest = points[-1]

        return MetricDetail(
            key=self.metric_key,
            label=self.label,
            value_text=self.formatter(latest.value),
            summary_text=f"{self.label} over the last {period_label}",
            as_of_text=latest.day.isoformat(),
            source_name="FRED",
            period_label=period_label,
            history=points,
        )


def _points_from_observations(observations: list[dict[str, str]]) -> list[DataPoint]:
    points: list[DataPoint] = []
    for observation in observations:
        value_text = observation["value"]
        if value_text == ".":
            continue
        points.append(
            DataPoint(
                day=datetime.strptime(observation["date"], "%Y-%m-%d").date(),
                value=float(value_text),
            )
        )
    if not points:
        raise ValueError("No FRED observations returned for the selected period.")
    return points


def _latest_point(observations: list[dict[str, str]]) -> DataPoint:
    return _points_from_observations(observations)[0]


def _period_to_days(period_label: str) -> int:
    mapping = {"1M": 30, "3M": 90, "1Y": 365}
    return mapping.get(period_label, 30)


def _raise_for_fred_error(response: httpx.Response, series_id: str, api_key: str) -> None:
    if response.is_success:
        return

    detail = _response_error_detail(response).replace(api_key, "***")
    raise RuntimeError(
        f"FRED request failed for series {series_id} with HTTP {response.status_code}: {detail}"
    ) from None


def _response_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:300]

    message = payload.get("error_message") or payload.get("message") or response.text
    return str(message)[:300]
