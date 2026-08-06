---
doc_type: 7q-readme
---

# telegent

## Table of Contents

- [What Is This?](#what-is-this)
- [How Do I Set It Up?](#how-do-i-set-it-up)
- [How Do I Use It?](#how-do-i-use-it)
- [How Does It Work Inside?](#how-does-it-work-inside)
- [How Is It Deployed?](#how-is-it-deployed)
- [What Decisions Were Made?](#what-decisions-were-made)
- [What's Broken / Known Debts?](#whats-broken--known-debts)

---

## What Is This?

The **Telegram bridge** for [universal-chat-agent](../universal-chat-agent). A thin,
stateless pipe: it receives Telegram messages, forwards them to the brain over HTTP,
and sends the brain's reply back. It holds **no intelligence and no memory** — swap the
brain's model or wipe its database and telegent doesn't change; build a WhatsApp/web
bridge against the same brain and this repo is untouched.

For **anyone self-hosting a Telegram front-end** onto a reusable chat agent.

### Architecture

Follows the **A-Boxed Level 1** pattern (flat semantic-prefix layers). Because the bridge
is stateless, its `data_*` and `business_*` layers are intentionally empty placeholders
(each has a README explaining why).

```
Telegram ──▶ api_controllers/telegram_handler
                 │  conversation_id = "telegram:<chat_id>"   (namespacing → brain stays platform-agnostic)
                 ▼
             api_integrations/brain/brain_client  ──HTTP POST /chat──▶  universal-chat-agent
                 │                                                              │
                 ◀──────────────────────  {reply}  ◀────────────────────────────┘
                 ▼
             common/message_chunker  (split to 4096)  ──▶  Telegram reply
```

The bridge never sees the model or the database — only the brain's
`{conversation_id, message} → {reply}` contract.

### Tech Stack

- **Runtime**: Python 3.12+
- **Telegram**: python-telegram-bot 22 (long-polling)
- **HTTP client**: httpx (keep-alive connection to the brain)
- **Config**: python-dotenv

---

## How Do I Set It Up?

### Prerequisites

- Python 3.12+ (`python --version`)
- A running [universal-chat-agent](../universal-chat-agent) instance (the brain)
- A Telegram bot token (from @BotFather)

### Setup

1. Clone and install:
   ```sh
   git clone <repo-url>
   cd telegent
   python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Create a bot: message **@BotFather** → `/newbot` → follow prompts → copy the token.

3. Configure environment:
   ```sh
   cp .env.example .env
   # Edit .env — see Environment Variables below
   ```

4. Start (with the brain already running):
   ```sh
   python -m application.main
   ```

5. Verify it works: message your bot on Telegram and send `/start` — it should greet you,
   then reply to any text with a brain-generated answer.

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather (required) | `123456:ABC-...` |
| `BRAIN_URL` | Base URL of the running brain | `http://localhost:8000` |
| `BRAIN_TIMEOUT` | Seconds to wait for a brain reply (LLM is slow) | `60` |

---

## How Do I Use It?

### Commands

| Command | Description |
|---------|-------------|
| `python -m application.main` | Start the bridge (long-polling) |
| `python -m pytest tests/ -q` | Run model-free tests |

### Bot commands

| Command | Description |
|---------|-------------|
| `/start` | Greeting |
| *(any text)* | Forwarded to the brain; reply returned with conversation memory |

---

## How Does It Work Inside?

### Core Flow: message → reply

1. **Receive** (`application/api_controllers/telegram_handler.py`)
   - A text update arrives; the handler tags it `conversation_id = "telegram:<chat_id>"`.
2. **Forward** (`application/api_integrations/brain/brain_client.py`)
   - `POST {BRAIN_URL}/chat {conversation_id, message}` over a keep-alive httpx client.
3. **Reply** (`application/common/message_chunker.py`)
   - The brain's `{reply}` is split into ≤4096-char pieces and sent back to the chat.

On any failure the handler logs it and sends a friendly apology, so a brain outage never
crashes the bridge.

### External Integrations

| Service | Purpose | Protocol | Timeout |
|---------|---------|----------|---------|
| Telegram Bot API | Receive messages / send replies | HTTPS (long-poll) | library default |
| universal-chat-agent | Get the reply for a message | HTTP `POST /chat` | `BRAIN_TIMEOUT` (60s) |

The bridge holds no database — conversation memory lives in the brain, keyed by
`conversation_id`.

---

## How Is It Deployed?

### Environments

| Environment | URL | Branch | Auto-deploy |
|-------------|-----|--------|-------------|
| Local | n/a (long-polling) | `main` | No |

Long-polling means **one running instance per bot token** — a second copy causes a
Telegram `409 Conflict`.

### Docker

```sh
docker compose up --build      # set BRAIN_URL in .env so it can reach the brain
```

Running both services in Docker: put both compose projects on a shared network and set
`BRAIN_URL=http://universal-chat-agent:8000`, or point the bridge at the host with
`BRAIN_URL=http://host.docker.internal:8000`.

### CI/CD

[NOT FOUND: no CI/CD pipeline configured yet.]

---

## What Decisions Were Made?

### ADR-001: Split the bridge from the brain (2026-08-05)

**Context**: M1 was a monolith (Telegram + model + memory in one repo).
**Decision**: Extract the agent into `universal-chat-agent` and keep telegent as a
Telegram-only bridge that calls it over HTTP.
**Trade-off**: Two processes to run instead of one — accepted, because it isolates
Telegram-specific dependencies/failures and lets one brain serve many bridges (WhatsApp,
web) unchanged.

### ADR-002: HTTP to the brain (2026-08-05)

**Context**: Bridge and brain both run locally; was HTTP overhead a concern (vs gRPC / in-process)?
**Decision**: Plain HTTP behind a thin `brain_client`.
**Trade-off**: A network hop, but measured at ~0.85 ms on localhost vs a ~4.2 s LLM call
(0.02%) — negligible. HTTP keeps bridges language-agnostic and dependency-isolated;
transport can be swapped in one file later if streaming is ever needed.

### ADR-003: Stateless bridge (2026-08-05)

**Context**: Where should conversation memory live?
**Decision**: In the brain, keyed by `conversation_id`; the bridge stores nothing.
**Trade-off**: The bridge can't work offline from the brain — accepted, since statelessness
is what lets many bridges share one brain and one memory without coordination.

---

## What's Broken / Known Debts?

### High Priority

- **M1 bot token was leaked to logs and is unrotated.** *Why*: an early run logged the
  token-bearing Telegram URL (logging is now silenced). Rotate it in @BotFather.

### Medium Priority

- **Requires the brain to be running** (`BRAIN_URL`); no offline fallback or retry/backoff.
  *Why*: M2 scope — reliability hardening deferred.

### Known Limitations

- Long-polling only — no webhook mode yet.
- `/start` is the only command; no rich command routing.
- Backlog replay: messages sent while the bridge is offline are delivered on reconnect
  (Telegram queues updates ~24h). Intentional for a personal bot; set
  `run_polling(drop_pending_updates=True)` in `application/main.py` to disable.

---

## License

MIT — see [LICENSE](LICENSE).
