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

The **chat-platform bridges** of the telegent stack (the monorepo root is [`../../`](../../README.md)).
Thin pipes: they receive messages from a chat platform, forward them to the brain
([`../brain`](../brain)) over HTTP, and send the brain's reply back. They hold **almost no
intelligence and no conversation memory** — swap the brain's model or wipe its database and
these bridges don't change.

One application, **two transports, two processes**:

| Transport | Entry point | How messages arrive | Public ingress |
|---|---|---|---|
| Telegram | `application/main_telegram.py` | long-polls Telegram, outbound only | none |
| WhatsApp | `application/main_whatsapp.py` | Meta POSTs to a webhook | HTTPS, reverse-proxied |

They share everything that is not vendor-specific — the brain client, the allowlist rule, the
message chunker, and the workflow itself — and run as separate processes because their
runtime shapes differ: one dials out and waits, the other sits still and is dialled into.

For **anyone self-hosting a chat front-end** onto a reusable chat agent.

### Architecture

Follows the **A-Boxed Level 1** pattern (flat semantic-prefix layers). The bridge holds no
conversation state; its only storage is a table of WhatsApp message ids already answered,
which exists because Meta retries deliveries (see ADR-005).

```
Telegram ──poll──▶ api_controllers/telegram_handler ─┐
                                                     ├─▶ business_services/forward
Meta ────push────▶ api_controllers/whatsapp_handler ─┘        │
                   (FastAPI on loopback)                      │  business_domain/access_policy: allowed?
                        ▲                                     │  conversation_id = "<platform>:<id>"
                        │                                     ▼
                 reverse proxy (TLS)              api_integrations/brain/brain_client
                                                              │  HTTP POST /chat
                                                              ▼
                                                        brain (../brain)
```

Both handlers converge on `forward` within a few lines of receiving a message. Everything
below that line is one implementation, so the allowlist decision, the platform-namespaced
ids, the brain call and the chunked reply cannot drift apart between transports.

### Tech Stack

- **Runtime**: Python 3.12+
- **Telegram**: python-telegram-bot 22 (long-polling)
- **WhatsApp**: FastAPI + uvicorn (webhook), Meta Graph API for sending
- **HTTP client**: httpx (keep-alive connections to the brain and to Meta)
- **Storage**: SQLite, one table, WhatsApp only
- **Config**: python-dotenv

---

## How Do I Set It Up?

### Prerequisites

- Python 3.12+ (`python --version`)
- A running brain ([`../brain`](../brain)) reachable over HTTP
- For Telegram: a bot token from @BotFather
- For WhatsApp: a WhatsApp Business number on the Cloud API, a permanent System User token,
  the app secret, and a public HTTPS hostname that reverse-proxies to this process

### Setup

Run from this component's folder (`application/bridge`):

1. Install:
   ```sh
   cd application/bridge
   python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Get your credentials. Telegram: message **@BotFather** → `/newbot` → copy the token.
   WhatsApp: **Business Settings → Users → System users → Generate new token** with
   `whatsapp_business_messaging`; the temporary dashboard token expires in about a day and
   is not usable for a service.

3. Configure environment:
   ```sh
   cp .env.example .env
   # Edit .env — see Environment Variables below
   ```

4. Start whichever transports you want, with the brain already running:
   ```sh
   python -m application.main_telegram
   python -m application.main_whatsapp
   ```

5. For WhatsApp, point Meta at the webhook: **WhatsApp → Configuration → Webhook**, callback
   URL `https://<your-host>/webhook`, verify token matching `WHATSAPP_VERIFY_TOKEN`, then
   subscribe to **messages** under Webhook fields. The subscription is a separate click and
   is the step that gets forgotten — without it the URL verifies and nothing ever arrives.

### Environment Variables

Both processes read the same `.env` and ignore what they do not recognise, so a Telegram-only
deployment simply leaves the WhatsApp block out.

**Shared**

| Variable | Description | Example |
|----------|-------------|---------|
| `BRAIN_URL` | Base URL of the running brain | `http://127.0.0.1:8100` |
| `BRAIN_TIMEOUT` | Seconds to wait for a brain reply (LLM is slow) | `60` |
| `AGENT_ID` | Which agent these bots *are* (sent on every `/chat`); empty = the brain's default agent | `invintiry-operator` |

**Telegram**

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather (required) | `123456:ABC-...` |
| `ALLOWED_CHAT_IDS` | Comma-separated chat ids that may talk to this bot; empty = anyone | `8932435376,-100123` |
| `DROP_PENDING_UPDATES` | Discard messages queued while the bridge was down | `true` (default) |

**WhatsApp**

