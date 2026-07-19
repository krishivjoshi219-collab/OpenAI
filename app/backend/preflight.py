"""Asynchronous pre-flight health checks for external dependencies."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class PreflightResult:
    """Outcome of one pre-flight dependency check."""

    name: str
    ok: bool
    latency_ms: float
    error: str | None = None
    status_code: int | None = None


async def _check_openai(
    api_key: str | None,
    model: str,
    timeout: float,
) -> PreflightResult:
    """Verify OpenAI API connectivity with a lightweight model lookup."""

    if not api_key:
        return PreflightResult("openai", False, 0.0, "missing_api_key")

    def _sync() -> PreflightResult:
        start = time.perf_counter()
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, timeout=timeout)
            client.models.retrieve(model)
            latency = (time.perf_counter() - start) * 1000
            return PreflightResult("openai", True, latency)
        except Exception as exc:  # noqa: BLE001
            latency = (time.perf_counter() - start) * 1000
            error_str = str(exc)
            status = None
            if "429" in error_str:
                status = 429
            elif "401" in error_str:
                status = 401
            return PreflightResult("openai", False, latency, error_str, status)

    return await asyncio.to_thread(_sync)


async def _check_telegram(
    bot_token: str | None,
    timeout: float,
) -> PreflightResult:
    """Verify Telegram Bot API connectivity with getMe."""

    if not bot_token:
        return PreflightResult("telegram", False, 0.0, "missing_token")

    def _sync() -> PreflightResult:
        start = time.perf_counter()
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            req = Request(url, method="GET")
            with urlopen(req, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                latency = (time.perf_counter() - start) * 1000
                if body.get("ok"):
                    return PreflightResult("telegram", True, latency)
                return PreflightResult("telegram", False, latency, str(body))
        except HTTPError as exc:
            latency = (time.perf_counter() - start) * 1000
            return PreflightResult("telegram", False, latency, str(exc), exc.code)
        except Exception as exc:  # noqa: BLE001
            latency = (time.perf_counter() - start) * 1000
            return PreflightResult("telegram", False, latency, str(exc))

    return await asyncio.to_thread(_sync)


async def _check_odoo(
    url: str | None,
    db: str | None,
    username: str | None,
    password: str | None,
    timeout: float,
) -> PreflightResult:
    """Verify Odoo JSON-RPC connectivity with authenticate."""

    if not all([url, db, username, password]):
        return PreflightResult("odoo", False, 0.0, "missing_credentials")

    def _sync() -> PreflightResult:
        start = time.perf_counter()
        try:
            from app.business.odoo import OdooJsonRpcClient

            client = OdooJsonRpcClient(url, db, username, password)
            client._authenticate()
            latency = (time.perf_counter() - start) * 1000
            return PreflightResult("odoo", True, latency)
        except Exception as exc:  # noqa: BLE001
            latency = (time.perf_counter() - start) * 1000
            error_str = str(exc)
            status = None
            if "401" in error_str or "403" in error_str:
                status = 401
            elif "429" in error_str:
                status = 429
            return PreflightResult("odoo", False, latency, error_str, status)

    return await asyncio.to_thread(_sync)


async def run_preflight_checks(
    settings: Any,
    total_timeout_ms: int = 3000,
) -> dict[str, PreflightResult]:
    """Run all dependency checks in parallel and return their outcomes."""

    timeout = total_timeout_ms / 1000.0
    per_check_timeout = min(timeout / 2, 2.0)

    tasks = [
        _check_openai(
            getattr(settings, "openai_api_key", None),
            getattr(settings, "openai_model", "gpt-4.1-mini"),
            per_check_timeout,
        ),
        _check_telegram(
            getattr(settings, "telegram_bot_token", None),
            per_check_timeout,
        ),
        _check_odoo(
            getattr(settings, "odoo_url", None),
            getattr(settings, "odoo_db", None) or getattr(settings, "odoo_database", None),
            getattr(settings, "odoo_username", None),
            getattr(settings, "odoo_password", None) or getattr(settings, "odoo_api_key", None),
            per_check_timeout,
        ),
    ]

    try:
        raw_results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raw_results = [
            PreflightResult(name, False, timeout * 1000, "preflight_timeout")
            for name in ("openai", "telegram", "odoo")
        ]

    results: dict[str, PreflightResult] = {}
    for item in raw_results:
        if isinstance(item, PreflightResult):
            results[item.name] = item
        elif isinstance(item, BaseException):
            results["unknown"] = PreflightResult(
                "unknown", False, 0.0, str(item)
            )
    return results
