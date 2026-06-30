# ═══════════════════════════════════════════════════════════════════════
# HELIOS OS + SEVRA AI — Developer Makefile
# All developer workflow commands live here.
# Usage: make <target>
# ═══════════════════════════════════════════════════════════════════════

.PHONY: help dev down build test lint format typecheck migrate clean logs shell

# Default target
help:
	@echo ""
	@echo "  HELIOS OS + SEVRA AI — Developer Commands"
	@echo "  ═══════════════════════════════════════════"
	@echo "  make dev          Start full development stack"
	@echo "  make down         Stop and remove all containers"
	@echo "  make build        Rebuild Docker images"
	@echo "  make test         Run all tests with coverage"
	@echo "  make test-unit    Run unit tests only"
	@echo "  make lint         Run ruff linter"
	@echo "  make format       Auto-format code with ruff"
	@echo "  make typecheck    Run mypy type checker"
	@echo "  make migrate      Run Alembic database migrations"
	@echo "  make makemigration msg='description'  Create new migration"
	@echo "  make logs         Tail all container logs"
	@echo "  make logs-backend Tail backend logs only"
	@echo "  make shell        Open bash in backend container"
	@echo "  make clean        Remove all containers, volumes, and __pycache__"
	@echo "  make setup        First-time setup (copy .env, install deps)"
	@echo ""

# ── Development Stack ─────────────────────────────────────────────────────────

dev:
	@echo "Starting HELIOS development stack..."
	docker compose up -d
	@echo "Stack started. Backend: http://localhost:8000"
	@echo "Grafana: http://localhost:3001 | Prometheus: http://localhost:9090"

dev-build:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build --no-cache backend

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	cd backend && \
	HELIOS_ENVIRONMENT=testing \
	python -m pytest tests/ \
		--cov=. \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=80 \
		-v

test-unit:
	cd backend && \
	HELIOS_ENVIRONMENT=testing \
	python -m pytest tests/unit/ -v

test-integration:
	cd backend && \
	HELIOS_ENVIRONMENT=testing \
	python -m pytest tests/integration/ -v

test-watch:
	cd backend && \
	HELIOS_ENVIRONMENT=testing \
	python -m pytest tests/ -v --tb=short -x

# ── Code Quality ──────────────────────────────────────────────────────────────

lint:
	cd backend && python -m ruff check .

lint-fix:
	cd backend && python -m ruff check . --fix

format:
	cd backend && python -m ruff format .

format-check:
	cd backend && python -m ruff format . --check

typecheck:
	cd backend && python -m mypy . --ignore-missing-imports

# ── Database Migrations ───────────────────────────────────────────────────────

migrate:
	cd backend && python -m alembic upgrade head

migrate-down:
	cd backend && python -m alembic downgrade -1

makemigration:
	@[ "${msg}" ] || ( echo "Usage: make makemigration msg='your description'"; exit 1 )
	cd backend && python -m alembic revision --autogenerate -m "$(msg)"

migrate-history:
	cd backend && python -m alembic history

migrate-current:
	cd backend && python -m alembic current

# ── Logs ──────────────────────────────────────────────────────────────────────

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-redis:
	docker compose logs -f redis

logs-postgres:
	docker compose logs -f postgres

# ── Shell Access ──────────────────────────────────────────────────────────────

shell:
	docker compose exec backend bash

shell-redis:
	docker compose exec redis redis-cli

shell-postgres:
	docker compose exec postgres psql -U helios -d helios

# ── Setup ─────────────────────────────────────────────────────────────────────

setup:
	@echo "Setting up HELIOS development environment..."
	cp -n backend/.env.example backend/.env || true
	cd backend && pip install -e ".[dev]"
	@echo "Setup complete. Run 'make dev' to start the stack."

install:
	cd backend && pip install -e ".[dev]"

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	docker compose down -v --remove-orphans
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "Cleanup complete."

# ── Health ────────────────────────────────────────────────────────────────────

health:
	@curl -s http://localhost:8000/api/v1/health | python -m json.tool

status:
	docker compose ps
