# business_services — the one workflow both transports share

This layer was a near-empty placeholder while there was a single transport, on the
reasoning that one orchestration — tag the conversation, ask the brain, reply — was
thin enough to live in the handler. That was true right up until a second transport
arrived, at which point an inlined workflow is a *copied* workflow.

`forward.py` is that workflow, and it is the whole layer. It owns the allowlist
decision, the platform-namespaced `conversation_id` and `end_user_id`, the brain
call, the chunked reply, and the catch-all apology that stops a bad turn from
crashing the process.

Everything platform-shaped is passed in rather than branched on: `send` is how this
transport puts text in front of a person, and `on_admitted` is whatever it does once
a caller is let through — Telegram shows a typing indicator, WhatsApp marks the
message read. Adding a third transport should mean writing a handler and passing two
callables, not touching this file.
