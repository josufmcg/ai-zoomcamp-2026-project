# EFINGES project Makefile
#
# Backend targets (backlog task 1). Docker Compose targets (`up`, `down`,
# `logs`, `url`) are added by backlog task 3.

BACKEND_DIR ?= backend
BACKEND_PORT ?= 8000

.PHONY: install run test backend-install backend-run backend-test

## Install backend dependencies
install: backend-install

## Run the backend development server
run: backend-run

## Run all tests (backend for now)
test: backend-test

backend-install:
	cd $(BACKEND_DIR) && uv sync

backend-run:
	cd $(BACKEND_DIR) && uv run uvicorn app.main:app --reload --port $(BACKEND_PORT)

backend-test:
	cd $(BACKEND_DIR) && uv run pytest
