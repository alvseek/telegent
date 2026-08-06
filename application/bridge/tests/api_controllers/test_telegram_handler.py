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


def _fake_context(brain):
    bot = SimpleNamespace(send_chat_action=AsyncMock())
    return SimpleNamespace(bot=bot, bot_data={"brain": brain})


def test_forwards_to_brain_with_namespaced_id_and_replies():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="hi there"))
    update = _fake_update("hello", 42, sent)
    context = _fake_context(brain)

    asyncio.run(telegram_handler.on_message(update, context))

    brain.chat.assert_awaited_once_with("telegram:42", "hello")
    assert sent == ["hi there"]


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
