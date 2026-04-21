from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class DataPoint:
    day: date
    value: float


@dataclass(frozen=True)
class MetricSnapshot:
    key: str
    label: str
    value_text: str
    summary_text: str
    as_of_text: str
    source_name: str


@dataclass(frozen=True)
class MetricDetail:
    key: str
    label: str
    value_text: str
    summary_text: str
    as_of_text: str
    source_name: str
    period_label: str
    history: list[DataPoint] = field(default_factory=list)
