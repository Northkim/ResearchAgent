SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

COMPOSE := docker compose --env-file .env

.PHONY: demo-configure demo-config-check demo-start demo-stop demo-reset \
	demo-seed demo-status demo-logs test-backend compile-backend \
	test-frontend lint-frontend build-frontend test-integration test-e2e test-all

demo-configure:
	@if [[ -f .env ]]; then \
		echo ".env already exists; leaving it unchanged"; \
	else \
		cp .env.example .env; \
		echo "Created .env from .env.example"; \
	fi

demo-config-check:
	@test -f .env || { echo "Missing .env; run 'make demo-configure' first" >&2; exit 1; }
	$(COMPOSE) config --quiet

demo-start: demo-config-check
	$(COMPOSE) up --build --detach --wait --wait-timeout 240

demo-stop: demo-config-check
	$(COMPOSE) down --remove-orphans

demo-reset: demo-config-check
	$(COMPOSE) down --volumes --remove-orphans

demo-seed: demo-config-check
	$(COMPOSE) run --rm seed

demo-status: demo-config-check
	$(COMPOSE) ps

demo-logs: demo-config-check
	$(COMPOSE) logs --follow --tail=200

test-backend:
	conda run --no-capture-output -n reagent-dev pytest -q backend

compile-backend:
	conda run --no-capture-output -n reagent-dev python -m compileall -q backend

test-frontend:
	cd frontend && npm test

lint-frontend:
	cd frontend && npm run lint

build-frontend:
	cd frontend && npm run build

test-integration: demo-config-check
	$(COMPOSE) up --detach --wait db
	$(COMPOSE) --profile test run --rm integration-test

test-e2e:
	cd frontend && npm run test:e2e

test-all: test-backend compile-backend test-frontend lint-frontend \
	build-frontend test-integration test-e2e
