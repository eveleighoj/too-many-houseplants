import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from houseplants.common.security import (
    TokenVerifier,
    get_token_verifier,
    optional_user_id,
    require_user_id,
)
from houseplants.common.settings import get_settings

ISSUER = "https://issuer.test"  # matches tests/conftest.py


def bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def valid_claims(**overrides) -> dict:
    now = int(time.time())
    return {"sub": "user_x", "iss": ISSUER, "iat": now, "exp": now + 60, **overrides}


@pytest.fixture
def verifier() -> TokenVerifier:
    return get_token_verifier()


class TestTokenVerifier:
    def test_verify_returns_the_subject_of_a_valid_token(self, verifier, make_token):
        assert verifier.verify(make_token("user_abc")) == "user_abc"

    def test_verify_rejects_an_expired_token(self, verifier, make_token):
        long_ago = int(time.time()) - 3600

        assert verifier.verify(make_token(iat=long_ago, nbf=long_ago, exp=long_ago + 60)) is None

    def test_verify_allows_small_clock_skew(self, verifier, make_token):
        assert verifier.verify(make_token(exp=int(time.time()) - 5)) == "user_test"

    def test_verify_rejects_a_token_not_yet_valid(self, verifier, make_token):
        later = int(time.time()) + 3600

        assert verifier.verify(make_token(nbf=later, exp=later + 60)) is None

    def test_verify_rejects_another_issuer(self, verifier, make_token):
        assert verifier.verify(make_token(iss="https://evil.example")) is None

    @pytest.mark.parametrize("claim", ["sub", "exp", "iss"])
    def test_verify_rejects_a_token_missing_a_required_claim(self, verifier, make_token, claim):
        assert verifier.verify(make_token(**{claim: None})) is None

    def test_verify_rejects_an_empty_subject(self, verifier, make_token):
        assert verifier.verify(make_token("")) is None

    def test_verify_rejects_an_unauthorized_party(self, verifier, make_token):
        assert verifier.verify(make_token(azp="https://evil.example")) is None

    def test_verify_allows_a_token_without_azp(self, verifier, make_token):
        assert verifier.verify(make_token(azp=None)) == "user_test"

    def test_verify_rejects_a_token_signed_by_another_key_with_our_key_id(self, verifier):
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = jwt.encode(
            valid_claims(), other_key, algorithm="RS256", headers={"kid": "test-key"}
        )

        assert verifier.verify(token) is None

    def test_verify_rejects_a_token_with_an_unknown_key_id(self, verifier):
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = jwt.encode(valid_claims(), other_key, algorithm="RS256", headers={"kid": "nope"})

        assert verifier.verify(token) is None

    def test_verify_rejects_an_hs256_token(self, verifier):
        token = jwt.encode(
            valid_claims(), "a-shared-secret-of-thirty-two-bytes!", headers={"kid": "test-key"}
        )

        assert verifier.verify(token) is None

    def test_verify_rejects_an_unsigned_token(self, verifier):
        token = jwt.encode(valid_claims(), None, algorithm="none", headers={"kid": "test-key"})

        assert verifier.verify(token) is None

    def test_verify_rejects_garbage(self, verifier):
        assert verifier.verify("not-a-token") is None

    def test_verify_returns_none_when_the_jwks_is_unreachable(self, make_token):
        unreachable = TokenVerifier(ISSUER, "http://127.0.0.1:9/jwks.json", [])

        assert unreachable.verify(make_token()) is None


class TestGetTokenVerifier:
    def test_get_token_verifier_uses_the_configured_issuer(self):
        assert get_token_verifier().issuer == get_settings().auth_issuer

    def test_get_token_verifier_is_none_without_an_issuer(self, monkeypatch):
        monkeypatch.setattr(get_settings(), "auth_issuer", None)
        get_token_verifier.cache_clear()
        try:
            assert get_token_verifier() is None
        finally:
            monkeypatch.undo()
            get_token_verifier.cache_clear()


def test_optional_user_id_returns_none_without_credentials():
    assert optional_user_id(None) is None


def test_optional_user_id_returns_none_for_invalid_token():
    assert optional_user_id(bearer("not-a-token")) is None


def test_optional_user_id_returns_user_id_for_valid_token(make_token):
    assert optional_user_id(bearer(make_token("user_abc"))) == "user_abc"


def test_require_user_id_raises_401_without_a_user():
    with pytest.raises(HTTPException) as error:
        require_user_id(None)

    assert error.value.status_code == 401
    assert error.value.headers == {"WWW-Authenticate": "Bearer"}


def test_require_user_id_passes_user_id_through():
    assert require_user_id("user_abc") == "user_abc"
