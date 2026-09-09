# data_entities — one shape, and only because a transport forced it

Nearly empty by design. Conversation state lives in the brain
(`universal-chat-agent/data_entities`), keyed by `conversation_id`, and the
bridge holds none of it.

The single exception is `seen_message.py`: a WhatsApp message id the bridge has
already answered. Meta redelivers a webhook whose acknowledgement it did not see
in time, and the redelivery carries the same `wamid` — so without a record of
what has been answered, one question from a customer becomes two replies. The
row's *presence* is the decision; its `seen_at` exists only so the table can be
pruned.

Telegram needs no equivalent, which is why this layer stayed empty for as long
as there was one transport.
