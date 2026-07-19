"""Health check utilities for operational readiness."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Callable


class HealthStatus(StrEnum):
    """Overall health outcomes."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class ComponentHealth:
    """Readiness of a single dependency or subsystem."""

    name: str
    status: HealthStatus
    message: str
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    latency_ms: float | None = None


@dataclass
class HealthCheck:
    """Aggregate health checks for the application and its dependencies."""

    _checks: dict[str, Callable[[], ComponentHealth]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def register(self, name: str, check: Callable[[], ComponentHealth]) -> None:
        """Register a named health check."""

        with self._lock:
            self._checks[name] = check

    def check(self) -> dict[str, Any]:
        """Run all registered checks and return the aggregate health."""

        components: dict[str, ComponentHealth] = {}
        with self._lock:
            for name, check in list(self._checks.items()):
                try:
                    components[name] = check()
                except Exception as error:  # noqa: BLE001
                    components[name] = ComponentHealth(
                        name=name,
                        status=HealthStatus.UNHEALTHY,
                        message=str(error),
                    )

        statuses = [c.status for c in components.values()]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return {
            "status": overall.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                name: {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "checked_at": c.checked_at,
                    "latency_ms": c.latency_ms,
                }
                for name, c in components.items()
            },
        }
