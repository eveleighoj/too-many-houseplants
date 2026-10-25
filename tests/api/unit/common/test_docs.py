from api.common.docs import SWAGGER_UI_PARAMETERS, api_description
from api.common.settings import get_settings


def test_api_description_is_unchanged_without_a_dev_tokens_url(monkeypatch):
    monkeypatch.setattr(get_settings(), "auth_dev_tokens_url", None)

    assert api_description("Trips.") == "Trips."


def test_api_description_links_to_dev_tokens_when_configured(monkeypatch):
    monkeypatch.setattr(get_settings(), "auth_dev_tokens_url", "http://localhost:8082")

    description = api_description("Trips.")

    assert description.startswith("Trips.")
    assert "(http://localhost:8082)" in description


def test_swagger_ui_parameters_persist_authorization():
    assert SWAGGER_UI_PARAMETERS["persistAuthorization"] is True
