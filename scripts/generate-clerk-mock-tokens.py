"""Regenerates clerk-mock's JWKS and dev users' tokens (docker/wiremock/clerk/).

    make mock-tokens        (= uv run python scripts/generate-clerk-mock-tokens.py)

Run after changing USERS, ISSUER or AUTHORIZED_PARTY below, then restart clerk-mock. Uses the
key in dev-key/ if you have one, otherwise makes a new one (it's gitignored: the committed
JWKS and tokens are all anyone needs). Local development ONLY: these tokens are trusted only
by a backend whose AUTH_ISSUER is the mock's (docker/compose.env), never by production.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

HERE = Path(__file__).resolve().parent.parent / "docker" / "wiremock" / "clerk"
KEY_FILE = HERE / "dev-key" / "dev-private-key.pem"
KEY_ID = "clerk-mock-dev-key"

# Must match AUTH_ISSUER and AUTH_AUTHORIZED_PARTIES in docker/compose.env.
ISSUER = "http://localhost:8082"
AUTHORIZED_PARTY = "http://localhost:5173"
# Long-lived, unlike Clerk's ~60s tokens, so they can be pasted into /docs or curl.
EXPIRES = datetime(2100, 1, 1, tzinfo=UTC)

# The ids must match the seed's default owners (scripts/api/seed/__init__.py).
USERS = [
    {"id": "user_demo", "name": "Demo", "email": "demo@example.com"},
    {"id": "user_friend", "name": "Friend", "email": "friend@example.com"},
]


def load_or_create_key() -> rsa.RSAPrivateKey:
    if KEY_FILE.exists():
        return serialization.load_pem_private_key(KEY_FILE.read_bytes(), password=None)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    KEY_FILE.parent.mkdir(exist_ok=True)
    KEY_FILE.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return key


def render_index(users: list[dict]) -> str:
    """http://localhost:8082/ — the dev users' tokens, one click to copy (e.g. for /docs)."""
    rows = "\n".join(
        f"""      <tr>
        <td><strong>{user["name"]}</strong><br><code>{user["id"]}</code></td>
        <td><button data-token="{user["token"]}">Copy token</button></td>
      </tr>"""
        for user in users
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>clerk-mock dev tokens</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 40rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
    table {{ border-collapse: collapse; width: 100%; }}
    td {{ padding: 0.75rem 0.5rem; border-top: 1px solid #ddd; vertical-align: middle; }}
    button {{ padding: 0.4rem 0.9rem; cursor: pointer; }}
    code {{ color: #555; }}
  </style>
</head>
<body>
  <h1>clerk-mock dev tokens</h1>
  <p>Local development only. In the API's docs (e.g.
    <a href="http://localhost:8000/trips/docs">/trips/docs</a>) click <strong>Authorize</strong>
    and paste a token — just the token, Swagger adds "Bearer" itself. Tokens last until 2100.</p>
  <table>
{rows}
  </table>
  <script>
    for (const button of document.querySelectorAll("button[data-token]")) {{
      button.addEventListener("click", async () => {{
        await navigator.clipboard.writeText(button.dataset.token);
        button.textContent = "Copied!";
        setTimeout(() => (button.textContent = "Copy token"), 1500);
      }});
    }}
  </script>
</body>
</html>
"""


def main() -> None:
    key = load_or_create_key()

    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwks = {"keys": [{**jwk, "kid": KEY_ID, "use": "sig", "alg": "RS256"}]}
    (HERE / "__files" / "jwks.json").write_text(json.dumps(jwks, indent=2) + "\n")

    issued_at = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
    users = [
        {
            **user,
            "token": jwt.encode(
                {
                    "sub": user["id"],
                    "iss": ISSUER,
                    "azp": AUTHORIZED_PARTY,
                    "iat": issued_at,
                    "nbf": issued_at,
                    "exp": int(EXPIRES.timestamp()),
                },
                key,
                algorithm="RS256",
                headers={"kid": KEY_ID},
            ),
        }
        for user in USERS
    ]
    (HERE / "__files" / "dev-users.json").write_text(json.dumps({"users": users}, indent=2) + "\n")
    (HERE / "__files" / "index.html").write_text(render_index(users))
    print(f"Wrote JWKS and tokens for {', '.join(u['id'] for u in USERS)}")


if __name__ == "__main__":
    main()
