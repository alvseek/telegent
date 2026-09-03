"""External integration: HTTP client to universal-chat-agent (the brain).

The ONLY place the bridge knows how to reach the brain. Swapping transport
(e.g. HTTP -> gRPC for streaming) later is localized to this file.

A single long-lived ``httpx.AsyncClient`` is reused across requests so
keep-alive eliminates per-request TCP/handshake cost — on localhost the hop is
sub-millisecond and dwarfed by the brain's LLM call.
"""
from __future__ import annotations

import httpx


class BrainClient:
    def __init__(
        self, base_url: str, timeout: float, client: httpx.AsyncClient | None = None
    ) -> None:
        self._url = base_url.rstrip("/") + "/chat"
        # Injectable so tests can hand in a client with a mock transport.
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def chat(
        self,
        conversation_id: str,
        message: str,
        agent_id: str | None = None,
        end_user_id: str | None = None,
    ) -> str:
        """POST one turn to the brain and return its reply text.

        ``agent_id`` names which agent answers and ``end_user_id`` names who is
        asking; each is sent only when set, so a brain that predates either sees
        the same request it always did.
        """
        body: dict = {"conversation_id": conversation_id, "message": message}
        if agent_id:
            body["agent_id"] = agent_id
        if end_user_id:
            body["end_user_id"] = end_user_id
        resp = await self._client.post(self._url, json=body)
        resp.raise_for_status()
        return resp.json()["reply"]

    async def aclose(self) -> None:
        await self._client.aclose()
