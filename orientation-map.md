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
- **status**: useful
- **tags**: [overview, entry-point, stack]
- **last_verified**: "2026-09-09"
- **verified_by**: "software-architect / 2026-09-09 WhatsApp transport session"
- **update_trigger**: ""
- **notes**: "Monorepo root README. A self-hosted Telegram AI agent: a thin stateless bridge doing Telegram I/O in front of a reusable chat-agent brain. Start here for the two-component picture."

### `application/bridge/README.md`

- **type**: 7q-readme
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [bridge, telegram, adr, entry-point, allowlist]
- **last_verified**: "2026-09-09"
- **verified_by**: "software-architect / 2026-09-09 WhatsApp transport session"
- **update_trigger**: ""
- **notes**: "The bridges - two transports, one application, two processes. Rewritten 2026-09-09. Carries ADR-001 to ADR-004 plus ADR-005, which records the one dedupe table and names exactly which clauses of ADR-003 and ADR-004 it supersedes. The high-priority debt at the bottom is real: no cost control stands in front of the model."

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
- **status**: useful
- **tags**: [a-boxed, placeholder, layer]
- **last_verified**: "2026-09-09"
- **verified_by**: "software-architect / 2026-09-09 WhatsApp transport session"
- **update_trigger**: ""
- **notes**: "No longer a placeholder. Holds forward.py, the one workflow both transports share - the allowlist decision, the namespaced ids, the brain call, the chunked reply and the apology."

### `application/bridge/application/data_entities/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [a-boxed, placeholder, layer, stateless]
- **last_verified**: "2026-09-09"
- **verified_by**: "software-architect / 2026-09-09 WhatsApp transport session"
- **update_trigger**: ""
- **notes**: "One shape, added 2026-09-09: a WhatsApp message id already answered. Nearly empty by design; conversation state still lives in the brain."

### `application/bridge/application/data_repositories/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [a-boxed, placeholder, layer, stateless]
- **last_verified**: "2026-09-09"
- **verified_by**: "software-architect / 2026-09-09 WhatsApp transport session"
- **update_trigger**: ""
- **notes**: "The bridge's only storage, added 2026-09-09 because Meta retries webhooks. INSERT OR IGNORE makes the check and the write atomic. Telegram still writes nothing."

### `application/bridge/application/middleware/README.md`

- **type**: other
- **scope**: shared
- **roles**: []
- **status**: useful
- **tags**: [a-boxed, placeholder, layer, http]
- **last_verified**: "2026-09-09"
- **verified_by**: "software-architect / 2026-09-09 WhatsApp transport session"
- **update_trigger**: ""
- **notes**: "Still empty, but for a narrower reason since 2026-09-09: the bridge DOES run an HTTP server now. Signature verification sits in the route because it needs the raw body, and error handling sits in forward.py so both transports inherit it."

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
