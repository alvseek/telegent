"""The shared workflow — a photo rides through to the brain, unchanged.

The allowlist decision, the namespaced ids and the chunked reply live here so both
transports inherit them; the photo is carried the same way, as one optional
argument that reaches ``brain.chat`` verbatim.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from application.business_services.forward import forward


def _send(sent):
    async def send(part: str) -> None:
        sent.append(part)

    return send


def _run(brain, text, *, image=None, allowed=None):
    asyncio.run(
        forward(
            platform="telegram",
            chat_key=42,
            user_key=7,
            text=text,
            brain=brain,
            agent_id=None,
            allowlist=allowed,
            send=_send([]),
            image=image,
        )
    )


def test_the_image_reaches_the_brain_verbatim():
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))

    _run(brain, "set the photo on HDMI", image=b"photo-bytes")

    assert brain.chat.await_args.kwargs["image"] == b"photo-bytes"


def test_a_text_turn_carries_no_image():
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))

    _run(brain, "hi")

    assert brain.chat.await_args.kwargs["image"] is None


def test_a_refused_chat_never_reaches_the_brain_even_with_a_photo():
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))

    _run(brain, "set the photo on HDMI", image=b"photo-bytes", allowed=frozenset({999}))

    brain.chat.assert_not_awaited()
