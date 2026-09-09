"""Presentation layer: the two HTTP routes Meta talks to. Pure I/O — no brain.

This is the structural difference between the transports. Telegram dials out and
asks for updates; WhatsApp only ever dials in, so this half of the bridge is a
web server and everything below follows from that.

``GET /webhook`` is Meta's one-time handshake and runs once, at registration.
``POST /webhook`` carries every message afterwards, and its order is deliberate:

1. **Verify the signature over the raw body.** With the allowlist open, this URL
   is otherwise an unauthenticated endpoint that turns POSTs into model calls
   somebody else pays for. The HMAC must be computed over the exact bytes
   received — re-serialising the parsed JSON produces different bytes and will
   never match.
2. **Acknowledge before doing any work.** Meta redelivers anything it does not
   see acknowledged quickly, and a brain turn takes four to fifteen seconds. So
   the reply is sent from a background task and the 200 goes out first.
3. **Deduplicate before scheduling, not inside the task.** A redelivery that
   arrives while the first is still thinking must be dropped at the door;
   checking inside the task would let both through.

Whatever is left is handed to ``business_services.forward``, which both
transports share — so the allowlist decision, the namespaced ids and the chunked
reply are the same code that serves Telegram.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from application.business_services.forward import forward

log = logging.getLogger("telegent")

PLATFORM = "whatsapp"
SIGNATURE_HEADER = "X-Hub-Signature-256"

router = APIRouter()


def signature_ok(secret: str, raw_body: bytes, header: str | None) -> bool:
    """Whether this body really came from Meta.

    Compared with ``compare_digest`` rather than ``==`` so the comparison does
    not leak, byte by byte, how much of a forged signature was correct.
    """
    if not header:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


def extract_message(payload: dict) -> dict | None:
    """Pull the one text message out of a webhook, or None if there isn't one.

    Meta delivers several unrelated things down this route. A payload carrying
    ``statuses`` is a delivery receipt for something *we* sent — the sent /
    delivered / read lifecycle — and answering one would mean replying to
    ourselves. Media, stickers and button taps arrive with no ``text.body`` and
    are ignored, matching what the Telegram side does with a non-text update.
    """
    try:
        value = payload["entry"][0]["changes"][0]["value"]
    except (KeyError, IndexError, TypeError):
        return None
    messages = value.get("messages")
    if not messages:
        return None
    message = messages[0]
    body = (message.get("text") or {}).get("body")
    sender = message.get("from")
    wamid = message.get("id")
    if not body or not sender or not wamid:
        return None
    return {"wamid": wamid, "sender": sender, "text": body}


@router.get("/webhook", response_class=PlainTextResponse)
async def verify(
    request: Request,
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
) -> PlainTextResponse:
    """Meta's handshake: echo the challenge back as plain text, or refuse.

    The response must be the bare challenge. Returning it as JSON — quoted —
    fails verification with no explanation, which is a long afternoon if you do
    not already know.
    """
    expected = request.app.state.config.verify_token
    if hub_mode == "subscribe" and hub_verify_token and hmac.compare_digest(
        hub_verify_token, expected
    ):
        log.info("webhook handshake accepted")
        return PlainTextResponse(hub_challenge or "")
    log.warning("webhook handshake refused: mode=%r token mismatch", hub_mode)
    raise HTTPException(status_code=403, detail="verification failed")


@router.post("/webhook")
async def receive(request: Request, background: BackgroundTasks) -> PlainTextResponse:
    state = request.app.state
    raw = await request.body()

    if not signature_ok(
        state.config.app_secret, raw, request.headers.get(SIGNATURE_HEADER)
    ):
        log.warning("rejected webhook: bad or missing %s", SIGNATURE_HEADER)
        raise HTTPException(status_code=403, detail="bad signature")

    try:
        payload = json.loads(raw)
    except ValueError:
        # Acknowledged deliberately: a body that will not parse now will not
        # parse on redelivery either, so refusing it only earns retries.
        log.warning("webhook body was not JSON; acknowledged and dropped")
        return PlainTextResponse("ok")

    message = extract_message(payload)
    if message is None:
        return PlainTextResponse("ok")

    if not state.seen.mark_seen(message["wamid"]):
        log.info("duplicate delivery ignored: %s", message["wamid"])
        return PlainTextResponse("ok")

    background.add_task(handle_message, state, message)
    return PlainTextResponse("ok")


async def handle_message(state, message: dict) -> None:
    """Run one delivered message through the shared workflow."""
    sender = message["sender"]
    try:
        chat_key = int(sender)
    except (TypeError, ValueError):
        # A wa_id is a phone number in international form; anything else is a
        # shape we do not understand, and guessing at it is worse than dropping.
        log.warning("dropped message from an unparseable sender: %r", sender)
        return

    async def send(part: str) -> None:
        await state.whatsapp.send_text(sender, part)

    async def on_admitted() -> None:
        await state.whatsapp.mark_read(message["wamid"])

    await forward(
        platform=PLATFORM,
        chat_key=chat_key,
        # In a one-to-one WhatsApp chat the room and the person are the same
        # thing, unlike a Telegram group where they diverge.
        user_key=chat_key,
        text=message["text"],
        brain=state.brain,
        agent_id=state.config.agent_id,
        allowlist=state.config.allowed_ids,
        send=send,
        on_admitted=on_admitted,
    )
