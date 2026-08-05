"""Composition root: wire config + brain client + Telegram handlers, then poll.

The bridge is a dumb, faithful pipe: Telegram message -> brain -> reply. It
holds no intelligence and no memory.
"""
from __future__ import annotations

import logging

from application.api_controllers import telegram_handler
from application.api_integrations.brain.brain_client import BrainClient
from application.api_integrations.telegram.telegram_client import build_application
from application.configuration.env import load_config
from application.logger import logger_setup


def main() -> None:
    logger_setup.configure()
    config = load_config()

    brain = BrainClient(config.brain_url, config.brain_timeout)
    app = build_application(
        config.telegram_bot_token,
        telegram_handler.on_start,
        telegram_handler.on_message,
    )
    app.bot_data.update(brain=brain, config=config)

    logging.getLogger("telegent").info(
        "telegent bridge starting -> brain=%s (long-polling)", config.brain_url
    )
    app.run_polling()


if __name__ == "__main__":
    main()
