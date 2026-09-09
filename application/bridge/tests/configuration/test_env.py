"""Config tests — each transport's settings parse the way its README promises,
and neither transport's missing variables can break the other's startup.

That last property is the point of the split: both processes read the same
``.env`` from the same directory, so a Telegram bridge must boot on a file that
has no WhatsApp values in it yet, and a WhatsApp bridge must boot without a
Telegram token.
"""
import pytest

from application.configuration import env

_WHATSAPP_VARS = (
    "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_APP_SECRET",
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_ALLOWED_IDS",
    "WHATSAPP_DB_PATH",
    "WHATSAPP_HOST",
    "WHATSAPP_PORT",
    "WHATSAPP_API_VERSION",
)

_REQUIRED_WHATSAPP = _WHATSAPP_VARS[:4]


def _clear(monkeypatch, *names):
    for name in names:
        monkeypatch.delenv(name, raising=False)


def _load(monkeypatch, **values):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    _clear(monkeypatch, "ALLOWED_CHAT_IDS", "DROP_PENDING_UPDATES", "AGENT_ID")
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return env.load_telegram_config()


def _load_wa(monkeypatch, **values):
    _clear(monkeypatch, *_WHATSAPP_VARS, "AGENT_ID")
    for name in _REQUIRED_WHATSAPP:
        monkeypatch.setenv(name, "x")
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return env.load_whatsapp_config()


# --- Telegram -------------------------------------------------------------


def test_defaults_are_open_and_drop_pending(monkeypatch):
    config = _load(monkeypatch)
    assert config.allowed_chat_ids is None
    assert config.drop_pending_updates is True


def test_allowlist_parses_to_ids(monkeypatch):
    config = _load(monkeypatch, ALLOWED_CHAT_IDS="8932435376, -100")
    assert config.allowed_chat_ids == frozenset({8932435376, -100})


def test_allowlist_typo_fails_at_startup(monkeypatch):
    with pytest.raises(ValueError, match="ALLOWED_CHAT_IDS"):
        _load(monkeypatch, ALLOWED_CHAT_IDS="42,abc")


def test_drop_pending_accepts_known_tokens(monkeypatch):
    assert _load(monkeypatch, DROP_PENDING_UPDATES="false").drop_pending_updates is False
    assert _load(monkeypatch, DROP_PENDING_UPDATES="0").drop_pending_updates is False
    assert _load(monkeypatch, DROP_PENDING_UPDATES="TRUE").drop_pending_updates is True


def test_drop_pending_typo_fails_at_startup(monkeypatch):
    with pytest.raises(ValueError, match="DROP_PENDING_UPDATES"):
        _load(monkeypatch, DROP_PENDING_UPDATES="ture")


# --- The split: neither transport can break the other ---------------------


def test_telegram_loads_with_no_whatsapp_values_present(monkeypatch):
    """A box that has never heard of WhatsApp must still start the bot it has."""
    _clear(monkeypatch, *_WHATSAPP_VARS)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    assert env.load_telegram_config().telegram_bot_token == "t"


def test_whatsapp_loads_with_no_telegram_token(monkeypatch):
    _clear(monkeypatch, "TELEGRAM_BOT_TOKEN")
    assert _load_wa(monkeypatch).access_token == "x"


# --- WhatsApp -------------------------------------------------------------


@pytest.mark.parametrize("missing", _REQUIRED_WHATSAPP)
def test_each_whatsapp_variable_fails_by_its_own_name(monkeypatch, missing):
    _clear(monkeypatch, *_WHATSAPP_VARS)
    for name in _REQUIRED_WHATSAPP:
        if name != missing:
            monkeypatch.setenv(name, "x")
    with pytest.raises(ValueError, match=missing):
        env.load_whatsapp_config()


def test_whatsapp_defaults(monkeypatch):
    config = _load_wa(monkeypatch)
    assert config.allowed_ids is None          # open, per the product decision
    assert config.host == "127.0.0.1"          # loopback — Caddy terminates TLS
    assert config.port == 8200
    assert config.db_path == "whatsapp.db"
    assert config.api_version == "v22.0"


def test_whatsapp_allowlist_parses_phone_numbers(monkeypatch):
    config = _load_wa(monkeypatch, WHATSAPP_ALLOWED_IDS="6282311020200")
    assert config.allowed_ids == frozenset({6282311020200})


def test_whatsapp_allowlist_typo_names_its_own_variable(monkeypatch):
    """Not ALLOWED_CHAT_IDS — the reader must be sent to the right setting."""
    with pytest.raises(ValueError, match="WHATSAPP_ALLOWED_IDS"):
        _load_wa(monkeypatch, WHATSAPP_ALLOWED_IDS="62823,nope")


def test_whatsapp_port_typo_fails_at_startup(monkeypatch):
    with pytest.raises(ValueError, match="WHATSAPP_PORT"):
        _load_wa(monkeypatch, WHATSAPP_PORT="eight-thousand")


def test_agent_id_is_shared_by_both_transports(monkeypatch):
    """One brain, two doors, same agent — the selector lives in each bridge."""
    assert _load_wa(monkeypatch, AGENT_ID="invintiry-operator").agent_id == "invintiry-operator"
    assert _load(monkeypatch, AGENT_ID="invintiry-operator").agent_id == "invintiry-operator"


def test_agent_id_absent_means_the_brains_default_agent(monkeypatch):
    assert _load_wa(monkeypatch).agent_id is None
    assert _load(monkeypatch).agent_id is None
