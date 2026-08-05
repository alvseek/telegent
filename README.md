# telegent

The **Telegram bridge** for [universal-chat-agent](../universal-chat-agent). A
thin, stateless pipe: it receives Telegram messages, forwards them to the brain
over HTTP, and sends the brain's reply back. It holds **no intelligence and no
memory** — swap the brain's model or wipe its database and telegent doesn't
change; build a WhatsApp/web bridge against the same brain and this repo is
untouched.

> Brain (the reusable agent): [universal-chat-agent](../universal-chat-agent)

---

## Q1 — What is this?

A Telegram bot front-end. Its only job is translation between Telegram and the
brain's HTTP contract. Every message is tagged with a namespaced
`conversation_id` (`telegram:<chat_id>`) so the brain keeps each chat's memory
separate and never collides with other platforms.

Structured with the **A-Boxed Level 1** pattern (flat semantic-prefix layers).
Because it's stateless, its data/business layers are intentionally empty
placeholders (see their READMEs).

## Q2 — How to set up?

```bash
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill TELEGRAM_BOT_TOKEN + BRAIN_URL
```

Create a bot: message **@BotFather** on Telegram → `/newbot` → follow prompts →
copy the token into `.env` as `TELEGRAM_BOT_TOKEN`.

## Q3 — How to use?

Start the brain first (see universal-chat-agent), then run the bridge:

```bash
python -m application.main
```

Message your bot on Telegram. `/start` for a greeting; any text gets a reply
from the brain, with conversation memory.

## Q4 — How it works?

```
Telegram ──▶ api_controllers/telegram_handler
                 │  conversation_id = "telegram:<chat_id>"
                 ▼
             api_integrations/brain/brain_client  ──HTTP POST /chat──▶  brain
                 │                                                        │
                 ◀────────────────────  {reply}  ◀────────────────────────┘
                 ▼
             common/message_chunker (split to 4096)  ──▶ Telegram reply
```

The bridge never sees the model or the database — only the brain's
`{conversation_id, message} → {reply}` contract.

## Q5 — How deployed?

```bash
docker compose up --build      # set BRAIN_URL in .env so it can reach the brain
```

Running both in Docker: put both compose projects on a shared network and set
`BRAIN_URL=http://universal-chat-agent:8000`, or point the bridge at the host
with `BRAIN_URL=http://host.docker.internal:8000`.

## Q6 — What decisions?

- **Split from the brain (this repo = bridge only)**: isolates Telegram-specific
  deps and failures, and lets one brain serve many bridges (WhatsApp, web, …).
- **HTTP to the brain**: any-language bridges + full process/dep isolation; the
  localhost hop is sub-millisecond next to the LLM call. Transport is behind
  `brain_client`, so a future swap (gRPC) is one file.
- **Stateless**: memory lives in the brain, keyed by `conversation_id`.

## Q7 — What's broken / TODO?

- Requires the brain to be running (`BRAIN_URL`); no offline fallback.
- Long-polling only (no webhook mode yet).
- `/start` is the only command; no rich command routing.

## License

MIT — see [LICENSE](LICENSE).
