"""Circuit breaker pattern for resilient external service calls."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(StrEnum):
    """Possible states for a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Protect external calls with a circuit breaker that trips after repeated failures."""

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _half_open_calls: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute ``func`` through the circuit breaker."""

        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info("Circuit breaker %s moved to half-open", self.name)
                else:
                    raise CircuitOpenError(
                        f"Circuit breaker {self.name} is open. "
                        f"Retry after {self.recovery_timeout - (time.monotonic() - self._last_failure_time):.1f}s"
                    )
            if self._state == CircuitState.HALF_OPEN and self._half_open_calls >= self.half_open_max_calls:
                raise CircuitOpenError(f"Circuit breaker {self.name} is half-open and saturated.")

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

        try:
            result = func(*args, **kwargs)
        except Exception as error:
            self._record_failure()
            raise
        else:
            self._record_success()
            return result

    def _record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker %s opened after %d failures",
                    self.name,
                    self._failure_count,
                )

    def _record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._half_open_calls = 0
                logger.info("Circuit breaker %s closed after successful probe", self.name)
            elif self._state == CircuitState.CLOSED:
                self._failure_count = max(0, self._failure_count - 1)


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is open."""
