---
doc_type: 7q-readme
---

# telegent — bridge

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

The **Telegram bridge** of the telegent stack (the monorepo root is [`../../`](../../README.md)).
A thin, stateless pipe: it receives Telegram messages, forwards them to the brain
([`../brain`](../brain)) over HTTP, and sends the brain's reply back. It holds **no
intelligence and no memory** — swap the brain's model or wipe its database and this bridge
doesn't change; build a WhatsApp/web bridge against the same brain and this component is
untouched.

For **anyone self-hosting a Telegram front-end** onto a reusable chat agent.

### Architecture

Follows the **A-Boxed Level 1** pattern (flat semantic-prefix layers). Because the bridge is
stateless, its `data_*` and `business_services` layers are intentionally empty placeholders
(each has a README explaining why). The one domain rule it does own — *which chats may talk
to this bot* — lives in `business_domain/access_policy.py` as pure functions.

```
Telegram ──▶ api_controllers/telegram_handler
                 │  business_domain/access_policy: chat on ALLOWED_CHAT_IDS?  (no → dropped, WARNING logged)
                 │  conversation_id = "telegram:<chat_id>"   (namespacing → brain stays platform-agnostic)
                 ▼
             api_integrations/brain/brain_client  ──HTTP POST /chat {…, agent_id?}──▶  brain (../brain)
                 │                                                            │
                 ◀──────────────────────  {reply}  ◀──────────────────────────┘
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
- A running brain ([`../brain`](../brain)) reachable over HTTP
- A Telegram bot token (from @BotFather)

### Setup

Run from this component's folder (`application/bridge`):

1. Install:
   ```sh
   cd application/bridge
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
| `BRAIN_URL` | Base URL of the running brain | `http://127.0.0.1:8100` |
| `BRAIN_TIMEOUT` | Seconds to wait for a brain reply (LLM is slow) | `60` |
| `AGENT_ID` | Which agent this bot *is* (sent on every `/chat`); empty = the brain's default agent | `invintiry-operator` |
| `ALLOWED_CHAT_IDS` | Comma-separated chat ids that may talk to this bot; empty = anyone. Other chats are dropped silently and logged at WARNING | `8932435376,-100123` |
| `DROP_PENDING_UPDATES` | Discard messages queued while the bridge was down instead of replaying them on start | `true` (default) |

Your own chat id is in the bridge log the first time you message the bot from an unlisted
account (`refused chat <id>`), or in the brain's conversation ids (`telegram:<id>`).

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

1. **Admit** (`application/business_domain/access_policy.py`)
   - Before anything else, the chat is checked against `ALLOWED_CHAT_IDS`. An unlisted chat
     gets no typing indicator, no brain call and no reply — only a WARNING line with its id.
     This applies to `/start` too, so a stranger cannot even confirm the bot is alive.
2. **Receive** (`application/api_controllers/telegram_handler.py`)
   - A text update arrives; the handler tags it `conversation_id = "telegram:<chat_id>"`.
3. **Forward** (`application/api_integrations/brain/brain_client.py`)
   - `POST {BRAIN_URL}/chat {conversation_id, message, agent_id?}` over a keep-alive httpx client.
4. **Reply** (`application/common/message_chunker.py`)
   - The brain's `{reply}` is split into ≤4096-char pieces and sent back to the chat.

On any failure the handler logs it and sends a friendly apology, so a brain outage never
crashes the bridge.

### Messages sent while the bridge is down

Telegram queues updates for ~24 h. python-telegram-bot confirms a fetched batch to Telegram
*before* the handlers run, so a crash mid-reply never replays that message — it is lost.
What *would* be replayed is the backlog from downtime, and with `DROP_PENDING_UPDATES=true`
(the default) that backlog is discarded on start: a command sent hours ago should not run the
moment the bot comes back. The sender sees no reply and re-sends. Set it to `false` for a
personal bot that should catch up instead.

### External Integrations

| Service | Purpose | Protocol | Timeout |
|---------|---------|----------|---------|
| Telegram Bot API | Receive messages / send replies | HTTPS (long-poll) | library default |
| brain (`../brain`) | Get the reply for a message | HTTP `POST /chat` | `BRAIN_TIMEOUT` (60s) |

The bridge holds no database — conversation memory lives in the brain, keyed by
`conversation_id`.

---

## How Is It Deployed?

Runs as a single long-running Python process (`python -m application.main`) under any process
manager — systemd, Docker, a supervisor, etc. Being long-polling, there must be **exactly one
running instance per bot token** (a second copy causes a Telegram `409 Conflict`). Production
topology and provisioning are managed out-of-repo.

### Docker

```sh
docker compose up --build      # set BRAIN_URL in .env so it can reach the brain
```

To run both components in Docker, put both compose projects on a shared network and set
`BRAIN_URL=http://brain:8100`, or point the bridge at the host with
`BRAIN_URL=http://host.docker.internal:8100`.

---

## What Decisions Were Made?

### ADR-001: Split the bridge from the brain (2026-08-05)

**Context**: M1 was a monolith (Telegram + model + memory in one repo).
**Decision**: Keep this component as a Telegram-only bridge that calls the brain over HTTP.
**Trade-off**: Two processes instead of one — accepted, because it isolates Telegram-specific
dependencies/failures and lets one brain serve many bridges (WhatsApp, web) unchanged.

### ADR-002: HTTP to the brain (2026-08-05)

**Context**: Bridge and brain both run locally; was HTTP overhead a concern (vs gRPC / in-process)?
**Decision**: Plain HTTP behind a thin `brain_client`.
**Trade-off**: A network hop, but measured ~0.85 ms on localhost vs a ~4.2 s LLM call
(0.02%) — negligible. HTTP keeps bridges language-agnostic and dependency-isolated;
transport can be swapped in one file later if streaming is ever needed.

### ADR-003: Stateless bridge (2026-08-05)

**Context**: Where should conversation memory live?
**Decision**: In the brain, keyed by `conversation_id`; the bridge stores nothing.
**Trade-off**: The bridge can't work offline from the brain — accepted, since statelessness
is what lets many bridges share one brain and one memory without coordination.

### ADR-004: The bridge is the door — allowlist here, and drop the backlog (2026-09-01)

**Context**: Once a bot answers *as* a named agent that can act on other systems, "who may
message it" is an authorization boundary, and the bridge is the only component in front of
the brain. Separately, replaying downtime backlog would run commands out of their moment.
**Decision**: A per-bot `ALLOWED_CHAT_IDS` checked before any I/O (silent drop, WARNING
log), and `DROP_PENDING_UPDATES` defaulting to true. Neither adds state to the bridge.
**Trade-off**: An unlisted chat gets silence rather than an explanation, and a message sent
while the bot was down is lost rather than answered late — both accepted for an operator
bot; a personal bot can set an empty list and `DROP_PENDING_UPDATES=false`. An `update_id`
dedupe store was rejected: the library already confirms updates before processing, so it
would guard a millisecond window at the cost of the bridge's statelessness.

---

## What's Broken / Known Debts?

### Medium Priority

- **Requires the brain to be running** (`BRAIN_URL`); no offline fallback or retry/backoff.
  *Why*: M2 scope — reliability hardening deferred.

### Known Limitations

- Long-polling only — no webhook mode yet.
- `/start` is the only command; no rich command routing.
- The allowlist is per bot, not per agent: one bridge is one bot is one agent, so they
  coincide today, but a bridge serving several agents would need the list keyed by agent.

---

## License

MIT — see [../../LICENSE](../../LICENSE).