| Variable | Description | Example |
|----------|-------------|---------|
| `WHATSAPP_ACCESS_TOKEN` | Permanent System User token (required) | `EAA...` |
| `WHATSAPP_PHONE_NUMBER_ID` | The sending number's id, not the number (required) | `1302139689652749` |
| `WHATSAPP_APP_SECRET` | Verifies `X-Hub-Signature-256` on every webhook (required) | 32 hex chars |
| `WHATSAPP_VERIFY_TOKEN` | Your own string, echoed during Meta's handshake (required) | `any-random-string` |
| `WHATSAPP_ALLOWED_IDS` | Comma-separated sender numbers, no plus; empty = anyone | `6282311020200` |
| `WHATSAPP_HOST` / `WHATSAPP_PORT` | Where this process listens | `127.0.0.1` / `8200` |
| `WHATSAPP_DB_PATH` | SQLite file of message ids already answered | `whatsapp.db` |
| `WHATSAPP_API_VERSION` | Graph API version, pinned deliberately | `v22.0` |

> Put comments on their **own line** in `.env`. python-dotenv ends an unquoted value at a
> whitespace-preceded `#`, so `WHATSAPP_ALLOWED_IDS=   # leave empty` makes the comment the
> value. A key with a real value in front of the `#` is fine; an empty one is not.

Your own Telegram chat id appears in the log the first time you message the bot from an
unlisted account (`refused chat <id>`), or in the brain's conversation ids
(`<agent>:telegram:<id>`).

---

## How Do I Use It?

### Commands

| Command | Description |
|---------|-------------|
| `python -m application.main_telegram` | Start the Telegram bridge (long-polling) |
| `python -m application.main_whatsapp` | Start the WhatsApp bridge (webhook server) |
| `python -m pytest tests/ -q` | Run model-free tests |

### Bot commands

| Command | Description |
|---------|-------------|
| `/start` | Forwarded to the brain; carries a link code when one is present |
| *(any text)* | Forwarded to the brain; reply returned with conversation memory |

On Telegram a deep link delivers `/start <code>` automatically. WhatsApp has no deep-link
equivalent, so the same code is typed by hand as an ordinary message — the brain parses it
either way.

---

## How Does It Work Inside?

### Core Flow: message → reply

Both transports end up in the same place.

1. **Receive** (`api_controllers/telegram_handler.py` or `whatsapp_handler.py`)
   - Telegram: an update arrives from the long poll. WhatsApp: Meta POSTs to `/webhook`.
   - Each handler unwraps the two ids its platform provides and calls `forward`.
2. **Admit, ask, reply** (`business_services/forward.py`)
   - The chat is checked against the allowlist. An unlisted caller gets **no** typing
     indicator, **no** brain call and **no** reply — only a WARNING with its id.
   - `conversation_id = "<platform>:<chat>"` and `end_user_id = "<platform>:<user>"`. They
     differ in a Telegram group and coincide in a WhatsApp one-to-one chat, and credentials
     follow the **person**.
   - `POST {BRAIN_URL}/chat` over a keep-alive httpx client.
   - The reply is split into ≤4096-char pieces and sent back through the transport.
3. **Failures never escape.** Any error is logged and answered with one apology, so a brain
   outage degrades a conversation instead of crashing the process.

### The WhatsApp webhook, in order

The order is the design, not an implementation detail:

1. **Verify `X-Hub-Signature-256` over the raw bytes.** With an open allowlist this URL is
   otherwise an unauthenticated endpoint that turns POSTs into model calls. The HMAC must be
   computed over exactly what arrived — re-serialising the parsed JSON produces different
   bytes and never matches.
2. **Acknowledge with 200 before doing any work.** Meta redelivers anything it does not see
   acknowledged quickly, and a brain turn takes seconds. The reply is sent from a background
   task.
3. **Deduplicate before scheduling.** A redelivery arriving while the first is still being
   answered has to be dropped at the door; checking inside the task would let both through.

Payloads carrying `statuses` rather than `messages` are delivery receipts for messages *we*
sent, and are dropped — answering one would mean replying to ourselves. Media, stickers and
button taps have no `text.body` and are ignored, matching Telegram's treatment of non-text.

### Messages sent while a bridge is down

Telegram queues updates for ~24 h, and `DROP_PENDING_UPDATES=true` (the default) discards
that backlog on start: a command sent hours ago should not run the moment the bot comes
back. Meta retries a failed webhook for a while and then gives up; a message that arrives
while the WhatsApp bridge is down is lost, and the sender re-sends.

### External Integrations

| Service | Purpose | Protocol | Timeout |
|---------|---------|----------|---------|
| Telegram Bot API | Receive / send | HTTPS long-poll | library default |
| WhatsApp Cloud API | Receive (inbound webhook) / send (Graph API) | HTTPS | 30 s on send |
| brain (`../brain`) | Get the reply for a message | HTTP `POST /chat` | `BRAIN_TIMEOUT` |

Conversation memory lives in the brain, keyed by `conversation_id`.

---

## How Is It Deployed?

Each transport runs as its own long-running process under any process manager. Being
long-polling, Telegram must have **exactly one instance per bot token** (a second copy causes
a `409 Conflict`).

