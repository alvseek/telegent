"""Composition root: wire config + clients + dedupe store, then serve.

The WhatsApp half of the bridge is a web server because Meta only ever dials in.
That is the single structural difference from ``main_telegram``, and everything
below the handler — the brain client, the allowlist, the chunker, the shared
workflow — is the same code the Telegram process runs.

Construction happens at import time so a missing variable kills the process at
boot rather than at the first message. A bridge that starts successfully and
then fails on every webhook is worse than one that refuses to start, because
Meta will keep retrying into it and nobody is watching the log yet.

Host and port come from config rather than from the unit file's command line, so
there is one place to change where this listens. It listens on loopback: Caddy
terminates TLS for ``wa.lok.quest`` and proxies inward.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI

from application.api_controllers.whatsapp_handler import router
from application.api_integrations.brain.brain_client import BrainClient
from application.api_integrations.whatsapp.whatsapp_client import WhatsAppClient
from application.configuration.env import load_whatsapp_config
from application.data_repositories.seen_message_repository import SeenMessageRepository
from application.logger import logger_setup

logger_setup.configure()

config = load_whatsapp_config()

app = FastAPI(title="telegent — WhatsApp bridge", docs_url=None, redoc_url=None)
app.state.config = config
app.state.brain = BrainClient(config.brain_url, config.brain_timeout)
app.state.whatsapp = WhatsAppClient(
    access_token=config.access_token,
    phone_number_id=config.phone_number_id,
    api_version=config.api_version,
)
app.state.seen = SeenMessageRepository(config.db_path)
app.include_router(router)

_log = logging.getLogger("telegent")
_purged = app.state.seen.purge_older_than()
_log.info(
    "telegent whatsapp bridge starting -> brain=%s agent=%s allowlist=%s "
    "listen=%s:%s api=%s (purged %d stale message ids)",
    config.brain_url,
    config.agent_id or "default",
    "open" if config.allowed_ids is None else f"{len(config.allowed_ids)} number(s)",
    config.host,
    config.port,
    config.api_version,
    _purged,
)


def main() -> None:
    import uvicorn

    # log_config=None keeps logger_setup's configuration, which silences httpx so
    # bearer tokens never reach the log.
    #
    # access_log=False for a reason that is not tidiness. uvicorn's access line
    # includes the full query string, and Meta's handshake carries the verify
    # token in the query string — so leaving it on writes a credential into the
    # journal on every registration. It also fills the log with the vulnerability
    # scanners that find this host within minutes of its certificate appearing in
    # the public certificate-transparency feed. The handler's own logging is the
    # part worth keeping: handshakes accepted and refused, signatures rejected,
    # duplicates dropped.
    uvicorn.run(
        app, host=config.host, port=config.port, log_config=None, access_log=False
    )


if __name__ == "__main__":
    main()
