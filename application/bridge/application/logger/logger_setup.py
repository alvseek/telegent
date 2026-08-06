"""Observability + token safety: logging setup for the bridge.

CRITICAL: Telegram API URLs embed the bot token, and the HTTP client logs full
URLs at INFO. We silence httpx/httpcore to WARNING so the token is never written
to logs. (The bridge is the only side holding the Telegram token.)
"""
from __future__ import annotations

import logging


def configure(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
