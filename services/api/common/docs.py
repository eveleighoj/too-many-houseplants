"""Shared settings for each sub-app's interactive docs (/<sub-app>/docs)."""

from api.common.settings import get_settings

# Swagger UI keeps what you enter under "Authorize" across page reloads (in that browser).
SWAGGER_UI_PARAMETERS = {"persistAuthorization": True}


def api_description(text: str) -> str:
    """A sub-app's docs description, plus — locally — where to get a token for "Authorize"."""
    tokens_url = get_settings().auth_dev_tokens_url
    if not tokens_url:
        return text
    return (
        f"{text}\n\n**Local development:** click **Authorize** and paste a dev user's token "
        f'from [clerk-mock]({tokens_url}) — just the token, Swagger adds "Bearer" itself.'
    )
