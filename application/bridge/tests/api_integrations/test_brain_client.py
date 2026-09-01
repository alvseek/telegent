"""Brain client tests — the brain is doubled with httpx.MockTransport.

Verifies the /chat contract the bridge sends: agent_id is included only when set,
so an older brain sees exactly the request it always did.
"""
import asyncio

import httpx

from application.api_integrations.brain.brain_client import BrainClient


def _client_with(handler):
    return BrainClient(
        "http://brain.example",
        timeout=5.0,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def test_agent_id_is_sent_when_set():
    seen = {}

    def handler(request):
        seen["json"] = request.read().decode()
        return httpx.Response(200, json={"reply": "ok"})

    reply = asyncio.run(_client_with(handler).chat("telegram:1", "hi", agent_id="op"))

    assert reply == "ok"
    assert '"agent_id":"op"' in seen["json"].replace(" ", "")


def test_agent_id_is_omitted_when_absent():
    seen = {}

    def handler(request):
        seen["json"] = request.read().decode()
        return httpx.Response(200, json={"reply": "ok"})

    asyncio.run(_client_with(handler).chat("telegram:1", "hi"))

    assert "agent_id" not in seen["json"]
