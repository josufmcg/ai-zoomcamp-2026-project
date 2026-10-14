# EFINGES project Makefile
#
# Backend targets (backlog task 1) and frontend targets (backlog task 2).
# Docker Compose targets (`up`, `down`, `logs`, `url`) are added by backlog
# task 3.

BACKEND_DIR ?= backend
BACKEND_PORT ?= 8000
FRONTEND_DIR ?= frontend
FRONTEND_PORT ?= 3000

.PHONY: install run test build \
	backend-install backend-run backend-test \
	frontend-install frontend-run frontend-test frontend-build

## Install backend and frontend dependencies
install: backend-install frontend-install

## Run the backend development server
run: backend-run

## Run all tests (backend and frontend)
test: backend-test frontend-test

## Build the frontend for production
build: frontend-build

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
