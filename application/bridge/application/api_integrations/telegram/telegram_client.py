"""External integration: Telegram Bot API wiring (python-telegram-bot).

Builds the Application and registers handlers. Keeps the python-telegram-bot
specifics in one place; the handlers themselves live in api_controllers.
"""
from __future__ import annotations

from typing import Callable

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)


def build_application(
    token: str, on_start: Callable, on_message: Callable
) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    return app
