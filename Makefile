.PHONY: all dev build test lint clean install

all: dev

# ─── Development ────────────────────────────────────────────────────────────
dev:
	docker compose up --build

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# ─── Install ─────────────────────────────────────────────────────────────────
install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

# ─── Build ───────────────────────────────────────────────────────────────────
build:
	cd frontend && npm run build
	docker compose build

# ─── Test ────────────────────────────────────────────────────────────────────
test:
	cd backend && pytest tests/ -v --tb=short
	cd frontend && npm run test

test-backend:
	cd backend && pytest tests/ -v --tb=short

test-frontend:
	cd frontend && npm run test

# ─── Lint ─────────────────────────────────────────────────────────────────────
lint:
	cd backend && ruff check app/ && mypy app/
	cd frontend && npm run lint

# ─── Clean ────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	cd frontend && rm -rf dist node_modules/.cache
