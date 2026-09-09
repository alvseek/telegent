"""Domain rule: which Telegram chats this bot will talk to.

Pure functions, no I/O. The bridge is the only thing standing between a
stranger and the brain, so the decision "is this chat allowed?" is made here,
once, before any network call — and it is testable without Telegram.

An allowlist of ``None`` means *open* (every chat is admitted — the bot's
original behaviour). A non-empty set admits only those chat ids.
"""
from __future__ import annotations

Allowlist = frozenset[int] | None


def parse_allowlist(raw: str | None, name: str = "ALLOWED_CHAT_IDS") -> Allowlist:
    """Turn an allowlist env value into an allowlist.

    Comma-separated integers — Telegram chat ids (negative for groups), or
    WhatsApp sender numbers in international form without a plus. Empty or
    missing means open. Any token that is not an integer raises ``ValueError``
    so a typo fails at startup instead of silently admitting nobody or everybody.

    ``name`` is the variable the value came from, so the error names the setting
    the reader has to go and fix rather than whichever transport happened to be
    written first.
    """
    if raw is None or not raw.strip():
        return None
    ids: set[int] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            ids.add(int(token))
        except ValueError as exc:
            raise ValueError(
                f"{name}: {token!r} is not a chat id (integers, comma-separated)"
            ) from exc
    return frozenset(ids) if ids else None


def is_allowed(chat_id: int, allowlist: Allowlist) -> bool:
    """True when ``chat_id`` may reach the brain under this allowlist."""
    return allowlist is None or chat_id in allowlist
