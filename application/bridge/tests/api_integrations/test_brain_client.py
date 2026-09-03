"""Brain client tests — the brain is doubled with httpx.MockTransport.

Verifies the /chat contract the bridge sends: agent_id is included only when set,
so an older brain sees exactly the request it always did.
"""
import asyncio
import json

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


def test_end_user_id_is_sent_when_set_and_omitted_when_not():
    """The brain keys credentials off this, so it must arrive verbatim."""
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"reply": "ok"})

    client = BrainClient("http://brain", 5.0, client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ))
    asyncio.run(client.chat("telegram:42", "hi", end_user_id="telegram:7"))
    asyncio.run(client.chat("telegram:42", "hi"))

    assert bodies[0]["end_user_id"] == "telegram:7"
    assert "end_user_id" not in bodies[1]


def test_agent_id_is_omitted_when_absent():
    seen = {}

    def handler(request):
        seen["json"] = request.read().decode()
        return httpx.Response(200, json={"reply": "ok"})

    asyncio.run(_client_with(handler).chat("telegram:1", "hi"))

    assert "agent_id" not in seen["json"]
