# UrbView — developer entry points. POSIX make; runs under Git Bash on Windows and on Linux/macOS.
# Every target from CLAUDE.md §11 exists. Targets whose phase has not landed exit non-zero with
# a message naming that phase, never silently succeed.

# GNU make on Windows defaults to cmd.exe; every recipe here is POSIX sh, which Git Bash
# provides. On Linux/macOS this is a no-op.
SHELL     := sh

COMPOSE   := docker compose
BACKEND   := $(COMPOSE) exec -T backend
FRONTEND  := $(COMPOSE) exec -T frontend

.DEFAULT_GOAL := help
.PHONY: help up down logs load-data extract warehouse types test test-backend test-frontend \
        lint lint-backend lint-frontend format

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --- Run -------------------------------------------------------------------------------

up: ## Build and start the stack: app on :5173, API on :8000
	$(COMPOSE) up --build

down: ## Stop the stack (keeps the Postgres volume)
	$(COMPOSE) down

logs: ## Tail all service logs
	$(COMPOSE) logs -f

# --- Data (Phase 2) --------------------------------------------------------------------
# All three run inside the backend container: DuckDB + spatial + httpfs are already there.

load-data: ## Fetch the prepared Overture extract (release asset, checksummed) and build data/warehouse.duckdb
	$(BACKEND) python -m pipeline.load_data

extract: ## Re-run the real Overture S3 pull from scratch (slow, ~10 min), then build
	$(BACKEND) python -m pipeline.extract
	$(BACKEND) python -m pipeline.build

warehouse: ## Rebuild data/warehouse.duckdb from data/raw/ (no download)
	$(BACKEND) python -m pipeline.build

publish-extract: ## Maintainer: upload data/raw/*.parquet as a GitHub release asset and refresh pipeline/manifest.json
	python backend/pipeline/publish.py

# --- Types (Phase 4) -------------------------------------------------------------------

types: ## Regenerate frontend/src/api/schema.gen.ts from the OpenAPI schema
	@echo "make types: not implemented yet - lands in Phase 4 (API layer)." >&2
	@exit 1

# --- Quality ---------------------------------------------------------------------------

test: test-backend test-frontend ## Backend + frontend tests (inside the running containers)

test-backend: ## pytest
	$(BACKEND) pytest -q

test-frontend: ## vitest
	$(FRONTEND) npm test --silent

lint: lint-backend lint-frontend ## ruff + mypy + eslint + tsc --noEmit

lint-backend: ## ruff check, ruff format --check, mypy
	$(BACKEND) ruff check .
	$(BACKEND) ruff format --check .
	$(BACKEND) mypy

lint-frontend: ## eslint, prettier --check, tsc --noEmit
	$(FRONTEND) npm run --silent lint
	$(FRONTEND) npm run --silent format:check
	$(FRONTEND) npm run --silent typecheck

format: ## Rewrite files with ruff format + prettier
	$(BACKEND) ruff format .
	$(FRONTEND) npm run --silent format
