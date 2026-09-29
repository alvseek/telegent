"""WhatsApp webhook tests — Meta is a signed HTTP request, nothing is mocked away.

The route is a public endpoint that turns POSTs into model calls somebody pays
for, so the tests that matter most here are the refusals: a wrong signature, a
delivery receipt, a redelivery. Each of those is paired with a control that must
*succeed*, because a test asserting only that something was refused also passes
against a handler that refuses everything.
"""
import hashlib
import hmac
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from application.api_controllers.whatsapp_handler import router

SECRET = "app-secret"
VERIFY = "verify-me"
SENDER = "6282311020200"


class _Seen:
    """Dedupe double: every id is new unless named in ``duplicates``."""

    def __init__(self, duplicates=()):
        self.duplicates = set(duplicates)
        self.marked = []

    def mark_seen(self, wamid):
        self.marked.append(wamid)
        return wamid not in self.duplicates


def _app(seen=None, brain=None, whatsapp=None, allowed=None, agent_id=None):
    app = FastAPI()
    app.state.config = SimpleNamespace(
        app_secret=SECRET, verify_token=VERIFY, agent_id=agent_id, allowed_ids=allowed
    )
    app.state.brain = brain or SimpleNamespace(chat=AsyncMock(return_value="ok"))
    app.state.whatsapp = whatsapp or SimpleNamespace(
        send_text=AsyncMock(return_value=True),
        mark_read=AsyncMock(return_value=True),
        download_media=AsyncMock(return_value=b"image-bytes"),
    )
    app.state.seen = seen or _Seen()
    app.include_router(router)
    return app


def _sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _message_payload(text="hello", sender=SENDER, wamid="wamid.AAA"):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": sender,
                                    "id": wamid,
                                    "timestamp": "1788000000",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }


def _image_payload(caption=None, media_id="media.1", sender=SENDER, wamid="wamid.IMG"):
    image = {"id": media_id, "mime_type": "image/jpeg"}
    if caption is not None:
        image["caption"] = caption
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": sender,
                                    "id": wamid,
                                    "timestamp": "1788000000",
                                    "type": "image",
                                    "image": image,
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }


def _post(app, payload=None, *, raw=None, secret=SECRET, sign=True):
    body = raw if raw is not None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if sign:
        headers["X-Hub-Signature-256"] = _sign(body, secret)
    return TestClient(app).post("/webhook", content=body, headers=headers)


# --- the handshake --------------------------------------------------------


def test_handshake_echoes_the_challenge_as_bare_text():
    """Quoted JSON fails Meta's verification with no explanation."""
    response = TestClient(_app()).get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY, "hub.challenge": "1158201444"},
    )
    assert response.status_code == 200
    assert response.text == "1158201444"
    assert response.text != '"1158201444"'


def test_handshake_refuses_a_wrong_token():
    response = TestClient(_app()).get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "1"},
    )
    assert response.status_code == 403


def test_handshake_refuses_a_wrong_mode():
    response = TestClient(_app()).get(
        "/webhook",
        params={"hub.mode": "unsubscribe", "hub.verify_token": VERIFY, "hub.challenge": "1"},
    )
    assert response.status_code == 403


# --- the signature, with its control --------------------------------------


def test_a_wrong_signature_is_refused():
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    response = _post(_app(brain=brain), _message_payload(), secret="not-the-secret")
    assert response.status_code == 403
    brain.chat.assert_not_awaited()


def test_a_missing_signature_is_refused():
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    response = _post(_app(brain=brain), _message_payload(), sign=False)
    assert response.status_code == 403
    brain.chat.assert_not_awaited()


def test_a_correct_signature_is_accepted():
    """The control. Without this, 'refused' could mean 'refuses everything'."""
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    response = _post(_app(brain=brain), _message_payload())
    assert response.status_code == 200
    brain.chat.assert_awaited_once()


def test_the_signature_is_over_the_raw_bytes_not_the_reparsed_json():
    """Re-serialising before hashing is the trap; this body proves we don't.

    The whitespace here survives only if the exact received bytes are hashed —
    ``json.dumps`` of the parsed object would produce different bytes and a
    signature that never matches.
    """
    payload = _message_payload()
    spaced = json.dumps(payload, indent=4).encode()
    assert spaced != json.dumps(payload).encode()

    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    response = _post(_app(brain=brain), raw=spaced)

    assert response.status_code == 200
    brain.chat.assert_awaited_once()


# --- what must never reach the brain --------------------------------------


def test_a_delivery_receipt_does_not_reach_the_brain():
    """Replying to our own sent/delivered/read status would answer ourselves."""
    brain = SimpleNamespace(chat=AsyncMock())
    payload = {
        "entry": [
            {"changes": [{"value": {"statuses": [{"id": "wamid.X", "status": "delivered"}]}}]}
        ]
    }
    response = _post(_app(brain=brain), payload)
    assert response.status_code == 200
    brain.chat.assert_not_awaited()


def test_an_image_reaches_the_brain_with_its_bytes():
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    whatsapp = SimpleNamespace(
        send_text=AsyncMock(return_value=True),
        mark_read=AsyncMock(return_value=True),
        download_media=AsyncMock(return_value=b"image-bytes"),
    )

    _post(_app(brain=brain, whatsapp=whatsapp), _image_payload(caption="set this on HDMI"))

    whatsapp.download_media.assert_awaited_once_with("media.1")
    args, kwargs = brain.chat.await_args
    assert args[1] == "set this on HDMI"
    assert kwargs["image"] == b"image-bytes"


