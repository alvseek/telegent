"""Handler tests — model-free. The brain is mocked; Telegram objects are fakes.

Verifies the bridge's core contract: a Telegram message is tagged with the
platform-namespaced conversation_id *and* the platform-namespaced end_user_id,
forwarded to the brain, and the brain's reply is sent back to the chat.

The distinction those two ids draw is the point of several tests below. The chat
is where a message arrived; the user is who sent it. They coincide in a private
chat and diverge in a group, and since credentials belong to a person, taking the
chat id for the person is the bug that would hand one member of a group another
member's inventory.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from application.api_controllers import telegram_handler


def _fake_update(text, chat_id, sent, user_id=None):
    async def reply_text(part):
        sent.append(part)

    message = SimpleNamespace(text=text, chat_id=chat_id, reply_text=reply_text)
    user = None if user_id is None else SimpleNamespace(id=user_id)
    return SimpleNamespace(message=message, effective_user=user)


def _fake_context(brain, agent_id=None, allowed=None):
    bot = SimpleNamespace(send_chat_action=AsyncMock())
    bot_data = {"brain": brain}
    if agent_id is not None or allowed is not None:
        bot_data["config"] = SimpleNamespace(agent_id=agent_id, allowed_chat_ids=allowed)
    return SimpleNamespace(bot=bot, bot_data=bot_data)


def test_forwards_to_brain_with_namespaced_ids_and_replies():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="hi there"))
    update = _fake_update("hello", 42, sent, user_id=7)
    context = _fake_context(brain)

    asyncio.run(telegram_handler.on_message(update, context))

    brain.chat.assert_awaited_once_with(
        "telegram:42", "hello", agent_id=None, end_user_id="telegram:7"
    )
    assert sent == ["hi there"]


def test_the_caller_is_the_user_not_the_chat():
    """In a group these differ, and credentials follow the person."""
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    update = _fake_update("hello", -100200300, sent, user_id=7)

    asyncio.run(telegram_handler.on_message(update, _fake_context(brain)))

    _, kwargs = brain.chat.await_args
    assert kwargs["end_user_id"] == "telegram:7"  # the person
    assert brain.chat.await_args.args[0] == "telegram:-100200300"  # the room


def test_forwards_agent_id_from_config():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="I am the operator"))
    update = _fake_update("who are you?", 42, sent, user_id=7)
    context = _fake_context(brain, agent_id="invintiry-operator")

    asyncio.run(telegram_handler.on_message(update, context))

    brain.chat.assert_awaited_once_with(
        "telegram:42",
        "who are you?",
        agent_id="invintiry-operator",
        end_user_id="telegram:7",
    )
    assert sent == ["I am the operator"]


def test_a_message_without_a_sender_forwards_no_caller():
    # Rare (channel posts), but it must degrade to "unlinked", never to a guess.
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    update = _fake_update("hello", 42, sent, user_id=None)

    asyncio.run(telegram_handler.on_message(update, _fake_context(brain)))

    assert brain.chat.await_args.kwargs["end_user_id"] is None


def test_ignores_non_text_message():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock())
    update = SimpleNamespace(
        message=SimpleNamespace(text=None, chat_id=1), effective_user=None
    )
    context = _fake_context(brain)

    asyncio.run(telegram_handler.on_message(update, context))

    brain.chat.assert_not_awaited()


def test_brain_failure_sends_apology():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(side_effect=RuntimeError("boom")))
    update = _fake_update("hello", 7, sent, user_id=7)
    context = _fake_context(brain)

    asyncio.run(telegram_handler.on_message(update, context))

    assert sent and "wrong" in sent[0].lower()


def test_unlisted_chat_gets_nothing_and_is_logged(caplog):
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="should not happen"))
    update = _fake_update("hello", 999, sent, user_id=7)
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
    update = _fake_update("hello", 42, sent, user_id=7)
    context = _fake_context(brain, allowed=frozenset({42}))

    asyncio.run(telegram_handler.on_message(update, context))

    brain.chat.assert_awaited_once()
    assert sent == ["ok"]


def test_open_allowlist_admits_everyone():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    update = _fake_update("hello", 999, sent, user_id=7)
    context = _fake_context(brain, allowed=None)

    asyncio.run(telegram_handler.on_message(update, context))

    brain.chat.assert_awaited_once()
    assert sent == ["ok"]


def test_start_is_gated_too():
    sent = []
    brain = SimpleNamespace(chat=AsyncMock())
    update = _fake_update("/start", 999, sent, user_id=7)
    context = _fake_context(brain, allowed=frozenset({42}))

    asyncio.run(telegram_handler.on_start(update, context))

    brain.chat.assert_not_awaited()
    assert sent == []


def test_start_is_forwarded_so_a_link_code_reaches_the_brain():
    """A deep link arrives as "/start <code>". Answering it here would eat it."""
    sent = []
    brain = SimpleNamespace(chat=AsyncMock(return_value="Linked as Alvi"))
    update = _fake_update("/start ABC123", 42, sent, user_id=7)
    context = _fake_context(brain, allowed=frozenset({42}))

    asyncio.run(telegram_handler.on_start(update, context))

    brain.chat.assert_awaited_once_with(
        "telegram:42", "/start ABC123", agent_id=None, end_user_id="telegram:7"
    )
    assert sent == ["Linked as Alvi"]
