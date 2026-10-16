.PHONY: help init up down logs seed run dev test test-backend test-unit test-integration test-acceptance test-trips-frontend lint format api-types mock-tokens db-up db-down migrate migration

BACKEND := cd backend &&
TRIPS_FRONTEND := cd trips-frontend &&
# On the host, trust clerk-mock on its host port unless backend/.env names another issuer.
HOST_AUTH := $(if $(shell grep -s '^AUTH_ISSUER=' backend/.env),,AUTH_ISSUER=http://localhost:8082 AUTH_JWKS_URL=http://localhost:8082/.well-known/jwks.json AUTH_AUTHORIZED_PARTIES=http://localhost:5173 AUTH_DEV_TOKENS_URL=http://localhost:8082)

help: ## Show available make targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

init: backend/.env ## Install backend (uv) and frontend (npm) dependencies; create backend/.env
	$(BACKEND) uv sync
	$(TRIPS_FRONTEND) npm ci && npx playwright install chromium

backend/.env:
	cp backend/.env.example backend/.env

# --- Docker Compose: the whole stack ---------------------------------------------------

up: backend/.env ## Start everything (docker compose): API on :8000, trips frontend on :5173, mocks
	docker compose up --build -d

down: ## Stop the compose stack
	docker compose down

logs: ## Follow API and frontend logs
	docker compose logs -f api trips-frontend

seed: ## Reset the local database's demo trips (needs `make up` or `make db-up`)
	$(BACKEND) uv run python -m houseplants.seed

# --- Running the backend on the host instead ------------------------------------------

db-up: ## Start only Postgres and clerk-mock (for logging in)
	docker compose up -d db clerk-mock

db-down: ## Stop only Postgres
	docker compose stop db

run: ## Run the backend on the host
	$(BACKEND) $(HOST_AUTH) uv run uvicorn houseplants.main:app --port 8000

dev: ## Run the backend on the host with live reload
	$(BACKEND) $(HOST_AUTH) uv run uvicorn houseplants.main:app --port 8000 --reload

# --- Tests (backend integration and acceptance need Docker for testcontainers) --------

test: test-backend test-trips-frontend ## Run every test, backend and frontend

test-backend: ## Run every backend test
	$(BACKEND) uv run pytest

test-unit: ## Run backend unit tests (no Docker needed)
	$(BACKEND) uv run pytest tests/unit

test-integration: ## Run backend integration tests
	$(BACKEND) uv run pytest tests/integration

test-acceptance: ## Run backend acceptance (API contract) tests
	$(BACKEND) uv run pytest tests/acceptance

test-trips-frontend: ## Run the trips frontend's unit and component tests
	$(TRIPS_FRONTEND) npm test

lint: ## Lint, type-check and check formatting, backend and frontend
	$(BACKEND) uv run ruff check . && uv run ruff format --check .
	$(TRIPS_FRONTEND) npm run lint && npm run check

format: ## Fix lint issues and format, backend and frontend
	$(BACKEND) uv run ruff check --fix . && uv run ruff format .
	$(TRIPS_FRONTEND) npm run format

api-types: ## Regenerate the frontend's API types from the running backend (make up first)
	$(TRIPS_FRONTEND) npm run api:types

mock-tokens: ## Regenerate clerk-mock's JWKS and dev users' tokens (mocks/clerk/generate.py)
	$(BACKEND) uv run python ../mocks/clerk/generate.py

# --- Database -------------------------------------------------------------------------

migrate: ## Apply every sub-app's migrations to DATABASE_URL in backend/.env
	$(BACKEND) uv run python -m houseplants.common.migrations

migration: ## Autogenerate a migration: make migration chain=trips m="add cover image"
	@test -n "$(chain)" -a -n "$(m)" || (echo 'usage: make migration chain=<trips> m="message"' && exit 1)
	$(BACKEND) uv run alembic -c src/houseplants/$(chain)/alembic.ini revision --autogenerate -m "$(m)"
