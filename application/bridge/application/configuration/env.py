"""Configuration: load and validate environment for each transport.

The bridge holds only what it needs to (a) talk to a chat platform and (b) reach
the brain over HTTP. It has NO model config and NO database of its own — the
brain owns those. The one exception is the WhatsApp dedupe store, which exists
because Meta retries webhooks and nothing else in the process remembers.

Both transports run as separate processes from the same directory, so they read
the same ``.env`` and each ignores what it does not recognise. That is why the
split is three loaders rather than three files: ``load_shared_config`` for what
every transport needs, and one loader per transport that requires only its own
variables. A WhatsApp process must not refuse to start because a Telegram token
is missing, and the reverse.

Every loader fails at startup, by name. A missing value raises pointing at the
variable and the README; a mistyped boolean raises rather than defaulting,
because a typo must not silently flip a safety setting.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from application.business_domain.access_policy import Allowlist, parse_allowlist

load_dotenv()

DEFAULT_BRAIN_URL = "http://localhost:8000"
DEFAULT_WHATSAPP_HOST = "127.0.0.1"
DEFAULT_WHATSAPP_PORT = 8200
DEFAULT_WHATSAPP_DB = "whatsapp.db"
# Pinned rather than latest: Meta's error responses differ between versions, and
# an endpoint silently moving under us is the kind of drift that surfaces as a
# mystery 400 months later.
DEFAULT_GRAPH_API_VERSION = "v22.0"


@dataclass(frozen=True)
class SharedConfig:
    """What every transport needs regardless of which platform it speaks."""

    brain_url: str        # base URL of universal-chat-agent, e.g. http://localhost:8100
    brain_timeout: float  # seconds to wait for a brain reply (LLM calls are slow)
    # Which agent this bot *is*. One bridge = one bot = one agent. Absent, the
    # brain answers as its default agent; set, the brain awakens that agent from
    # the memory service and answers as it. This is the roster entry for this bot.
    agent_id: str | None


@dataclass(frozen=True)
class TelegramConfig(SharedConfig):
    telegram_bot_token: str
    # Which chats may talk to this bot. None = open (anyone); a set = only those
    # chat ids, everything else is dropped silently before the brain is called.
    allowed_chat_ids: Allowlist
    # Discard updates Telegram queued while the bridge was down, instead of
    # replaying them on start. On by default: a command sent hours ago should not
    # run the moment the bot comes back.
    drop_pending_updates: bool


@dataclass(frozen=True)
class WhatsAppConfig(SharedConfig):
    access_token: str      # permanent system-user token from Meta
    phone_number_id: str   # the sending number's id, used in every Graph API URL
    app_secret: str        # verifies X-Hub-Signature-256 on inbound webhooks
    verify_token: str      # our own string, echoed during Meta's one-time handshake
    # Same meaning as Telegram's: None = open. A WhatsApp id is the sender's phone
    # number in international form without a plus, which parses as an integer.
    allowed_ids: Allowlist
    db_path: str           # SQLite file holding seen wamids, so a retry is not answered twice
    host: str
    port: int
    api_version: str


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


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        # Unlike a timeout, a wrong port fails silently at the wrong layer — the
        # process binds somewhere nobody is proxying to — so refuse it here.
        raise ValueError(f"{name}: {raw!r} is not a port number") from exc


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


def load_shared_config() -> SharedConfig:
    return SharedConfig(
        brain_url=os.getenv("BRAIN_URL", DEFAULT_BRAIN_URL).strip() or DEFAULT_BRAIN_URL,
        brain_timeout=_float("BRAIN_TIMEOUT", 60.0),
        agent_id=os.getenv("AGENT_ID", "").strip() or None,
    )


def load_telegram_config() -> TelegramConfig:
    shared = load_shared_config()
    return TelegramConfig(
        brain_url=shared.brain_url,
        brain_timeout=shared.brain_timeout,
        agent_id=shared.agent_id,
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        allowed_chat_ids=parse_allowlist(os.getenv("ALLOWED_CHAT_IDS")),
        drop_pending_updates=_bool("DROP_PENDING_UPDATES", True),
    )


def load_whatsapp_config() -> WhatsAppConfig:
    shared = load_shared_config()
    return WhatsAppConfig(
        brain_url=shared.brain_url,
        brain_timeout=shared.brain_timeout,
        agent_id=shared.agent_id,
        access_token=_require("WHATSAPP_ACCESS_TOKEN"),
        phone_number_id=_require("WHATSAPP_PHONE_NUMBER_ID"),
        app_secret=_require("WHATSAPP_APP_SECRET"),
        verify_token=_require("WHATSAPP_VERIFY_TOKEN"),
        allowed_ids=parse_allowlist(
            os.getenv("WHATSAPP_ALLOWED_IDS"), name="WHATSAPP_ALLOWED_IDS"
        ),
        db_path=os.getenv("WHATSAPP_DB_PATH", "").strip() or DEFAULT_WHATSAPP_DB,
        host=os.getenv("WHATSAPP_HOST", "").strip() or DEFAULT_WHATSAPP_HOST,
        port=_int("WHATSAPP_PORT", DEFAULT_WHATSAPP_PORT),
        api_version=os.getenv("WHATSAPP_API_VERSION", "").strip()
        or DEFAULT_GRAPH_API_VERSION,
    )
