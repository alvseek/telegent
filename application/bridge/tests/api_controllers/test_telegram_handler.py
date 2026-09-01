"""Handler tests — model-free. The brain is mocked; Telegram objects are fakes.

Verifies the bridge's core contract: a Telegram message is tagged with the
platform-namespaced conversation_id and forwarded to the brain, and the brain's
reply is sent back to the chat.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from application.api_controllers import telegram_handler


def _fake_update(text, chat_id, sent):
    async def reply_text(part):
        sent.append(part)

    message = SimpleNamespace(text=text, chat_id=chat_id, reply_text=reply_text)
    return SimpleNamespace(message=message)


def _fake_context(brain, agent_id=None, allowed=None):
    bot = SimpleNamespace(send_chat_action=AsyncMock())
    bot_data = {"brain": brain}
    if agent_id is not None or allowed is not None:
        bot_data["config"] = SimpleNamespace(agent_id=agent_id, allowed_chat_ids=allowed)
    return SimpleNamespace(bot=bot, bot_data=bot_data)


def test_forwards_to_brain_with_namespaced_id_and_replies():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="hi there"))
    update = _fake_update("hello", 42, sent)
    context = _fake_context(brain)

    asyncio.run(telegram_handler.on_message(update, context))

    brain.chat.assert_awaited_once_with("telegram:42", "hello", agent_id=None)
    assert sent == ["hi there"]


def test_forwards_agent_id_from_config():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="I am the operator"))
    update = _fake_update("who are you?", 42, sent)
    context = _fake_context(brain, agent_id="invintiry-operator")

    asyncio.run(telegram_handler.on_message(update, context))

    brain.chat.assert_awaited_once_with("telegram:42", "who are you?", agent_id="invintiry-operator")
    assert sent == ["I am the operator"]


def test_ignores_non_text_message():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock())
    update = SimpleNamespace(message=SimpleNamespace(text=None, chat_id=1))
    context = _fake_context(brain)

    asyncio.run(telegram_handler.on_message(update, context))

    brain.chat.assert_not_awaited()


def test_brain_failure_sends_apology():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(side_effect=RuntimeError("boom")))
    update = _fake_update("hello", 7, sent)
    context = _fake_context(brain)

    asyncio.run(telegram_handler.on_message(update, context))

    assert sent and "wrong" in sent[0].lower()


def test_unlisted_chat_gets_nothing_and_is_logged(caplog):
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="should not happen"))
    update = _fake_update("hello", 999, sent)
    context = _fake_context(brain, allowed=frozenset({42}))

    with caplog.at_level("WARNING", logger="telegent"):
        asyncio.run(telegram_handler.on_message(update, context))

    brain.chat.assert_not_awaited()
    context.bot.send_chat_action.assert_not_awaited()
    assert sent == []
    assert any("refused chat 999" in r.getMessage() for r in caplog.records)


def test_listed_chat_is_admitted():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    update = _fake_update("hello", 42, sent)
    context = _fake_context(brain, allowed=frozenset({42}))

    asyncio.run(telegram_handler.on_message(update, context))

    brain.chat.assert_awaited_once()
    assert sent == ["ok"]


def test_open_allowlist_admits_everyone():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    update = _fake_update("hello", 999, sent)
    context = _fake_context(brain, allowed=None)

    asyncio.run(telegram_handler.on_message(update, context))

    brain.chat.assert_awaited_once()
    assert sent == ["ok"]


def test_start_is_gated_too():
    sent = []
    update = _fake_update("/start", 999, sent)
    context = _fake_context(SimpleNamespace(), allowed=frozenset({42}))

    asyncio.run(telegram_handler.on_start(update, context))

    assert sent == []


def test_start_greets_listed_chat():
    sent = []
    update = _fake_update("/start", 42, sent)
    context = _fake_context(SimpleNamespace(), allowed=frozenset({42}))

    asyncio.run(telegram_handler.on_start(update, context))

    assert len(sent) == 1 and "telegent" in sent[0]
