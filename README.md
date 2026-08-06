---
doc_type: 7q-readme
---

# telegent

Monorepo for the **Telegram agent stack**: a thin Telegram bridge + a reusable chat-agent brain.

## What is this?
telegent connects Telegram to an AI chat-agent brain. It is split into two independently-deployed components:

| Component | Path | What it does |
|---|---|---|
| **Bridge** | [`application/bridge/`](application/bridge/) | Stateless Telegram I/O — long-polls Telegram, tags each message with `conversation_id = "telegram:<chat_id>"`, forwards to the brain over HTTP, chunks replies back. |
| **Brain** | [`application/brain/`](application/brain/) *(git submodule → [universal-chat-agent](https://github.com/alvseek/universal-chat-agent))* | The reusable agent brain: `POST /chat {conversation_id, message} -> {reply}`, per-conversation memory. Front-end-agnostic (a WhatsApp bridge could reuse it). |

The bridge is thin, Telegram-specific glue; the **brain is the reusable asset** (its own repo, referenced here as a submodule). See [deploy/SETUP.md](deploy/SETUP.md) for the deployment story and the M3 direction (multi-tenant agent runtime).

## Setup
Clone recursively (pulls the brain submodule):
```bash
git clone --recursive https://github.com/alvseek/telegent.git
```
Then follow [deploy/SETUP.md](deploy/SETUP.md). Each component has its own `.env`, deps, and tests — see [application/bridge/README.md](application/bridge/README.md) for the bridge.

## How it works
```
Telegram ──long-poll──▶ application/bridge ──HTTP POST /chat──▶ application/brain (127.0.0.1:8100)
```
Bridge and brain do not import each other — they talk over HTTP, so each has its own deps and lifecycle.

## Deployment
Two systemd services co-hosted on the invintiry VPS (no Docker, no public ingress). See [deploy/SETUP.md](deploy/SETUP.md).

## What's broken / in progress
- **Production runs the pre-restructure flat layout** — migrating the live box onto this monorepo is a coordinated redeploy (see the migration section in [deploy/SETUP.md](deploy/SETUP.md)).
- Brain-side deploy scripts still assume the standalone clone path; reconciling them onto `application/brain` is part of the planned `telegent-deploy` work.
- No CI/CD yet.

## License
MIT — see [LICENSE](LICENSE).
