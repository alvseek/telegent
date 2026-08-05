"""Configuration: load and validate environment for telegent.

Single source of settings. Fails fast (with a clear message) when a required
variable is missing, so misconfiguration is obvious at startup rather than at
the first message.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_SYSTEM_PROMPT = (
    "You are telegent, a helpful, friendly assistant on Telegram. "
    "Be concise and clear."
)
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    openrouter_api_key: str
    openrouter_model: str
    openrouter_base_url: str
    memory_window: int
    db_path: str
    system_prompt: str


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in (see README)."
        )
    return value


def load_config() -> Config:
    """Load settings from the environment (.env already applied)."""
    memory_window_raw = os.getenv("MEMORY_WINDOW", "15").strip()
    try:
        memory_window = int(memory_window_raw)
    except ValueError:
        memory_window = 15
    if memory_window < 1:
        memory_window = 15

    return Config(
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        openrouter_api_key=_require("OPENROUTER_API_KEY"),
        openrouter_model=_require("OPENROUTER_MODEL"),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", DEFAULT_BASE_URL).strip()
        or DEFAULT_BASE_URL,
        memory_window=memory_window,
        db_path=os.getenv("DB_PATH", "telegent.db").strip() or "telegent.db",
        system_prompt=os.getenv("SYSTEM_PROMPT", "").strip() or DEFAULT_SYSTEM_PROMPT,
    )
