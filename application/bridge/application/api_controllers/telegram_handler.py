"""Presentation layer: Telegram update handlers. Pure I/O — no brain.

Receives a Telegram message, checks the chat is one this bot talks to, tags it
with a platform-namespaced ``conversation_id`` (so the brain keeps every
platform/chat separate) and a platform-namespaced ``end_user_id`` (so the brain
knows *who* is asking), asks the brain for a reply over HTTP, and sends it back
(chunked to Telegram's limit). All intelligence and memory live in the brain.

The two ids answer different questions and are not interchangeable. The chat id
is the room; the user id is the person. They match in a private chat and diverge
in a group, and credentials belong to a person — so anything that acts on
someone's behalf keys off ``from.id``, never the chat.

``/start`` is forwarded rather than answered here. Telegram delivers a deep link
as ``/start <code>``, and the code has to reach the brain, which is what holds the
account bindings; a canned greeting in the bridge would swallow it.

A chat outside the allowlist gets nothing — no typing indicator, no brain call,
no reply — and one WARNING line naming its chat id, so the bot looks absent to a
stranger and the operator can still find an id worth adding.
"""
from __future__ import annotations

import logging

from telegram import Update, constants
from telegram.ext import ContextTypes

from application.business_domain.access_policy import is_allowed
from application.common.message_chunker import chunk

log = logging.getLogger("telegent")

PLATFORM = "telegram"


def _admitted(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Gate every handler: is this chat on the bot's allowlist?"""
    config = context.bot_data.get("config")
    allowlist = getattr(config, "allowed_chat_ids", None)
    chat_id = update.message.chat_id
    if is_allowed(chat_id, allowlist):
        return True
    log.warning("refused chat %s: not in ALLOWED_CHAT_IDS", chat_id)
    return False


def end_user_id(update: Update) -> str | None:
    """Who sent this, namespaced by platform — not the chat it arrived in."""
    user = update.effective_user
    return f"{PLATFORM}:{user.id}" if user is not None else None


async def _forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send one message to the brain and reply with what comes back."""
    message = update.message
    chat_id = message.chat_id
    brain = context.bot_data["brain"]
    config = context.bot_data.get("config")
    agent_id = getattr(config, "agent_id", None)
    conversation_id = f"{PLATFORM}:{chat_id}"
    try:
        await context.bot.send_chat_action(chat_id, constants.ChatAction.TYPING)
        reply = await brain.chat(
            conversation_id,
            message.text,
            agent_id=agent_id,
            end_user_id=end_user_id(update),
        )
        for part in chunk(reply):
            await message.reply_text(part)
    except Exception:
        log.exception("failed to handle message in chat %s", chat_id)
        await message.reply_text("Sorry — something went wrong. Please try again.")


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/start`` — forwarded, because it may carry a link code."""
    if update.message is None or not update.message.text:
        return
    if not _admitted(update, context):
        return
    await _forward(update, context)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or not message.text:
        return
    if not _admitted(update, context):
        return
    await _forward(update, context)
