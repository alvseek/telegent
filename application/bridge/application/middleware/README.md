# middleware — placeholder (A-Boxed L1 full skeleton)

Intentionally empty. The bridge runs no HTTP server, so there are no HTTP
routes to wrap. Cross-cutting handler concerns (errors, typing indicator) are
handled directly in `api_controllers/telegram_handler.py` via python-telegram-bot.

If the bridge adds a webhook server, request-level middleware would go here.
