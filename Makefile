# EFINGES project Makefile
#
# Backend targets (backlog task 1), frontend targets (backlog task 2), Docker
# Compose targets (backlog task 3), and observability targets (backlog task 4).

BACKEND_DIR ?= backend
BACKEND_PORT ?= 8000
FRONTEND_DIR ?= frontend
FRONTEND_PORT ?= 3000
POSTGRES_PORT ?= 5432
GRAFANA_PORT ?= 3001
PROMETHEUS_PORT ?= 9090
LOKI_PORT ?= 3100
TEMPO_PORT ?= 3200
EFINGES_SUBNET ?= 10.215.25.0/24
COMPOSE ?= docker compose

# Security scans (backlog task 21). The reports are committed under
# $(SECURITY_DIR); `make security` regenerates all of them. Bandit runs ad hoc
# through uvx (no project dependency) and Trivy is a separate binary.
SECURITY_DIR ?= security
EFINGES_TAG ?= local
BACKEND_IMAGE ?= efinges-backend:$(EFINGES_TAG)
FRONTEND_IMAGE ?= efinges-frontend:$(EFINGES_TAG)
TRIVY ?= trivy

# Dedicated database the integration workflows use (backlog task 18). It is
# separate from the development database so the workflows can wipe their tables
# without touching seeded or local data. Point it at any PostgreSQL server you
# control; the default matches the compose postgres on its published port.
INTEGRATION_DATABASE_URL ?= postgresql+psycopg://efinges:efinges@127.0.0.1:$(POSTGRES_PORT)/efinges_test

# Database the demo seed fills (backlog task 23). It defaults to the compose
# postgres the running stack uses, so `make seed` populates the very database
# the frontend and API read from. Override it to seed a different server.
SEED_DATABASE_URL ?= postgresql+psycopg://efinges:efinges@127.0.0.1:$(POSTGRES_PORT)/efinges

.PHONY: install run test build lint openapi-check security seed seed-reset \
	backend-install backend-run backend-test backend-test-integration \
	backend-migrate backend-revision backend-openapi backend-seed backend-seed-reset \
	backend-lint \
	frontend-install frontend-run frontend-test frontend-build frontend-lint \
	integration integration-db \
	up down logs url

## Install backend and frontend dependencies
install: backend-install frontend-install

## Run the backend development server
run: backend-run

## Run all unit tests (backend and frontend)
test: backend-test frontend-test

## Lint both sides (Ruff for the backend, ESLint for the frontend)
lint: backend-lint frontend-lint

## Run the integration workflows against a dedicated database (needs postgres up)
integration: backend-test-integration

## Create the dedicated integration test database in the compose postgres
integration-db:
	@$(COMPOSE) exec -T postgres psql -U efinges -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='efinges_test'" | grep -q 1 \
		|| $(COMPOSE) exec -T postgres createdb -U efinges efinges_test

## Build the frontend for production
build: frontend-build

## Apply the database migrations (alembic upgrade head)
migrate: backend-migrate

## Create a new migration from the current models (use m="message")
revision: backend-revision

## Seed the demo data (idempotent; re-running creates nothing)
seed: backend-seed

## Reset the demo rows and seed them again (leaves all other data alone)
seed-reset: backend-seed-reset

## Export the FastAPI OpenAPI schema to openapi.yaml at the repository root
openapi: backend-openapi

## Verify openapi.yaml matches the backend application schema
openapi-check:
	cd $(BACKEND_DIR) && uv run python -m scripts.export_openapi --check

## Run the security scans and refresh the reports under security/ (needs trivy and the built images)
security:
	cd $(BACKEND_DIR) && uvx bandit --exit-zero -r app scripts alembic --exclude alembic/versions -f txt > ../$(SECURITY_DIR)/bandit-report.txt
	$(TRIVY) image --scanners vuln --format template --template '@$(SECURITY_DIR)/trivy-report.tpl' $(BACKEND_IMAGE) > $(SECURITY_DIR)/trivy-backend.txt
	$(TRIVY) image --scanners vuln --format template --template '@$(SECURITY_DIR)/trivy-report.tpl' $(FRONTEND_IMAGE) > $(SECURITY_DIR)/trivy-frontend.txt

## Build and start the full stack (backend, frontend, postgres, observability)
up:
	BACKEND_PORT=$(BACKEND_PORT) FRONTEND_PORT=$(FRONTEND_PORT) POSTGRES_PORT=$(POSTGRES_PORT) \
	GRAFANA_PORT=$(GRAFANA_PORT) PROMETHEUS_PORT=$(PROMETHEUS_PORT) LOKI_PORT=$(LOKI_PORT) TEMPO_PORT=$(TEMPO_PORT) \
	EFINGES_SUBNET=$(EFINGES_SUBNET) $(COMPOSE) up --build -d --wait
	@$(MAKE) --no-print-directory url

## Stop and remove the stack containers
down:
	$(COMPOSE) down

## Follow the backend and frontend logs
logs:
	$(COMPOSE) logs -f backend frontend

## Print the local URLs of the running stack
url:
	@echo "Frontend:   http://127.0.0.1:$(FRONTEND_PORT)"
	@echo "Backend:    http://127.0.0.1:$(BACKEND_PORT)"
	@echo "API docs:   http://127.0.0.1:$(BACKEND_PORT)/docs"
	@echo "Grafana:    http://127.0.0.1:$(GRAFANA_PORT) (admin/admin)"
	@echo "Prometheus: http://127.0.0.1:$(PROMETHEUS_PORT)"
	@echo "Loki:       http://127.0.0.1:$(LOKI_PORT)"
	@echo "Tempo:      http://127.0.0.1:$(TEMPO_PORT)"
	@echo "Postgres:   postgresql://efinges:efinges@127.0.0.1:$(POSTGRES_PORT)/efinges"

backend-install:
	cd $(BACKEND_DIR) && uv sync

backend-run:
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --port $(BACKEND_PORT)

backend-test:
	cd $(BACKEND_DIR) && uv run pytest

backend-test-integration:
	cd $(BACKEND_DIR) && TEST_DATABASE_URL="$(INTEGRATION_DATABASE_URL)" uv run pytest tests/integration

backend-migrate:
	cd $(BACKEND_DIR) && uv run alembic upgrade head

backend-revision:
	cd $(BACKEND_DIR) && uv run alembic revision --autogenerate -m "$(m)"

backend-seed:
	cd $(BACKEND_DIR) && uv run python -m scripts.seed_demo --database-url "$(SEED_DATABASE_URL)"

backend-seed-reset:
	cd $(BACKEND_DIR) && uv run python -m scripts.seed_demo --database-url "$(SEED_DATABASE_URL)" --reset

backend-openapi:
	cd $(BACKEND_DIR) && uv run python -m scripts.export_openapi

backend-lint:
	cd $(BACKEND_DIR) && uv run ruff check . && uv run ruff format --check .

frontend-install:
	cd $(FRONTEND_DIR) && npm install

frontend-run:
	cd $(FRONTEND_DIR) && npm run dev -- --port $(FRONTEND_PORT)

frontend-test:
	cd $(FRONTEND_DIR) && npm test

frontend-lint:
	cd $(FRONTEND_DIR) && npm run lint

frontend-build:
	cd $(FRONTEND_DIR) && npm run build
