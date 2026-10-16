from houseplants.common.settings import Settings


def test_settings_splits_comma_separated_allowed_origins():
    settings = Settings(allowed_origins=" http://a.test, http://b.test ,")

    assert settings.allowed_origins == ["http://a.test", "http://b.test"]


def test_settings_reads_allowed_origins_from_environment(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://a.test,http://b.test")

    assert Settings().allowed_origins == ["http://a.test", "http://b.test"]


def test_settings_splits_comma_separated_authorized_parties():
    settings = Settings(auth_authorized_parties="http://a.test,http://b.test")

    assert settings.auth_authorized_parties == ["http://a.test", "http://b.test"]


def test_settings_jwks_url_defaults_to_the_issuers_well_known_path():
    settings = Settings(auth_issuer="https://clerk.example.com/", auth_jwks_url=None)

    assert settings.jwks_url == "https://clerk.example.com/.well-known/jwks.json"


def test_settings_jwks_url_can_be_set_explicitly():
    settings = Settings(auth_issuer="https://clerk.example.com", auth_jwks_url="http://mock/jwks")

    assert settings.jwks_url == "http://mock/jwks"


def test_settings_jwks_url_is_none_without_an_issuer():
    assert Settings(auth_issuer=None, auth_jwks_url=None).jwks_url is None
