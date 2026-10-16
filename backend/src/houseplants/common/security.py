"""Bearer token verification, shared by every sub-app.

Tokens are issued elsewhere — by Clerk in production, by the clerk-mock service locally —
and only verified here: RS256 signature against the issuer's published keys (JWKS), plus
issuer, expiry and authorized party. The `sub` claim is trusted as the caller's user id.
No sub-app talks to the issuer beyond fetching its public keys.
"""

import logging
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from houseplants.common.settings import get_settings

logger = logging.getLogger(__name__)

ALGORITHM = "RS256"
# Allowance for clock differences between us and the issuer (Clerk tokens live ~60s).
LEEWAY_SECONDS = 10


class TokenVerifier:
    def __init__(self, issuer: str, jwks_url: str, authorized_parties: list[str]):
        self.issuer = issuer
        self.authorized_parties = authorized_parties
        # Fetches and caches the issuer's public keys, refetching for an unknown key id.
        self.jwks = jwt.PyJWKClient(jwks_url, cache_keys=True)

    def verify(self, token: str) -> str | None:
        """The token's user id (`sub`) if it's valid, otherwise None."""
        try:
            key = self.jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                key.key,
                # Never trust the token's own alg header.
                algorithms=[ALGORITHM],
                issuer=self.issuer,
                leeway=LEEWAY_SECONDS,
                options={"require": ["sub", "exp", "iss"], "verify_aud": False},
            )
        except jwt.PyJWKClientConnectionError:
            logger.exception("could not fetch the token issuer's JWKS")
            return None
        except jwt.PyJWTError:
            return None

        azp = claims.get("azp")
        if azp is not None and self.authorized_parties and azp not in self.authorized_parties:
            return None
        sub = claims["sub"]
        return sub if isinstance(sub, str) and sub else None


@lru_cache
def get_token_verifier() -> TokenVerifier | None:
    settings = get_settings()
    if not settings.auth_issuer:
        logger.warning("AUTH_ISSUER is not set: every request will be treated as anonymous")
        return None
    return TokenVerifier(settings.auth_issuer, settings.jwks_url, settings.auth_authorized_parties)


# auto_error=False so public endpoints can still serve anonymous callers; the
# authorization decision is left to the dependency (or handler) below.
_bearer = HTTPBearer(auto_error=False)


def optional_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str | None:
    """The caller's user id if they sent a valid bearer token, otherwise None."""
    verifier = get_token_verifier()
    if credentials is None or verifier is None:
        return None
    return verifier.verify(credentials.credentials)


def require_user_id(user_id: Annotated[str | None, Depends(optional_user_id)]) -> str:
    if user_id is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


OptionalUserId = Annotated[str | None, Depends(optional_user_id)]
UserId = Annotated[str, Depends(require_user_id)]
