"""Configuration: load and validate environment for the Telegram bridge.

The bridge holds only what it needs to (a) talk to Telegram and (b) reach the
brain over HTTP. It has NO model config and NO database — the brain owns those.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from application.business_domain.access_policy import Allowlist, parse_allowlist

load_dotenv()

DEFAULT_BRAIN_URL = "http://localhost:8000"


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    brain_url: str       # base URL of universal-chat-agent, e.g. http://localhost:8000
    brain_timeout: float  # seconds to wait for a brain reply (LLM calls are slow)
    # Which agent this bot *is*. One bridge = one bot token = one agent. Absent, the
    # brain answers as its default agent; set, the brain awakens that agent from the
    # memory service and answers as it. This is the roster entry for this bot.
    agent_id: str | None
    # Which chats may talk to this bot. None = open (anyone); a set = only those
    # chat ids, everything else is dropped silently before the brain is called.
    allowed_chat_ids: Allowlist
    # Discard updates Telegram queued while the bridge was down, instead of
    # replaying them on start. On by default: a command sent hours ago should not
    # run the moment the bot comes back.
    drop_pending_updates: bool


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in (see README)."
        )
    return value


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)).strip())
    except ValueError:
        return default


_TRUE = ("1", "true", "yes", "on")
_FALSE = ("0", "false", "no", "off")


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    # A typo must not silently flip a safety setting — fail at startup, by name.
    raise ValueError(f"{name}: {value!r} is not a boolean (use true/false)")


def load_config() -> Config:
    return Config(
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        brain_url=os.getenv("BRAIN_URL", DEFAULT_BRAIN_URL).strip() or DEFAULT_BRAIN_URL,
        brain_timeout=_float("BRAIN_TIMEOUT", 60.0),
        agent_id=os.getenv("AGENT_ID", "").strip() or None,
        allowed_chat_ids=parse_allowlist(os.getenv("ALLOWED_CHAT_IDS")),
        drop_pending_updates=_bool("DROP_PENDING_UPDATES", True),
    )
