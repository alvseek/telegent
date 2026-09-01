"""Config tests — the two access settings parse the way the README promises."""
import pytest

from application.configuration import env


def _load(monkeypatch, **values):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    for name in ("ALLOWED_CHAT_IDS", "DROP_PENDING_UPDATES", "AGENT_ID"):
        monkeypatch.delenv(name, raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return env.load_config()


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
