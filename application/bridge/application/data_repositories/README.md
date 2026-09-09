# data_repositories — the bridge's one piece of storage

The bridge was stateless by design, and mostly still is: conversation memory
lives in the brain (`universal-chat-agent`), keyed by `conversation_id`, and
that is what lets many bridges share one brain without coordinating.

`seen_message_repository.py` is the exception, and it was forced by the
transport rather than chosen. Meta retries a webhook it believes failed, so the
WhatsApp path needs to know which message ids it has already answered. Telegram
never needed this because python-telegram-bot confirms an update batch before
the handlers run — which is why the original decision to skip a dedupe store was
correct then and does not carry over.

The check and the write are deliberately **one statement** (`INSERT OR IGNORE`,
then read `rowcount`), so two concurrent deliveries of the same id can never
both be told they are new. A connection is opened per call rather than held: at
this volume the cost is irrelevant, and it keeps SQLite's thread affinity out of
a process where the caller may be a request handler or a background task.

Nothing else belongs here. If a second thing ever wants storage in the bridge,
that is the moment to ask whether it belongs in the brain instead.
