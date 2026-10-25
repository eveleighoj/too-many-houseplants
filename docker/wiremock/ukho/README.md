# UKHO tidal API mock

[WireMock](https://wiremock.org/) stubs standing in for the
[UKHO Admiralty tidal API](https://admiraltyapi.portal.azure-api.net/) in the local docker
compose stack (`ukho-mock` service). Not used by tests — they arrange their own responses.

- `mappings/tidal-events.json` — `GET /stations/{id}/TidalEvents` returns a week of
  alternating low/high water starting today (same data for every station).
- `mappings/missing-subscription-key.json` — anything without an
  `Ocp-Apim-Subscription-Key` header gets a 401, as the real API does.
- `__files/tidal-events.json` — the response body. Times are WireMock
  [response templates](https://wiremock.org/docs/response-templating/) offset from today's
  midnight, so the data never goes stale.

Edit the stubs and restart the service (`docker compose restart ukho-mock`), or browse what's
loaded at http://localhost:8081/__admin/mappings.
