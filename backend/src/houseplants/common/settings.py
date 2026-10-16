from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_commas(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://houseplant:houseplant@localhost:5432/houseplant"

    # Who we trust to issue bearer tokens — Clerk in production, the clerk-mock service
    # locally (mocks/clerk/). Tokens must be RS256-signed by a key from the JWKS, with this
    # exact `iss`. Without an issuer, every request is treated as anonymous.
    auth_issuer: str | None = None
    # Defaults to {auth_issuer}/.well-known/jwks.json, which is where Clerk publishes it.
    auth_jwks_url: str | None = None
    # Comma-separated. If set, a token's `azp` claim (the origin it was issued to, which
    # Clerk sets) must be one of these. Tokens without `azp` (e.g. machine tokens) still pass.
    auth_authorized_parties: Annotated[list[str], NoDecode] = []
    # Local development only: where to get dev users' tokens (clerk-mock). When set, the API
    # docs point there for "Authorize".
    auth_dev_tokens_url: str | None = None

    # Comma-separated in the environment, e.g. "http://localhost:5173,https://trips.example.com".
    allowed_origins: Annotated[list[str], NoDecode] = []

    # Optional: without it, /windsurf returns 503 rather than the whole app refusing to boot.
    ukho_api_key: str | None = None
    # Overridden locally to point at the WireMock stand-in (see mocks/ukho/).
    ukho_base_url: str = "https://admiraltyapi.azure-api.net/uktidalapi/api/V1"

    # Which users own the seed data (`make seed`). The defaults are the clerk-mock users;
    # set your own Clerk user id to own the demo trips when using a real Clerk instance.
    seed_demo_user_id: str = "user_demo"
    seed_friend_user_id: str = "user_friend"

    _split_origins = field_validator("allowed_origins", mode="before")(_split_commas)
    _split_parties = field_validator("auth_authorized_parties", mode="before")(_split_commas)

    @property
    def jwks_url(self) -> str | None:
        if self.auth_jwks_url:
            return self.auth_jwks_url
        if self.auth_issuer:
            return self.auth_issuer.rstrip("/") + "/.well-known/jwks.json"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
