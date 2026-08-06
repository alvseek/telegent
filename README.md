---
doc_type: 7q-readme
---

# telegent

A **self-hosted Telegram AI agent**: a thin Telegram bridge in front of a reusable
chat-agent brain. Message the bot, it remembers your conversation, it replies.

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

telegent is a two-component Telegram agent stack. A stateless **bridge** does Telegram
I/O; a reusable **brain** (its own repo, vendored here as a git submodule) holds the model
and per-conversation memory. They talk over HTTP, so either side can be swapped without
touching the other — and the same brain can back other front-ends (WhatsApp, web) unchanged.

For **anyone self-hosting a personal Telegram assistant** on a reusable agent core.

### Architecture

Two independently-deployed components live under `application/`, each with its own 7Q
README — read those for internals:

| Component | Path | Role |
|---|---|---|
| **Bridge** | [`application/bridge/`](application/bridge/) | Stateless Telegram I/O — long-polls Telegram, tags each message `conversation_id = "telegram:<chat_id>"`, forwards to the brain over HTTP, chunks replies back. |
| **Brain** | [`application/brain/`](application/brain/) *(submodule → [universal-chat-agent](https://github.com/alvseek/universal-chat-agent))* | The reusable agent: `POST /chat {conversation_id, message} -> {reply}`, per-conversation memory. Front-end-agnostic. |

Both components follow the **A-Boxed Level 1** pattern (flat semantic-prefix layers). The
bridge is thin, Telegram-specific glue; the **brain is the reusable asset** (its own repo,
referenced here as a submodule).

```
Telegram ──long-poll──▶ application/bridge ──HTTP POST /chat──▶ application/brain (127.0.0.1:8100)
                              ◀───────────────  {reply}  ───────────────
```

The two never import each other — the only coupling is the HTTP
`{conversation_id, message} → {reply}` contract, so each keeps its own deps and lifecycle.

### Tech Stack

| | Bridge | Brain |
|---|---|---|
| Runtime | Python 3.12+ | Python 3.12+ |
| Framework | python-telegram-bot 22 (long-poll) | FastAPI + uvicorn |
| Talks to | the brain, via httpx | OpenRouter, via pydantic-ai |
| State | none (stateless) | SQLite (per-conversation memory) |

Component-level detail lives in each component's README.

---

## How Do I Set It Up?

### Prerequisites

- Python 3.12+ (`python --version`)
- A Telegram bot token (from **@BotFather**)
- An OpenRouter API key ([openrouter.ai/keys](https://openrouter.ai/keys))

### Setup

1. Clone **recursively** (pulls the brain submodule into `application/brain`):
   ```sh
   git clone --recursive https://github.com/alvseek/telegent.git
   cd telegent
   ```
   Already cloned without `--recursive`? Run `git submodule update --init --recursive`.

2. Bring up the **brain** (see [application/brain/README.md](application/brain/README.md)):
   ```sh
   cd application/brain
   cp .env.example .env          # fill OPENROUTER_API_KEY; set HOST=127.0.0.1, PORT=8100
   uvicorn application.main:app --host 127.0.0.1 --port 8100
   ```

3. Bring up the **bridge** (see [application/bridge/README.md](application/bridge/README.md)):
   ```sh
   cd application/bridge
   cp .env.example .env          # fill TELEGRAM_BOT_TOKEN; set BRAIN_URL=http://127.0.0.1:8100
   python -m application.main
   ```

4. Verify it works: message your bot `/start`, then send any text — it should reply with a
   brain-generated answer. Brain liveness:
   ```sh
   curl -s http://127.0.0.1:8100/health   # {"status":"ok"}
   ```

Each component has its own `.env`, dependencies, and tests — this root README is the map;
the component READMEs are the manuals.

---

## How Do I Use It?

### Commands (per component)

| Where | Command | Description |
|---|---|---|
| `application/brain` | `uvicorn application.main:app --port 8100` | Start the brain |
| `application/brain` | `python -m pytest tests/ -q` | Brain model-free tests |
| `application/bridge` | `python -m application.main` | Start the bridge (long-poll) |
| `application/bridge` | `python -m pytest tests/ -q` | Bridge model-free tests |

### Bot commands

| Command | Description |
|---------|-------------|
| `/start` | Greeting |
| *(any text)* | Forwarded to the brain; reply returned with conversation memory |

---

## How Does It Work Inside?

### Core Flow: message → reply

1. **Receive** (`application/bridge/application/api_controllers/telegram_handler.py`)
   - A text update arrives; the bridge tags it `conversation_id = "telegram:<chat_id>"` —
     the namespacing seam that keeps the brain platform-agnostic.
2. **Forward** (`application/bridge/application/api_integrations/brain/brain_client.py`)
   - `POST {BRAIN_URL}/chat {conversation_id, message}` over a keep-alive httpx client.
3. **Answer** (`application/brain/application/business_services/chat_service.py`)
   - The brain validates the id, loads the recent memory window, runs the model
     (pydantic-ai → OpenRouter), persists the turns, returns `{reply}`.
4. **Reply** (`application/bridge/application/common/message_chunker.py`)
   - The reply is split into ≤4096-char pieces and sent back to the chat.

A brain outage never crashes the bridge — the handler logs the failure and sends a friendly
apology. See each component's README for its own internal map and data model.

### External Integrations

| Service | Called by | Purpose | Protocol |
|---------|-----------|---------|----------|
| Telegram Bot API | bridge | Receive messages / send replies | HTTPS (long-poll) |
| universal-chat-agent (brain) | bridge | Get the reply for a message | HTTP `POST /chat` |
| OpenRouter | brain | The LLM (OpenAI-compatible) | HTTPS |

All conversation memory lives in the brain, keyed by `conversation_id`; the bridge stores
nothing.

---

## How Is It Deployed?

Two **systemd** services co-hosted on the invintiry VPS — **no Docker, no public ingress**
(the bridge long-polls Telegram outbound; the brain listens on loopback only). Full,
copy-pasteable steps in **[deploy/SETUP.md](deploy/SETUP.md)**.

| Service | Runs | Listens |
|---|---|---|
| `telegent-brain` | `uvicorn application.main:app` (from `application/brain`) | `127.0.0.1:8100` |
| `telegent-bridge` | `python -m application.main` (long-poll) | nothing (outbound) |

Provisioning mirrors the invintiry `deploy/` convention (deps via `uv`, a root `setup.sh`
that installs the sudoers grant, `setup-app.sh` / `redeploy.sh` per component). Ops:

```sh
sudo systemctl status telegent-brain telegent-bridge
curl -s http://127.0.0.1:8100/health        # {"status":"ok"}
```

**One instance per bot token** — a second bridge polling the same token gets a Telegram
`409 Conflict`. **CI/CD**: none yet.

> ⚠️ **Production still runs the pre-restructure flat layout.** Migrating the live box onto
> this monorepo is a **coordinated redeploy** (WorkingDirectory + venv location change), not
> a plain `git pull` — see *Migrating the live box* in [deploy/SETUP.md](deploy/SETUP.md).

---

## What Decisions Were Made?

### ADR-001: Split the bridge from the brain (2026-08-05)

**Context**: M1 was a monolith (Telegram + model + memory in one repo).
**Decision**: Extract the agent into `universal-chat-agent` and keep telegent as a
Telegram-only bridge that calls it over HTTP.
**Trade-off**: Two processes instead of one — accepted, because it isolates Telegram-specific
deps/failures and lets one brain serve many bridges (WhatsApp, web) unchanged.

### ADR-002: HTTP between bridge and brain (2026-08-05)

**Context**: Both run locally — was HTTP overhead a concern (vs gRPC / in-process)?
**Decision**: Plain HTTP behind a thin `brain_client`.
**Trade-off**: A network hop, but measured ~0.85 ms on localhost vs a ~4.2 s LLM call
(0.02%) — negligible. HTTP keeps bridges language-agnostic and dependency-isolated.

### ADR-003: Stateless bridge (2026-08-05)

**Context**: Where should conversation memory live?
**Decision**: In the brain, keyed by `conversation_id`; the bridge stores nothing.
**Trade-off**: The bridge can't work offline from the brain — accepted, since statelessness
is what lets many bridges share one brain and one memory without coordination.

### ADR-004: Option-2 monorepo — brain as a submodule (2026-08-06)

**Context**: Where should the bridge and the reusable brain live relative to each other?
**Decision**: One monorepo — the bridge inline at `application/bridge/`, the brain as a **git
submodule** at `application/brain/` (it keeps its own repo and pin). A standalone bridge repo
would be YAGNI.
**Trade-off**: Submodule ceremony (`--recursive` clone, pointer bumps) — accepted, because it
enforces a **one-way dependency structurally**: the parent records only a gitlink; the brain
stays a self-contained repo that knows nothing about telegent, so it can be reused or
relocated freely.

---

## What's Broken / Known Debts?

### Medium Priority

- **Production runs the pre-restructure flat layout.** *Why*: the live box predates the
  monorepo restructure; migrating it is a coordinated redeploy (see [deploy/SETUP.md](deploy/SETUP.md)),
  done deliberately rather than incidentally.
- **The brain submodule's deploy scripts still assume a standalone clone path.** *Why*: they
  need to become **self-locating** (work whether cloned standalone or nested at
  `application/brain`); reconciled during the migration above.
- **No CI/CD** on the repo. *Why*: not built yet.

### Known Limitations

- Long-polling only — no webhook mode; **one running bridge per bot token** (a second copy
  causes a Telegram `409 Conflict`).
- Backlog replay: messages sent while the bridge is offline are delivered on reconnect
  (Telegram queues updates ~24h). Intentional for a personal bot; disable with
  `run_polling(drop_pending_updates=True)` in the bridge's `application/main.py`.
- No auth on the brain's `/chat` — it assumes a trusted local network / same host. Add an API
  key or network policy before exposing it publicly.

---

## License

MIT — see [LICENSE](LICENSE).
