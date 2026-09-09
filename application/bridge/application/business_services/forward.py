"""The bridge's one workflow: admit a caller, ask the brain, send the reply.

This lived inside the Telegram handler while there was one transport, which is
what this layer's README said was fine — "the single orchestration is thin
enough to live in the handler." A second transport is the event that ended
that: with two handlers, an inlined workflow is a copied workflow, and the
platform namespacing, the allowlist decision, the brain call and the chunking
would drift apart one bug fix at a time.

Everything transport-specific arrives as an argument. ``send`` is how this
transport puts text in front of a person; ``on_admitted`` is whatever the
transport does once a caller is let through and before the wait begins —
Telegram shows a typing indicator, WhatsApp has nothing to show and passes
nothing.

The allowlist check lives here rather than in each handler because the property
ADR-004 actually cares about is that a refused caller costs *no* I/O: no
indicator, no brain call, no reply, one WARNING naming the id. Keeping that in
one place is what stops a second transport implementing three quarters of it.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from application.business_domain.access_policy import Allowlist, is_allowed
from application.common.message_chunker import chunk

log = logging.getLogger("telegent")

Send = Callable[[str], Awaitable[None]]
OnAdmitted = Callable[[], Awaitable[None]]

APOLOGY = "Sorry — something went wrong. Please try again."


async def forward(
    *,
    platform: str,
    chat_key: int,
    user_key: Any | None,
    text: str,
    brain: Any,
    agent_id: str | None,
    allowlist: Allowlist,
    send: Send,
    on_admitted: OnAdmitted | None = None,
) -> None:
    """Run one message through the brain and send back what comes out.

    ``chat_key`` is the room and ``user_key`` is the person. They differ in a
    Telegram group and coincide in a WhatsApp one-to-one chat, and they are not
    interchangeable: credentials belong to a person, so anything acting on
    someone's behalf keys off ``user_key``. A message with no identifiable
    sender forwards no caller at all rather than guessing one.

    Failures never escape. The brain being down, the transport refusing a send,
    an unexpected payload — all of it degrades to one apology and one logged
    traceback, because a bridge that crashes on a bad turn stops serving every
    other conversation too.
    """
    if not is_allowed(chat_key, allowlist):
        log.warning("refused chat %s: not in the %s allowlist", chat_key, platform)
        return

    conversation_id = f"{platform}:{chat_key}"
    end_user_id = None if user_key is None else f"{platform}:{user_key}"

    try:
        if on_admitted is not None:
            await on_admitted()
        reply = await brain.chat(
            conversation_id,
            text,
            agent_id=agent_id,
            end_user_id=end_user_id,
        )
        for part in chunk(reply):
            await send(part)
    except Exception:
        log.exception("failed to handle message in %s", conversation_id)
        await send(APOLOGY)
