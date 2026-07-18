"""Lightweight Pendo server-side track event client."""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_logger = logging.getLogger("app.pendo")

_PENDO_TRACK_URL = "https://data.pendo.io/data/track"
_PENDO_INTEGRATION_KEY = "c506e110-5374-4df7-8ec2-9b94a22b438f"


def track(
    event: str,
    *,
    visitor_id: str = "system",
    account_id: str = "system",
    properties: dict[str, Any] | None = None,
) -> None:
    """Send a track event to the Pendo server-side API.

    Failures are logged and never propagated to the caller.
    """

    payload: dict[str, Any] = {
        "type": "track",
        "event": event,
        "visitorId": visitor_id,
        "accountId": account_id,
        "timestamp": int(time.time() * 1000),
        "properties": properties or {},
    }
    try:
        request = Request(
            _PENDO_TRACK_URL,
            data=json.dumps(payload, default=str).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-pendo-integration-key": _PENDO_INTEGRATION_KEY,
            },
            method="POST",
        )
        with urlopen(request, timeout=5):  # noqa: S310
            pass
    except (HTTPError, URLError, OSError) as error:
        _logger.warning("pendo track failed for %s: %s", event, error)
