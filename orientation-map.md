---
project: "telegent"
description: "Orientation map for the telegent product monorepo — the Telegram bridge, its A-Boxed layer notes, and a link to the brain's own map."
created: "2026-09-09"
last_full_scan: "2026-09-09"
---

# Orientation Map — telegent (product monorepo)

Index of orientation artifacts in this repo. Used by agents at awakening and refreshed at
wrap-up via the `/map-orientation` skill. Entry paths are relative to this repo's root.

This repo is a **submodule** of a private deploy repo and itself contains the brain as a
further submodule (`application/brain` → github.com/alvseek/universal-chat-agent). This map
is self-contained: nothing here depends on the parent, so a standalone clone can use it.

**Where the decisions live:** there is no `docs/adr/` folder. The ADRs are written into the
component READMEs — `application/bridge/README.md` carries ADR-001 through ADR-004 in its
*What Decisions Were Made?* section, and the brain's README does the same for its own.

## Status Legend

- **useful** — current, accurate, future tasks will rely on it.
- **stale-but-valuable** — could be useful if updated. Repair when a task hits its scope.
- **obsolete** — neither current nor valuable. Ignore.
- **unverified** — never verified, or mtime changed since `last_verified`.

## Scope Legend

Single-role repo: every entry is `shared` with empty `roles`, so the role filter is a no-op.

---

## Entries

### `README.md`

- **type**: 7q-readme
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [overview, entry-point, stack]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: ""
- **notes**: "Monorepo root README. A self-hosted Telegram AI agent: a thin stateless bridge doing Telegram I/O in front of a reusable chat-agent brain. Start here for the two-component picture."

### `application/bridge/README.md`

- **type**: 7q-readme
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [bridge, telegram, adr, entry-point, allowlist]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: ""
- **notes**: "The Telegram bridge — a stateless pipe holding no intelligence and no memory. Carries ADR-001 (split bridge from brain), ADR-002 (HTTP to the brain, measured 0.85ms vs a 4.2s LLM call), ADR-003 (stateless bridge), ADR-004 (the bridge is the door: allowlist here, drop the backlog). Names a WhatsApp/web bridge as the intended second case and records 'long-polling only, no webhook mode yet' as a known limitation."

### `application/bridge/application/api_dto/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [a-boxed, placeholder, layer]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: ""
- **notes**: "A-Boxed L1 placeholder, intentionally empty. The bridge defines no request/response contracts of its own — it speaks the brain's contract."

### `application/bridge/application/business_domain/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [a-boxed, layer, domain, access-policy]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: ""
- **notes**: "The one layer here that is not empty: the bridge's only domain rule is which chats may talk to this bot (access_policy.py, pure functions). Conversation rules live in the brain."

### `application/bridge/application/business_services/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [a-boxed, placeholder, layer]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: ""
- **notes**: "A-Boxed L1 placeholder, intentionally minimal. The single orchestration — tag conversation_id, ask brain, reply — is thin enough to live in the handler."

### `application/bridge/application/data_entities/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [a-boxed, placeholder, layer, stateless]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: ""
- **notes**: "A-Boxed L1 placeholder, intentionally empty — the bridge persists nothing. Persisted shapes live in the brain."

### `application/bridge/application/data_repositories/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [a-boxed, placeholder, layer, stateless]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: ""
- **notes**: "A-Boxed L1 placeholder, intentionally empty — the bridge is stateless by design. Conversation memory lives in the brain, keyed by conversation_id."

### `application/bridge/application/middleware/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: unverified
- **tags**: [a-boxed, placeholder, layer, http]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: ""
- **notes**: "A-Boxed L1 placeholder, intentionally empty because the bridge runs no HTTP server, so there are no routes to wrap. Read this before adding a push-based bridge: a webhook transport does run a server, and this layer stops being a placeholder."

### `application/brain/` (sub-project)

- **type**: orientation-map-link
- **scope**: shared
- **roles**: []
- **status**: unverified
- **child_map**: application/brain/orientation-map.md
- **tags**: [submodule, brain, reusable, universal-chat-agent]
- **last_verified**: ""
- **verified_by**: ""
- **update_trigger**: ""
- **notes**: "The brain, vendored as a submodule from github.com/alvseek/universal-chat-agent. Bridge-agnostic by design and reusable on its own, which is why it carries its own map."

---

## How to Use This File

Load this map alongside the repo. For the `orientation-map-link` entry, also load the brain's
map. This map never references its parent — a standalone clone is fully served by what is here.
