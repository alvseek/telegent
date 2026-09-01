"""Presentation layer: Telegram update handlers. Pure I/O — no brain.

Receives a Telegram message, checks the chat is one this bot talks to, tags it
with a platform-namespaced ``conversation_id`` (so the brain keeps every
platform/user separate), asks the brain for a reply over HTTP, and sends it back
(chunked to Telegram's limit). All intelligence and memory live in the brain.

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


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not _admitted(update, context):
        return
    await update.message.reply_text(
        "Hi! I'm telegent — send me a message and I'll reply. "
        "I remember our conversation."
    )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or not message.text:
        return
    if not _admitted(update, context):
        return
    chat_id = message.chat_id
    brain = context.bot_data["brain"]
    config = context.bot_data.get("config")
    agent_id = getattr(config, "agent_id", None)
    conversation_id = f"{PLATFORM}:{chat_id}"
    try:
        await context.bot.send_chat_action(chat_id, constants.ChatAction.TYPING)
        reply = await brain.chat(conversation_id, message.text, agent_id=agent_id)
        for part in chunk(reply):
            await message.reply_text(part)
    except Exception:
        log.exception("failed to handle message in chat %s", chat_id)
        await message.reply_text("Sorry — something went wrong. Please try again.")
