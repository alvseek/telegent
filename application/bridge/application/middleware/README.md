# middleware — empty, and now for a narrower reason

Originally empty because the bridge ran no HTTP server at all. That changed when the
WhatsApp transport arrived: `main_whatsapp` serves FastAPI, so there *are* routes
that could be wrapped.

It stays empty anyway, deliberately. The two things middleware would usually carry
here are already where they belong and are better placed for it:

- **Signature verification** is the first statement of the webhook handler rather
  than a wrapper, because it must run against the raw request body before anything
  parses it, and because a reader deciding whether this endpoint is safe should find
  that check in the route they are reading.
- **Error handling** lives in `business_services/forward`, so both transports inherit
  identical behaviour — a wrapper would only cover the one that speaks HTTP.

Add something here when a concern genuinely spans every HTTP route and belongs to
none of them: request ids, rate limiting, a health probe.
