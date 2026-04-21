from __future__ import annotations

from datetime import date, datetime, timedelta

import httpx

from morning_briefing_bot.config import Settings
from morning_briefing_bot.models import DataPoint, MetricDetail, MetricSnapshot


class ForexService:
    BASE_URL = "https://api.frankfurter.dev/v2"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def snapshot(self) -> MetricSnapshot:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/rate/{self.settings.fx_base}/{self.settings.fx_quote}"
            )
            _raise_for_frankfurter_error(response, self.settings.fx_base, self.settings.fx_quote)
            payload = response.json()

        rate = float(payload["rate"])
        as_of = payload["date"]

        return MetricSnapshot(
            key="fx",
            label=f"{self.settings.fx_base}/{self.settings.fx_quote}",
            value_text=f"{rate:.4f}",
            summary_text=f"1 {self.settings.fx_base} = {rate:.4f} {self.settings.fx_quote}",
            as_of_text=as_of,
            source_name="Frankfurter",
        )

    async def detail(self, period_label: str) -> MetricDetail:
        days = _period_to_days(period_label)
        end_day = date.today()
        start_day = end_day - timedelta(days=days)

        params = {
            "base": self.settings.fx_base,
            "quotes": self.settings.fx_quote,
            "from": start_day.isoformat(),
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{self.BASE_URL}/rates", params=params)
            _raise_for_frankfurter_error(response, self.settings.fx_base, self.settings.fx_quote)
            payload = response.json()

        points = _points_from_v2_rates(payload, self.settings.fx_base, self.settings.fx_quote)
        latest = points[-1]

        return MetricDetail(
            key="fx",
            label=f"{self.settings.fx_base}/{self.settings.fx_quote}",
            value_text=f"{latest.value:.4f}",
            summary_text=f"Exchange rate over the last {period_label}",
            as_of_text=latest.day.isoformat(),
            source_name="Frankfurter",
            period_label=period_label,
            history=points,
        )


def _period_to_days(period_label: str) -> int:
    mapping = {"1M": 30, "3M": 90, "1Y": 365}
    return mapping.get(period_label, 30)


def _points_from_v2_rates(
    payload: dict[str, object] | list[dict[str, object]],
    base_currency: str,
    quote_currency: str,
) -> list[DataPoint]:
    records = payload["value"] if isinstance(payload, dict) else payload

    points = [
        DataPoint(
            day=datetime.strptime(str(record["date"]), "%Y-%m-%d").date(),
            value=float(record["rate"]),
        )
        for record in records
        if record.get("base") == base_currency and record.get("quote") == quote_currency
    ]

    if not points:
        raise ValueError(f"No Frankfurter rates returned for {base_currency}/{quote_currency}.")

    return sorted(points, key=lambda point: point.day)


def _raise_for_frankfurter_error(
    response: httpx.Response,
    base_currency: str,
    quote_currency: str,
) -> None:
    if response.is_success:
        return

    raise RuntimeError(
        f"Frankfurter request failed for {base_currency}/{quote_currency} "
        f"with HTTP {response.status_code}: {_response_error_detail(response)}"
    ) from None


def _response_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:300]

    message = payload.get("message") or payload.get("error") or response.text
    return str(message)[:300]
