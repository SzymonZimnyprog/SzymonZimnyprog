.PHONY: install dev test lint format

# Install all dependencies
install:
	python -m venv .venv && .venv/bin/pip install -r backend/requirements-dev.txt
	cd frontend && npm install

# Run backend + frontend in dev mode (requires two terminals or use docker-compose)
dev-backend:
	.venv/bin/uvicorn backend.main:app --reload

dev-frontend:
	cd frontend && npm run dev

# Run with Docker Compose
dev:
	docker compose up --build

# Tests
test-backend:
	.venv/bin/pytest

test-frontend:
	cd frontend && npm test

test: test-backend test-frontend

# Lint
lint-backend:
	.venv/bin/ruff check backend/

lint-frontend:
	cd frontend && npm run lint

lint: lint-backend lint-frontend

# Format
format:
	.venv/bin/ruff format backend/
