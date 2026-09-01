# business_domain — the bridge's own rules (A-Boxed L1)

The bridge has almost no domain of its own — conversation rules live in the
**brain** (`../brain/application/business_domain`), and message chunking is a
generic utility that lives in `common/`. The one rule that is genuinely the
bridge's is *who may talk to this bot*, because the bridge is the only thing
standing between a Telegram chat and the brain:

- `access_policy.py` — `parse_allowlist()` turns `ALLOWED_CHAT_IDS` into an
  allowlist (`None` = open), and `is_allowed()` answers for one chat id. Pure
  functions, no I/O, tested without Telegram.
