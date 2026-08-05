# api_dto — placeholder (A-Boxed L1 full skeleton)

Intentionally empty. The bridge doesn't define its own request/response
contracts — it speaks the **brain's** contract (`{conversation_id, message}` →
`{reply}`), which lives in `universal-chat-agent`, and Telegram's own update
types (owned by python-telegram-bot).

Add DTOs here only if the bridge ever exposes its own HTTP surface (e.g. a
webhook endpoint with a validated payload).
