SHELL := /usr/bin/env bash

.PHONY: help api-install api-migrate api-seed api-test api-run web-install web-build web-dev web-typecheck compose-up compose-down smoke

help:
	@echo "JRDbooks dev commands"
	@echo "  make api-install    - install python deps"
	@echo "  make api-migrate    - run alembic migrations"
	@echo "  make api-seed       - seed demo organization"
	@echo "  make api-test       - run backend tests"
	@echo "  make api-run        - start API in foreground"
	@echo "  make web-install    - install frontend deps"
	@echo "  make web-build      - production build"
	@echo "  make web-dev        - dev server"
	@echo "  make compose-up     - boot postgres + redis + api + web"
	@echo "  make compose-down   - stop docker-compose stack"
	@echo "  make smoke          - curl-driven API smoke against localhost:8000"

api-install:
	cd apps/api && python -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]' && pip install 'bcrypt<4.1'

api-migrate:
	cd apps/api && source .venv/bin/activate && alembic upgrade head

api-seed:
	cd apps/api && source .venv/bin/activate && python -m jrdbooks.seed

api-test:
	cd apps/api && source .venv/bin/activate && pytest -q

api-run:
	cd apps/api && source .venv/bin/activate && uvicorn jrdbooks.main:app --reload --port 8000

web-install:
	cd apps/web && pnpm install

web-build:
	cd apps/web && pnpm build

web-dev:
	cd apps/web && pnpm dev

web-typecheck:
	cd apps/web && pnpm typecheck

compose-up:
	docker compose -f infra/docker-compose.yml up --build -d

compose-down:
	docker compose -f infra/docker-compose.yml down

smoke:
	@bash scripts/smoke.sh
