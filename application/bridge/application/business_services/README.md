# business_services — placeholder (A-Boxed L1 full skeleton)

Intentionally minimal. The bridge has almost no business logic: the single
"orchestration" (tag conversation_id → ask brain → reply) is thin enough to
live in the handler. All real orchestration is in the **brain**
(`universal-chat-agent/business_services`).

If the bridge grows non-trivial logic (rate limiting, command routing,
multi-step flows), extract it into a service here.
