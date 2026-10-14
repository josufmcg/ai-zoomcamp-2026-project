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

.PHONY: install run test build \
	backend-install backend-run backend-test \
	frontend-install frontend-run frontend-test frontend-build \
	up down logs url

## Install backend and frontend dependencies
install: backend-install frontend-install

## Run the backend development server
run: backend-run

## Run all tests (backend and frontend)
test: backend-test frontend-test

## Build the frontend for production
build: frontend-build

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

frontend-install:
	cd $(FRONTEND_DIR) && npm install

frontend-run:
	cd $(FRONTEND_DIR) && npm run dev -- --port $(FRONTEND_PORT)

frontend-test:
	cd $(FRONTEND_DIR) && npm test

frontend-build:
	cd $(FRONTEND_DIR) && npm run build
