"""WhatsApp client tests — Meta is doubled with httpx.MockTransport.

Verifies the wire shape Meta actually requires and, more importantly, that a
refused send degrades rather than propagates: an exception escaping here would
fail the background task, leaving the customer with silence and the log with a
traceback that says nothing about why Meta said no.
"""
import asyncio

import httpx
import pytest

from application.api_integrations.whatsapp.whatsapp_client import WhatsAppClient


def _client_with(handler, **kwargs):
    return WhatsAppClient(
        access_token=kwargs.get("token", "EAAtoken"),
        phone_number_id=kwargs.get("phone_id", "1302139689652749"),
        api_version=kwargs.get("api_version", "v22.0"),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def test_send_text_hits_the_right_url_with_the_right_envelope():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["json"] = request.read().decode()
        return httpx.Response(200, json={"messages": [{"id": "wamid.X"}]})

    ok = asyncio.run(_client_with(handler).send_text("6282311020200", "hello"))

    assert ok is True
    assert seen["url"] == (
        "https://graph.facebook.com/v22.0/1302139689652749/messages"
    )
    assert seen["auth"] == "Bearer EAAtoken"
    body = seen["json"].replace(" ", "")
    assert '"messaging_product":"whatsapp"' in body
    assert '"to":"6282311020200"' in body
    assert '"type":"text"' in body
    assert '"body":"hello"' in body


def test_api_version_is_configurable_and_lands_in_the_url():
    """A pinned version is only useful if changing it actually moves the call."""
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        return httpx.Response(200, json={})

    asyncio.run(_client_with(handler, api_version="v23.0").send_text("62", "hi"))

    assert "/v23.0/" in seen["url"]


def test_a_refusal_is_logged_with_the_body_and_does_not_raise(caplog):
    """Meta's numeric code lives in the body — losing it loses the diagnosis."""

    def handler(request):
        return httpx.Response(
            400,
            json={"error": {"code": 131047, "message": "Re-engagement message"}},
        )

    with caplog.at_level("ERROR", logger="telegent"):
        ok = asyncio.run(_client_with(handler).send_text("62", "hi"))

    assert ok is False
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "131047" in logged, "the error code must survive into the log"
    assert "400" in logged


def test_a_transport_failure_does_not_escape(caplog):
    """Meta unreachable must not fail the background task that called us."""

    def handler(request):
        raise httpx.ConnectError("no route")

    with caplog.at_level("ERROR", logger="telegent"):
        ok = asyncio.run(_client_with(handler).send_text("62", "hi"))

    assert ok is False


def test_mark_read_sends_the_status_envelope():
    seen = {}

    def handler(request):
        seen["json"] = request.read().decode()
        return httpx.Response(200, json={"success": True})

    ok = asyncio.run(_client_with(handler).mark_read("wamid.ABC"))

    assert ok is True
    body = seen["json"].replace(" ", "")
    assert '"status":"read"' in body
    assert '"message_id":"wamid.ABC"' in body


def test_the_success_check_can_fail():
    """Negative control: a 2xx and a non-2xx must not report the same thing."""

    def ok_handler(request):
        return httpx.Response(200, json={})

    def bad_handler(request):
        return httpx.Response(500, text="boom")

    assert asyncio.run(_client_with(ok_handler).send_text("62", "hi")) is True
    assert asyncio.run(_client_with(bad_handler).send_text("62", "hi")) is False


@pytest.mark.parametrize("status", [200, 201, 202])
def test_any_2xx_counts_as_accepted(status):
    def handler(request):
        return httpx.Response(status, json={})

    assert asyncio.run(_client_with(handler).send_text("62", "hi")) is True