The WhatsApp process listens on **loopback** and expects a reverse proxy to terminate TLS for
a public hostname and forward to it. Meta will not accept a plain-HTTP callback URL, and
exposing this process directly would put an unauthenticated port on the internet.

Production topology and provisioning are managed out-of-repo.

### Docker

```sh
docker compose up --build      # set BRAIN_URL in .env so it can reach the brain
```

To run components in Docker, put them on a shared network and set `BRAIN_URL=http://brain:8100`,
or point at the host with `BRAIN_URL=http://host.docker.internal:8100`.

---

## What Decisions Were Made?

### ADR-001: Split the bridge from the brain (2026-08-05)

**Context**: M1 was a monolith (Telegram + model + memory in one repo).
**Decision**: Keep this component as a transport-only bridge that calls the brain over HTTP.
**Trade-off**: Two processes instead of one — accepted, because it isolates platform-specific
dependencies/failures and lets one brain serve many bridges unchanged. Adding WhatsApp in
2026-09 cost the brain zero changes, which is this decision being collected on.

### ADR-002: HTTP to the brain (2026-08-05)

**Context**: Bridge and brain both run locally; was HTTP overhead a concern (vs gRPC / in-process)?
**Decision**: Plain HTTP behind a thin `brain_client`.
**Trade-off**: A network hop, but measured ~0.85 ms on localhost vs a ~4.2 s LLM call
(0.02%) — negligible. HTTP keeps bridges language-agnostic and dependency-isolated.

### ADR-003: Stateless bridge (2026-08-05) — *partially superseded by ADR-005*

**Context**: Where should conversation memory live?
**Decision**: In the brain, keyed by `conversation_id`; the bridge stores nothing.
**Trade-off**: The bridge can't work offline from the brain — accepted, since statelessness
is what lets many bridges share one brain without coordination. **Still true of conversation
state**; ADR-005 carves out one exception that is not conversation state.

### ADR-004: The bridge is the door — allowlist here, and drop the backlog (2026-09-01) — *dedupe clause superseded by ADR-005*

**Context**: Once a bot answers *as* a named agent that can act on other systems, "who may
message it" is an authorization boundary, and the bridge is the only component in front of
the brain. Separately, replaying downtime backlog would run commands out of their moment.
**Decision**: A per-bot allowlist checked before any I/O (silent drop, WARNING log), and
`DROP_PENDING_UPDATES` defaulting to true.
**Trade-off**: An unlisted chat gets silence rather than an explanation, and a message sent
while the bot was down is lost rather than answered late — both accepted. This ADR also
rejected an `update_id` dedupe store on the grounds that python-telegram-bot confirms updates
before processing, so it would guard a millisecond window; **that reasoning is specific to
Telegram's library and does not transfer to a push transport** — see ADR-005.

### ADR-005: One table of answered message ids, for WhatsApp only (2026-09-09)

**Context**: Meta redelivers a webhook whose acknowledgement it did not see in time, carrying
the same `wamid`. Without a record, a redelivery is a second model call and a second reply to
a customer who asked once — and for an agent that can move stock, potentially a repeated
write.
**Decision**: A SQLite table of seen message ids with a 48-hour retention window, written by
the WhatsApp handler **before** the reply is scheduled. The check and the write are one
`INSERT OR IGNORE` statement, so two concurrent deliveries of the same id cannot both be told
they are new.
**Trade-off**: The bridge is no longer literally stateless, which contradicts ADR-003's
wording and ADR-004's dedupe rejection. Both were right for a transport that does not retry.
The exception is deliberately narrow — one table, one reason, no conversation state — and
Telegram still writes nothing. A connection is opened per call rather than held, which costs
nothing at this volume and keeps SQLite's thread affinity out of a process where the caller
may be a request handler or a background task.

---

## What's Broken / Known Debts?

### High Priority

- **No cost control in front of the model.** With an open allowlist, any stranger who finds
  the bot spends the operator's LLM budget, and account linking does not prevent it — the
  model call happens before anyone checks who is asking. Needed before the number or the
  handle is published.

### Medium Priority

- **Requires the brain to be running** (`BRAIN_URL`); no offline fallback or retry/backoff.
- **A WhatsApp reply is fire-and-forget.** If Meta refuses the send, the failure is logged
  and the customer sees nothing; there is no retry.
- **`/start <code>` linking has never been exercised over WhatsApp**, only over Telegram.

### Known Limitations

- Telegram is long-polling only — no webhook mode. WhatsApp is webhook only; the Cloud API
  offers no polling.
- Media, voice notes and stickers are ignored rather than answered.
- The allowlist is per bot, not per agent: one bridge is one bot is one agent, so they
  coincide today, but a bridge serving several agents would need the list keyed by agent.
- WhatsApp free-form replies only work inside the 24-hour window opened by the customer's
  own message. Messaging someone first requires an approved template, which this bridge does
  not implement.

---

## License

Apache License 2.0 — see [../../LICENSE](../../LICENSE) and [../../NOTICE](../../NOTICE).
