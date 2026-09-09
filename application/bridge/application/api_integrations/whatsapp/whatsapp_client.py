"""External integration: WhatsApp Cloud API (Meta Graph).

The ONLY place the bridge knows how to send a WhatsApp message, mirroring what
``telegram_client`` does for the other transport. Everything Meta-shaped — the
Graph URL, the bearer header, the ``messaging_product`` envelope — stops here.

A single long-lived ``httpx.AsyncClient`` is reused so keep-alive removes the
TLS handshake from every reply; against Meta that handshake is real latency, not
the sub-millisecond hop the brain client sees.

Sends do not raise. A failed reply must not take down the process or turn into a
second inbound retry, so a non-2xx is logged with **the response body** and
swallowed. That body is the only useful diagnostic Meta gives — the numeric code
in it is what distinguishes a closed 24-hour window from a country restriction
from an expired token, and without it every failure looks identical.
"""
from __future__ import annotations

import logging

import httpx

log = logging.getLogger("telegent")

GRAPH_BASE = "https://graph.facebook.com"


class WhatsAppClient:
    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        api_version: str,
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._url = f"{GRAPH_BASE}/{api_version}/{phone_number_id}/messages"
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        # Injectable so tests can hand in a client with a mock transport.
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def send_text(self, to: str, body: str) -> bool:
        """Send one text message. Returns whether Meta accepted it.

        ``to`` is the sender's WhatsApp id — their number in international form
        with no plus — which is exactly what an inbound webhook gave us, so it is
        never reformatted here.
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        return await self._post(payload, "text")

    async def mark_read(self, message_id: str) -> bool:
        """Show the blue ticks. Best-effort: a failure here changes nothing."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        return await self._post(payload, "read receipt")

    async def _post(self, payload: dict, what: str) -> bool:
        try:
            response = await self._client.post(
                self._url, headers=self._headers, json=payload
            )
        except httpx.HTTPError:
            log.exception("whatsapp %s send failed before a response", what)
            return False
        if response.status_code // 100 != 2:
            # The body carries Meta's numeric error code; without it every
            # failure reads the same and none of them can be acted on.
            log.error(
                "whatsapp %s send refused: HTTP %s %s",
                what,
                response.status_code,
                response.text,
            )
            return False
        return True

    async def aclose(self) -> None:
        await self._client.aclose()
