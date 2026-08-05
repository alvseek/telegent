"""Entrypoint: wire config + memory + agent, then start long-polling."""
from __future__ import annotations

import logging

import agent_core
from bot_telegram import build_application
from config import load_config
from memory_store import MemoryStore


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Telegram API URLs embed the bot token; the HTTP client logs full URLs at
    # INFO. Silence them so the token is never written to logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    config = load_config()
    memory = MemoryStore(config.db_path)
    agent = agent_core.build_agent(
        model=config.openrouter_model,
        base_url=config.openrouter_base_url,
        api_key=config.openrouter_api_key,
        system_prompt=config.system_prompt,
    )
    app = build_application(config, agent, memory)
    logging.getLogger("telegent").info(
        "telegent starting (model=%s) - long-polling...", config.openrouter_model
    )
    app.run_polling()


if __name__ == "__main__":
    main()
