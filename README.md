# telegent

A Telegram-fronted AI agent. A Telegram bot bridges your messages to an LLM agent
(via [OpenRouter](https://openrouter.ai), using [pydantic-ai](https://ai.pydantic.dev))
with per-chat conversation memory. Minimal, self-hostable, MIT-licensed.

- **Telegram bot** = a dumb I/O bridge (receive → reply)
- **Brain** = a pydantic-ai agent on *your* chosen OpenRouter model
- **Memory** = per-`chat_id`, SQLite-persisted, bounded window (survives restarts)

> **M1** is the bare bot: message → model → reply, with memory. Skills, knowledge (RAG),
> and custom tools come in later increments.

---

## 1. Create a Telegram bot (BotFather)

1. In Telegram, open [**@BotFather**](https://t.me/BotFather).
2. Send `/newbot`, then follow the prompts (name + a username ending in `bot`).
3. BotFather replies with a **token** like `123456:ABC-...`. Copy it.

## 2. Get an OpenRouter key

Sign in at [openrouter.ai](https://openrouter.ai) → **Keys** → create a key.

## 3. Configure

```bash
cp .env.example .env
```

Fill `.env`:

| Variable | Required | Default | Notes |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | from BotFather |
| `OPENROUTER_API_KEY` | ✅ | — | from OpenRouter |
| `OPENROUTER_MODEL` | ✅ | `deepseek/deepseek-chat` | any OpenRouter model id — swap freely |
| `OPENROUTER_BASE_URL` | — | `https://openrouter.ai/api/v1` | OpenAI-compatible endpoint |
| `MEMORY_WINDOW` | — | `15` | recent messages remembered per chat |
| `DB_PATH` | — | `telegent.db` | SQLite memory file |
| `SYSTEM_PROMPT` | — | (friendly assistant) | the agent's persona |

> `.env` is gitignored — never commit it.

## 4. Run

**Local (Python 3.11+):**
```bash
pip install -r requirements.txt
python main.py
```

**Docker:**
```bash
docker compose up --build
```
(Memory persists in the `telegent-data` volume across `up`/`down`.)

Then open your bot in Telegram, send `/start`, and chat. It remembers the
conversation per chat.

---

## Tests

Model-free checks (no network or keys needed):
```bash
python test_telegent.py
```

## Project structure (A-Boxed Level 1)

```
config.py         # env loading + validation
memory_store.py   # per-chat_id SQLite conversation memory (bounded)
agent_core.py     # pydantic-ai agent on the OpenRouter model
bot_telegram.py   # Telegram handlers (dumb bridge) + reply chunking
main.py           # wires it together, starts long-polling
test_telegent.py  # model-free tests
Dockerfile · docker-compose.yml · requirements.txt · .env.example
```

## Notes

- **One instance per bot token** — long-polling means a second running copy causes a
  Telegram `409 Conflict`.
- **Swappable by design** — the brain lives only in `agent_core.py`; the platform,
  memory, and model can each change without touching the others.

## License

MIT — see [LICENSE](LICENSE).
