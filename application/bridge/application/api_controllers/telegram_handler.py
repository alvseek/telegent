"""Presentation layer: Telegram update handlers. Pure I/O — no brain.

Receives a Telegram message, tags it with a platform-namespaced
``conversation_id`` (so the brain keeps every platform/user separate), asks the
brain for a reply over HTTP, and sends it back (chunked to Telegram's limit).
All intelligence and memory live in the brain.
"""
from __future__ import annotations

import logging

from telegram import Update, constants
from telegram.ext import ContextTypes

from application.common.message_chunker import chunk

log = logging.getLogger("telegent")

PLATFORM = "telegram"


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I'm telegent — send me a message and I'll reply. "
        "I remember our conversation."
    )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or not message.text:
        return
    chat_id = message.chat_id
    brain = context.bot_data["brain"]
    conversation_id = f"{PLATFORM}:{chat_id}"
    try:
        await context.bot.send_chat_action(chat_id, constants.ChatAction.TYPING)
        reply = await brain.chat(conversation_id, message.text)
        for part in chunk(reply):
            await message.reply_text(part)
    except Exception:
        log.exception("failed to handle message in chat %s", chat_id)
        await message.reply_text("Sorry — something went wrong. Please try again.")
