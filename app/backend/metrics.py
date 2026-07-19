"""Lightweight metrics collection for operational observability."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Counter:
    """An ever-incrementing metric."""

    name: str
    value: int = 0
    labels: dict[str, str] = field(default_factory=dict)

    def inc(self, amount: int = 1) -> None:
        self.value += amount


@dataclass
class Histogram:
    """A distribution of observed values."""

    name: str
    values: list[float] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)

    def observe(self, value: float) -> None:
        self.values.append(value)

    def stats(self) -> dict[str, float]:
        if not self.values:
            return {"count": 0, "sum": 0.0, "min": 0.0, "max": 0.0, "avg": 0.0}
        return {
            "count": len(self.values),
            "sum": sum(self.values),
            "min": min(self.values),
            "max": max(self.values),
            "avg": sum(self.values) / len(self.values),
        }


class MetricsCollector:
    """Thread-safe metrics registry for counters and histograms."""

    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, **labels: str) -> Counter:
        key = self._key(name, labels)
        with self._lock:
            if key not in self._counters:
                self._counters[key] = Counter(name=name, labels=labels)
            return self._counters[key]

    def histogram(self, name: str, **labels: str) -> Histogram:
        key = self._key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = Histogram(name=name, labels=labels)
            return self._histograms[key]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": [
                    {"name": c.name, "value": c.value, "labels": c.labels}
                    for c in self._counters.values()
                ],
                "histograms": [
                    {**h.stats(), "name": h.name, "labels": h.labels}
                    for h in self._histograms.values()
                ],
            }

    @staticmethod
    def _key(name: str, labels: dict[str, str]) -> str:
        sorted_labels = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{sorted_labels}}}"


metrics = MetricsCollector()
