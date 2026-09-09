"""Presentation layer: Telegram update handlers. Pure I/O — no brain.

Receives a Telegram message, unwraps the two ids it carries, and hands them to
``business_services.forward``, which owns the workflow both transports share:
the allowlist decision, the platform-namespaced ids, the brain call and the
chunked reply. Everything Telegram-shaped stays here — how to send a message,
how to show a typing indicator, what an ``Update`` looks like.

The two ids answer different questions and are not interchangeable. The chat id
is the room; the user id is the person. They match in a private chat and diverge
in a group, and credentials belong to a person — so anything that acts on
someone's behalf keys off ``from.id``, never the chat.

``/start`` is forwarded rather than answered here. Telegram delivers a deep link
as ``/start <code>``, and the code has to reach the brain, which is what holds the
account bindings; a canned greeting in the bridge would swallow it.

A chat outside the allowlist gets nothing — no typing indicator, no brain call,
no reply — and one WARNING line naming its chat id, so the bot looks absent to a
stranger and the operator can still find an id worth adding. That rule is
enforced in ``forward``, once, for every transport.
"""
from __future__ import annotations

import logging

from telegram import Update, constants
from telegram.ext import ContextTypes

from application.business_services.forward import forward

log = logging.getLogger("telegent")

PLATFORM = "telegram"


def user_key(update: Update) -> int | None:
    """Who sent this — the person, not the chat it arrived in.

    ``None`` for a message with no sender (channel posts), which must degrade to
    "no caller" rather than to a guess.
    """
    user = update.effective_user
    return None if user is None else user.id


async def _forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adapt one Telegram update onto the shared workflow."""
    message = update.message
    config = context.bot_data.get("config")

    async def send(part: str) -> None:
        await message.reply_text(part)

    async def on_admitted() -> None:
        await context.bot.send_chat_action(message.chat_id, constants.ChatAction.TYPING)

    await forward(
        platform=PLATFORM,
        chat_key=message.chat_id,
        user_key=user_key(update),
        text=message.text,
        brain=context.bot_data["brain"],
        agent_id=getattr(config, "agent_id", None),
        allowlist=getattr(config, "allowed_chat_ids", None),
        send=send,
        on_admitted=on_admitted,
    )


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/start`` — forwarded, because it may carry a link code."""
    if update.message is None or not update.message.text:
        return
    await _forward(update, context)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or not message.text:
        return
    await _forward(update, context)
