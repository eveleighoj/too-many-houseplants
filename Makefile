.PHONY: help setup lock build test test-api test-api-unit test-api-integration test-api-acceptance test-frontends e2e lint check-test-packages format dev up down logs seed db-up db-down migrate migration check-commits api-types api-types-check mock-tokens

# Everything runs from the repo root (docs/repository-structure.md): one .venv (uv) and one
# node_modules (npm workspaces).

# On the host, trust clerk-mock on its host port unless .env names another issuer.
HOST_AUTH := $(if $(shell grep -s '^AUTH_ISSUER=' .env),,AUTH_ISSUER=http://localhost:8082 AUTH_JWKS_URL=http://localhost:8082/.well-known/jwks.json AUTH_AUTHORIZED_PARTIES=http://localhost:5173 AUTH_DEV_TOKENS_URL=http://localhost:8082)

help: ## Show available make targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# --- Standard targets ---------------------------------------------------------------------

setup: .env ## Install everything: .venv (uv), node_modules (npm), Chromium for tests, the commit-msg hook
	uv sync
	npm ci
	npx playwright install chromium
	uv run pre-commit install

.env:
	cp .env.example .env

lock: ## Re-lock dependencies after editing pyproject.toml or a package.json
	uv lock
	npm install --package-lock-only

build: ## Build the frontends and every service's Docker image
	npm run build
	docker build -f services/api/Dockerfile --target runtime -t too-many-houseplants/api .
	docker build -f services/trips-frontend/Dockerfile -t too-many-houseplants/trips-frontend .

test: test-api test-frontends ## Run every test except e2e (api integration/acceptance tests need Docker)

e2e: ## Run e2e tests against the running system (none yet)
	@echo "No e2e tests yet: see docs/testing.md."

lint: check-test-packages ## Lint, format-check, type-check and check import boundaries, everywhere
	uv run ruff check .
	uv run ruff format --check .
	uv run lint-imports
	npm run lint

format: ## Fix lint issues and format, everywhere
	uv run ruff check --fix .
	uv run ruff format .
	npm run format

dev: ## Run the api on the host with live reload (start the database first: make db-up)
	$(HOST_AUTH) uv run uvicorn api.main:app --port 8000 --reload --reload-dir services/api

# --- Tests ----------------------------------------------------------------------------------

test-api: ## Run the api's tests
	uv run pytest tests/api --ignore-glob='*/e2e/*'

test-api-unit: ## Run the api's unit tests (no Docker needed)
	uv run pytest tests/api/unit

test-api-integration: ## Run the api's integration tests
	uv run pytest tests/api/integration

test-api-acceptance: ## Run the api's acceptance (API contract) tests
	uv run pytest tests/api/acceptance

test-frontends: ## Run every frontend's unit and component tests
	npm test

check-test-packages: ## Fail if any folder under tests/ is missing its __init__.py
	@! find tests -type d ! -name __pycache__ ! -path '*/__pycache__/*' ! -exec test -e '{}/__init__.py' ';' -print | grep . \
		|| (echo "^ these test folders need an __init__.py (docs/testing.md)" && exit 1)

# --- Docker Compose: the whole stack -------------------------------------------------------

up: .env ## Start everything: API on :8000, trips frontend on :5173, mocks, Postgres
	docker compose up --build -d

down: ## Stop the compose stack
	docker compose down

logs: ## Follow the api and frontend logs
	docker compose logs -f api trips-frontend

db-up: ## Start only Postgres and clerk-mock (for `make dev`)
	docker compose up -d db clerk-mock

db-down: ## Stop only Postgres
	docker compose stop db

seed: ## Reset the local database's demo trips (needs `make up` or `make db-up`)
	uv run python -m scripts.api.seed

# --- Database -------------------------------------------------------------------------------

migrate: ## Apply every api sub-app's migrations to DATABASE_URL in .env
	uv run python -m api.common.migrations

migration: ## Autogenerate a migration: make migration chain=trips m="add cover image"
	@test -n "$(chain)" -a -n "$(m)" || (echo 'usage: make migration chain=<trips> m="message"' && exit 1)
	uv run alembic -c services/api/$(chain)/alembic.ini revision --autogenerate -m "$(m)"

# --- Other ----------------------------------------------------------------------------------

check-commits: ## Check your branch's commits are Conventional Commits, as CI does
	scripts/check-commits.sh

api-types: ## Regenerate the frontends' API types from the running api (make up first)
	npm run api:types -w services/trips-frontend

api-types-check: ## Fail if the frontends' API types are out of date with the api (no server needed)
	@specs=$$(mktemp -d) && \
	uv run python -m scripts.api.export_openapi $$specs > /dev/null && \
	API_SPEC_DIR=$$specs npm run --silent api:types -w services/trips-frontend > /dev/null && \
	rm -rf $$specs && \
	git diff --exit-code -- 'services/*/src/lib/api/' || \
	(echo "The frontends' API types were out of date and have been regenerated above — commit them." && exit 1)

mock-tokens: ## Regenerate clerk-mock's JWKS and dev users' tokens
	uv run python scripts/generate-clerk-mock-tokens.py
