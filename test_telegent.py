"""Model-free tests for telegent. Run: `python test_telegent.py` (no network needed).

Covers the deterministic parts: config validation, memory store behaviour, the
reply chunker, and agent wiring. The live end-to-end (real Telegram + model) is
verified by following the README.
"""
from __future__ import annotations

import os
import tempfile


def test_agent_builds_and_maps_history():
    import agent_core

    agent = agent_core.build_agent(
        "deepseek/deepseek-chat", "https://openrouter.ai/api/v1", "sk-x", "sys"
    )
    assert type(agent).__name__ == "Agent"
    msgs = agent_core._to_history([("user", "a"), ("assistant", "b")])
    assert [type(x).__name__ for x in msgs] == ["ModelRequest", "ModelResponse"]


def test_chunker_splits_long_replies():
    from bot_telegram import TELEGRAM_MAX, _chunk

    assert _chunk("hello") == ["hello"]
    assert _chunk("") == ["(empty reply)"]
    big = "x" * (TELEGRAM_MAX * 2 + 5)
    chunks = _chunk(big)
    assert len(chunks) == 3
    assert all(len(c) <= TELEGRAM_MAX for c in chunks)
    assert "".join(chunks) == big


def test_config_valid_and_missing():
    os.environ.update(
        TELEGRAM_BOT_TOKEN="t", OPENROUTER_API_KEY="k", OPENROUTER_MODEL="m"
    )
    os.environ.pop("MEMORY_WINDOW", None)
    import config

    c = config.load_config()
    assert c.telegram_bot_token == "t"
    assert c.memory_window == 15
    assert c.openrouter_base_url.startswith("https://")
    assert c.system_prompt  # default present

    os.environ.pop("OPENROUTER_MODEL")  # now missing a required var
    try:
        config.load_config()
        raise AssertionError("expected ValueError for missing OPENROUTER_MODEL")
    except ValueError:
        pass
    os.environ["OPENROUTER_MODEL"] = "m"  # restore for any later use


def test_memory_bounded_ordered_isolated_persistent():
    from memory_store import MemoryStore

    path = tempfile.mktemp(suffix=".db")
    m = MemoryStore(path)
    for i in range(5):
        m.append(1, "user", f"u{i}")
        m.append(1, "assistant", f"a{i}")
    m.append(2, "user", "other")

    h = m.get_history(1, 4)
    assert len(h) == 4
    assert h[0] == ("user", "u3") and h[-1] == ("assistant", "a4")  # oldest-first
    assert len(m.get_history(2, 10)) == 1  # per-chat isolation
    m.close()

    m2 = MemoryStore(path)  # reopen -> persistence
    assert len(m2.get_history(1, 100)) == 10
    m2.close()
    os.remove(path)


def _run() -> None:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    _run()
