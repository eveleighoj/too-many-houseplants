# The api service image. Build from the repo root, so the build context has pyproject.toml,
# uv.lock and tests/:
#   docker build -f services/api/Dockerfile --target runtime .
# Stages: base (locked dependencies + the api package), test (base + its unit tests; never
# deployed), runtime (what Render and docker compose run).
FROM python:3.13-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Locked third-party dependencies first, in their own cached layer.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

# Then the api package itself, installed (not editable) into the venv, so its source can go.
COPY pyproject.toml uv.lock ./
COPY services/api services/api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable \
 && rm -rf services


FROM base AS test
# Dev dependencies on top, keeping the installed api package (--inexact).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --inexact
COPY tests/__init__.py tests/
COPY tests/api tests/api
COPY scripts/api scripts/api
# Unit tests only: integration and acceptance tests start Postgres with testcontainers, which
# needs a Docker daemon the build doesn't have. CI runs those against the same lockfile.
RUN pytest tests/api/unit


# Keep runtime the last stage: Render (render.yaml) builds the last stage when no target is set.
FROM base AS runtime
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
