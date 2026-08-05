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
    def __init__(self, base_url: str, timeout: float) -> None:
        self._url = base_url.rstrip("/") + "/chat"
        self._client = httpx.AsyncClient(timeout=timeout)

    async def chat(self, conversation_id: str, message: str) -> str:
        """POST one turn to the brain and return its reply text."""
        resp = await self._client.post(
            self._url,
            json={"conversation_id": conversation_id, "message": message},
        )
        resp.raise_for_status()
        return resp.json()["reply"]

    async def aclose(self) -> None:
        await self._client.aclose()
