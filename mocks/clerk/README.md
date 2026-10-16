# Clerk mock (local token issuer)

Stands in for [Clerk](https://clerk.com) in the local docker compose stack (`clerk-mock`
service, http://localhost:8082), so local development needs no Clerk account, internet
connection or sign-in. Not used by tests — they issue their own tokens.

| Path | What |
| --- | --- |
| `GET /` | A page listing the dev users, with a **Copy token** button each, for pasting into the API's `/docs` (**Authorize**). |
| `GET /.well-known/jwks.json` | The public key the dev tokens are signed with. The backend verifies tokens against it, exactly as it does against Clerk's. |
| `GET /dev/users` | The dev users, each with a ready-made bearer token. The frontends' local login page lists these. |

| User id | Owns (after `make seed`) |
| --- | --- |
| `user_demo` | Scottish Highlands, Lake District, Japan |
| `user_friend` | Cornwall surf trip |

The tokens last until 2100, so they can be pasted into the API's `/docs` (**Authorize**) or
used with curl:

```bash
TOKEN=$(curl -s localhost:8082/dev/users | jq -r '.users[0].token')   # user_demo
curl -s localhost:8000/trips/ -H "Authorization: Bearer $TOKEN"
```

They're only trusted by a backend whose `AUTH_ISSUER` is `http://localhost:8082`
(`compose.env`) — never by production, which trusts only Clerk.

To change the users or claims, edit `generate.py`, run `make mock-tokens`, and restart the
service (`docker compose restart clerk-mock`).
