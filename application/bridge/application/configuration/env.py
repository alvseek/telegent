"""Configuration: load and validate environment for the Telegram bridge.

The bridge holds only what it needs to (a) talk to Telegram and (b) reach the
brain over HTTP. It has NO model config and NO database — the brain owns those.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_BRAIN_URL = "http://localhost:8000"


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    brain_url: str       # base URL of universal-chat-agent, e.g. http://localhost:8000
    brain_timeout: float  # seconds to wait for a brain reply (LLM calls are slow)


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


def load_config() -> Config:
    return Config(
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        brain_url=os.getenv("BRAIN_URL", DEFAULT_BRAIN_URL).strip() or DEFAULT_BRAIN_URL,
        brain_timeout=_float("BRAIN_TIMEOUT", 60.0),
    )
