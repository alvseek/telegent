"""Pure helper: split a reply into Telegram-sized pieces.

Telegram rejects messages longer than 4096 characters, so a long brain reply
must be sent as several messages. Pure function — no I/O, unit-tested.
"""
from __future__ import annotations

from typing import List

TELEGRAM_MAX = 4096  # Telegram's hard per-message character limit


def chunk(text: str, size: int = TELEGRAM_MAX) -> List[str]:
    """Split ``text`` into pieces of at most ``size`` chars (never empty)."""
    text = text or "(empty reply)"
    return [text[i : i + size] for i in range(0, len(text), size)]
