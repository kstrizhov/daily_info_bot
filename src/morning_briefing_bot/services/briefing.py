from __future__ import annotations

import asyncio
import html
import logging

from morning_briefing_bot.config import Settings
from morning_briefing_bot.models import MetricDetail, MetricSnapshot
from morning_briefing_bot.services.fred import FredSeriesService
from morning_briefing_bot.services.fx import ForexService
from morning_briefing_bot.services.weather import WeatherService

LOGGER = logging.getLogger(__name__)


class BriefingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.weather = WeatherService(settings)
        self.forex = ForexService(settings)
        self.metrics = {
            "weather": self.weather,
            "fx": self.forex,
            "oil": FredSeriesService(
                settings,
                metric_key="oil",
                label=settings.oil_label,
                series_id=settings.oil_series_id,
                formatter=_format_usd_price,
                y_label="USD",
            ),
            "stock": FredSeriesService(
                settings,
                metric_key="stock",
                label=settings.stock_label,
                series_id=settings.stock_series_id,
                formatter=_format_index_value,
                y_label="Index points",
            ),
            "extra": FredSeriesService(
                settings,
                metric_key="extra",
                label=settings.extra_label,
                series_id=settings.extra_series_id,
                formatter=_formatter_for(settings.extra_format),
                y_label=_y_label_for_format(settings.extra_format),
            ),
        }
        self.chart_labels = {
            "weather": "Temperature (C)",
            "fx": f"{self.settings.fx_quote} per {self.settings.fx_base}",
            "oil": "USD",
            "stock": "Index points",
            "extra": _y_label_for_format(settings.extra_format),
        }

    async def get_briefing(self) -> list[MetricSnapshot]:
        metric_keys = list(self.metrics)
        tasks = [self.metrics[key].snapshot() for key in metric_keys]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        snapshots: list[MetricSnapshot] = []
        for metric_key, result in zip(metric_keys, results, strict=False):
            if isinstance(result, Exception):
                LOGGER.warning("Failed to fetch %s snapshot: %s", metric_key, result)
                snapshots.append(self._unavailable_snapshot(metric_key))
                continue
            snapshots.append(result)

        return snapshots

    async def get_detail(self, metric_key: str, period_label: str) -> MetricDetail:
        service = self.metrics[metric_key]
        return await service.detail(period_label)

    def render_briefing_message(self, snapshots: list[MetricSnapshot]) -> str:
        lines = ["<b>Morning briefing</b>", ""]
        for snapshot in snapshots:
            lines.append(
                f"<b>{html.escape(snapshot.label)}</b>: "
                f"{html.escape(snapshot.summary_text)} "
                f"(<i>{html.escape(snapshot.as_of_text)}</i>)"
            )
        return "\n".join(lines)

    def render_detail_caption(self, detail: MetricDetail) -> str:
        change_text = _describe_change(detail.history)
        return (
            f"<b>{html.escape(detail.label)}</b>\n"
            f"{html.escape(detail.summary_text)}\n"
            f"Latest: {html.escape(detail.value_text)}\n"
            f"Change: {html.escape(change_text)}\n"
            f"As of: <i>{html.escape(detail.as_of_text)}</i>\n"
            f"Source: {html.escape(detail.source_name)}"
        )

    def chart_y_label(self, metric_key: str) -> str:
        return self.chart_labels.get(metric_key, "Value")

    def _unavailable_snapshot(self, metric_key: str) -> MetricSnapshot:
        return MetricSnapshot(
            key=metric_key,
            label=self._metric_label(metric_key),
            value_text="Unavailable",
            summary_text="Unavailable; check logs",
            as_of_text="n/a",
            source_name="Error",
        )

    def _metric_label(self, metric_key: str) -> str:
        labels = {
            "weather": f"Weather, {self.settings.city_name}",
            "fx": f"{self.settings.fx_base}/{self.settings.fx_quote}",
            "oil": self.settings.oil_label,
            "stock": self.settings.stock_label,
            "extra": self.settings.extra_label,
        }
        return labels.get(metric_key, metric_key)


def _format_usd_price(value: float) -> str:
    return f"${value:,.2f}"


def _format_index_value(value: float) -> str:
    return f"{value:,.2f}"


def _format_percent(value: float) -> str:
    return f"{value:.2f}%"


def _formatter_for(format_name: str):
    if format_name == "percent":
        return _format_percent
    if format_name == "index":
        return _format_index_value
    return _format_usd_price


def _y_label_for_format(format_name: str) -> str:
    if format_name == "percent":
        return "Percent"
    if format_name == "index":
        return "Index points"
    return "USD"


def _describe_change(points: list) -> str:
    if len(points) < 2:
        return "n/a"
    start = points[0].value
    end = points[-1].value
    delta = end - start
    if start == 0:
        return f"{delta:+.2f}"
    pct = (delta / start) * 100
    return f"{delta:+.2f} ({pct:+.2f}%)"
