from __future__ import annotations

from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from morning_briefing_bot.models import DataPoint


def render_timeseries_png(title: str, y_label: str, points: list[DataPoint]) -> BytesIO:
    if not points:
        raise ValueError("Cannot render a chart without data points.")

    dates = [point.day for point in points]
    values = [point.value for point in points]

    figure, axis = plt.subplots(figsize=(10, 5))
    axis.plot(dates, values, color="#1768AC", linewidth=2.2)
    axis.fill_between(dates, values, color="#B7D3F2", alpha=0.4)
    axis.set_title(title)
    axis.set_ylabel(y_label)
    axis.grid(alpha=0.25)
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    figure.autofmt_xdate()
    figure.tight_layout()

    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=160)
    plt.close(figure)
    buffer.seek(0)
    return buffer
