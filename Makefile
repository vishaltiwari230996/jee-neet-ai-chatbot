# NeetAI development commands.
# Run `make` (no args) for the menu.

SHELL := /bin/bash
.DEFAULT_GOAL := help

UV ?= uv
PNPM ?= pnpm
COMPOSE ?= docker compose

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
.PHONY: install
install: install-py install-js ## Install both Python and JS dependencies

.PHONY: install-py
install-py: ## Install the Python workspace with dev dependencies
	$(UV) sync --all-packages --all-extras

.PHONY: install-js
install-js: ## Install the JS workspace (pnpm)
	$(PNPM) install

.PHONY: hooks
hooks: ## Install pre-commit hooks
	$(UV) run pre-commit install --install-hooks

.PHONY: bootstrap
bootstrap: install hooks ## One-shot project bootstrap
	@echo "Workspace ready. Copy .env.example to .env, then run \`make dev\`."

# ---------------------------------------------------------------------------
# Local stack
# ---------------------------------------------------------------------------
.PHONY: dev
dev: ## Start databases + api (background)
	$(COMPOSE) up -d postgres redis
	@echo "Postgres on 5432, Redis on 6379."
	@echo "Run \`make api\` to start the API process locally."

.PHONY: dev-all
dev-all: ## Start everything (databases + dockerized api)
	$(COMPOSE) --profile api up -d --build

.PHONY: stop
stop: ## Stop the local stack
	$(COMPOSE) down

.PHONY: clean
clean: ## Stop the local stack AND wipe volumes
	$(COMPOSE) down -v

.PHONY: api
api: ## Run the API on the host (against dockerized DB/Redis)
	$(UV) run --package neetai-api uvicorn neetai_api.main:create_app --factory --reload --host 127.0.0.1 --port 8000

.PHONY: web
web: ## Run the Next.js dev server on the host (proxies /api/* to the API)
	$(PNPM) --filter @neetai/web dev

.PHONY: up-all
up-all: ## One-shot: start db, migrate, seed, then print boot instructions
	@$(MAKE) -s dev
	@echo "Waiting for Postgres to be healthy..."
	@for i in $$(seq 1 30); do \
		if docker inspect --format='{{.State.Health.Status}}' neetai-postgres-1 2>/dev/null | grep -q healthy; then \
			echo "Postgres healthy."; break; \
		fi; sleep 1; \
	done
	@$(MAKE) -s migrate
	@$(MAKE) -s seed
	@echo ""
	@echo "Stack is provisioned. Open two terminals:"
	@echo "  1) make api    # FastAPI on http://127.0.0.1:8000"
	@echo "  2) make web    # Next.js on http://127.0.0.1:3000"

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------
.PHONY: lint
lint: lint-py lint-js ## Lint everything

.PHONY: lint-py
lint-py: ## Ruff lint (no fixes)
	$(UV) run ruff check .

.PHONY: lint-js
lint-js: ## ESLint on the web app
	$(PNPM) --filter @neetai/web lint

.PHONY: fmt
fmt: ## Ruff format + fix
	$(UV) run ruff format .
	$(UV) run ruff check . --fix

.PHONY: typecheck-js
typecheck-js: ## tsc --noEmit on the web app
	$(PNPM) --filter @neetai/web typecheck

.PHONY: type
type: ## mypy strict over the whole workspace
	$(UV) run mypy \
		-p neetai_core -p neetai_ports \
		-p neetai_profiling -p neetai_question_bank \
		-p neetai_doubt_classifier -p neetai_retrieval \
		-p neetai_orchestrator -p neetai_safety \
		-p neetai_feedback -p neetai_analytics \
		-p neetai_api \
		-p neetai_llm_openrouter -p neetai_llm_anthropic -p neetai_llm_fake \
		-p neetai_db_postgres -p neetai_db_fake

.PHONY: arch
arch: ## Enforce module-boundary contracts
	$(UV) run lint-imports

.PHONY: check
check: lint type arch ## All static checks

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
.PHONY: test
test: ## Unit tests (no integration / llm markers)
	$(UV) run pytest -m "not integration and not llm"

.PHONY: test-cov
test-cov: ## Unit tests with coverage
	$(UV) run pytest -m "not integration and not llm" --cov --cov-report=term-missing

.PHONY: test-all
test-all: ## Every test (requires services running)
	$(UV) run pytest

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
QUESTIONS_CSV ?= infra/data/onboarding_questions.csv

.PHONY: migrate
migrate: ## Apply Alembic migrations against the configured DATABASE_URL
	$(UV) run alembic -c migrations/alembic.ini upgrade head

.PHONY: migrate-down
migrate-down: ## Roll back one Alembic revision (dangerous in prod)
	$(UV) run alembic -c migrations/alembic.ini downgrade -1

.PHONY: migrate-status
migrate-status: ## Show the current Alembic revision
	$(UV) run alembic -c migrations/alembic.ini current

.PHONY: migrate-new
migrate-new: ## Generate a new revision; use MSG="add foo column"
	@test -n "$(MSG)" || (echo "MSG is required, e.g. make migrate-new MSG='add foo'"; exit 1)
	$(UV) run alembic -c migrations/alembic.ini revision --autogenerate -m "$(MSG)"

.PHONY: seed-questions
seed-questions: ## Ingest the diagnostic question CSV into the question_bank table
	$(UV) run --package neetai-api python scripts/ingest_questions.py $(QUESTIONS_CSV)

.PHONY: seed-questions-dry
seed-questions-dry: ## Parse + validate the CSV without writing
	$(UV) run --package neetai-api python scripts/ingest_questions.py $(QUESTIONS_CSV) --dry-run

.PHONY: seed
seed: seed-questions ## Seed all local dev data (currently: questions)

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
.PHONY: smoke-llm
smoke-llm: ## One real round-trip through the LLM adapter (cheap + strong tier)
	$(UV) run --package neetai-api python scripts/smoke_llm.py

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
.PHONY: help
help: ## Show this menu
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