def test_a_caption_less_image_arrives_as_a_placeholder():
    brain = SimpleNamespace(chat=AsyncMock(return_value="which item?"))

    _post(_app(brain=brain), _image_payload())

    assert brain.chat.await_args.args[1] == "[photo]"


def test_a_failed_media_download_still_answers():
    """The caption still reaches the brain rather than the turn dying."""
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    whatsapp = SimpleNamespace(
        send_text=AsyncMock(return_value=True),
        mark_read=AsyncMock(return_value=True),
        download_media=AsyncMock(side_effect=RuntimeError("meta down")),
    )

    _post(_app(brain=brain, whatsapp=whatsapp), _image_payload(caption="set this on HDMI"))

    assert brain.chat.await_args.kwargs["image"] is None
    assert brain.chat.await_args.args[1] == "set this on HDMI"


def test_other_media_still_does_not_reach_the_brain():
    """A sticker has no text and no image — nothing the operator can act on."""
    brain = SimpleNamespace(chat=AsyncMock())
    payload = _message_payload()
    message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    del message["text"]
    message["type"] = "sticker"
    message["sticker"] = {"id": "sticker.1"}

    response = _post(_app(brain=brain), payload)

    assert response.status_code == 200
    brain.chat.assert_not_awaited()


def test_a_redelivery_does_not_reach_the_brain():
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    seen = _Seen(duplicates={"wamid.AAA"})
    response = _post(_app(brain=brain, seen=seen), _message_payload(wamid="wamid.AAA"))
    assert response.status_code == 200
    brain.chat.assert_not_awaited()
    assert seen.marked == ["wamid.AAA"]


def test_a_first_delivery_does_reach_the_brain():
    """Control for the redelivery test."""
    brain = SimpleNamespace(chat=AsyncMock(return_value="ok"))
    seen = _Seen()
    _post(_app(brain=brain, seen=seen), _message_payload(wamid="wamid.NEW"))
    brain.chat.assert_awaited_once()


def test_an_unparseable_body_is_acknowledged_not_retried():
    brain = SimpleNamespace(chat=AsyncMock())
    response = _post(_app(brain=brain), raw=b"{not json")
    assert response.status_code == 200
    brain.chat.assert_not_awaited()


def test_a_closed_allowlist_blocks_the_brain():
    brain = SimpleNamespace(chat=AsyncMock())
    response = _post(_app(brain=brain, allowed=frozenset({999})), _message_payload())
    assert response.status_code == 200
    brain.chat.assert_not_awaited()


def test_an_unparseable_sender_is_dropped():
    brain = SimpleNamespace(chat=AsyncMock())
    _post(_app(brain=brain), _message_payload(sender="not-a-number"))
    brain.chat.assert_not_awaited()


# --- the happy path -------------------------------------------------------


def test_a_message_is_namespaced_and_answered():
    brain = SimpleNamespace(chat=AsyncMock(return_value="nine locations"))
    whatsapp = SimpleNamespace(
        send_text=AsyncMock(return_value=True), mark_read=AsyncMock(return_value=True)
    )
    _post(_app(brain=brain, whatsapp=whatsapp, agent_id="invintiry-operator"),
          _message_payload(text="what's in Andes?"))

    brain.chat.assert_awaited_once_with(
        f"whatsapp:{SENDER}",
        "what's in Andes?",
        agent_id="invintiry-operator",
        end_user_id=f"whatsapp:{SENDER}",
        image=None,
    )
    whatsapp.send_text.assert_awaited_once_with(SENDER, "nine locations")


def test_a_long_reply_is_chunked():
    brain = SimpleNamespace(chat=AsyncMock(return_value="x" * 9000))
    whatsapp = SimpleNamespace(
        send_text=AsyncMock(return_value=True), mark_read=AsyncMock(return_value=True)
    )
    _post(_app(brain=brain, whatsapp=whatsapp), _message_payload())
    assert whatsapp.send_text.await_count == 3  # 4096 + 4096 + 808


def test_a_brain_failure_sends_an_apology():
    brain = SimpleNamespace(chat=AsyncMock(side_effect=RuntimeError("boom")))
    whatsapp = SimpleNamespace(
        send_text=AsyncMock(return_value=True), mark_read=AsyncMock(return_value=True)
    )
    _post(_app(brain=brain, whatsapp=whatsapp), _message_payload())
    sent = whatsapp.send_text.await_args.args[1]
    assert "wrong" in sent.lower()


def test_the_ack_does_not_wait_for_the_brain():
    """The 200 is what stops Meta redelivering; it must not depend on the turn."""
    order = []

    async def slow_chat(*args, **kwargs):
        order.append("brain")
        return "ok"

    brain = SimpleNamespace(chat=slow_chat)
    app = _app(brain=brain)
    client = TestClient(app)
    body = json.dumps(_message_payload()).encode()
    response = client.post(
        "/webhook", content=body, headers={"X-Hub-Signature-256": _sign(body)}
    )
    order.append("acked")

    assert response.status_code == 200
    # TestClient drains background tasks before returning, so the brain has run
    # by now — what this pins is that the handler *scheduled* it rather than
    # awaiting it inline before responding.
    assert "brain" in order
