"""Telegram bridge: receive messages, call the agent, reply. Pure I/O — no brain.

The bot holds no intelligence: it loads history, hands the message to the agent,
persists the exchange, and sends the reply back (splitting to respect Telegram's
message-length limit).
"""
from __future__ import annotations

import logging

from telegram import Update, constants
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import agent_core
from config import Config
from memory_store import MemoryStore

log = logging.getLogger("telegent")

TELEGRAM_MAX = 4096  # Telegram's hard per-message character limit


def _chunk(text: str, size: int = TELEGRAM_MAX) -> list[str]:
    """Split a reply into Telegram-sized pieces (never empty)."""
    text = text or "(empty reply)"
    return [text[i : i + size] for i in range(0, len(text), size)]


def build_application(
    config: Config, agent: agent_core.Agent, memory: MemoryStore
) -> Application:
    app = Application.builder().token(config.telegram_bot_token).build()
    app.bot_data.update(config=config, agent=agent, memory=memory)
    app.add_handler(CommandHandler("start", _on_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_message))
    return app


async def _on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I'm telegent — send me a message and I'll reply. "
        "I remember our conversation."
    )


async def _on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or not message.text:
        return
    chat_id = message.chat_id
    config: Config = context.bot_data["config"]
    agent = context.bot_data["agent"]
    memory: MemoryStore = context.bot_data["memory"]
    try:
        await context.bot.send_chat_action(chat_id, constants.ChatAction.TYPING)
        history = memory.get_history(chat_id, config.memory_window)
        reply = await agent_core.answer(agent, history, message.text)
        # Persist only after a successful reply, so a failure never stores half a turn.
        memory.append(chat_id, "user", message.text)
        memory.append(chat_id, "assistant", reply)
        for chunk in _chunk(reply):
            await message.reply_text(chunk)
    except Exception:
        log.exception("failed to handle message in chat %s", chat_id)
        await message.reply_text("Sorry — something went wrong. Please try again.")
