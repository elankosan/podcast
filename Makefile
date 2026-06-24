.PHONY: dev prod test lint build migrate backup clean

# === Development ===
dev:
	docker compose up --build

prod:
	docker compose -f docker-compose.prod.yml up -d --build

# === Testing ===
test:
	cd api && pytest ../tests/ -v
	cd app && npm test

# === Linting ===
lint:
	cd api && flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	cd app && npm run lint

# === Building ===
build:
	docker build -t maf-podcast-api:latest ./api
	docker build -t maf-podcast-app:latest ./app

# === Database ===
migrate:
	cd api && alembic upgrade head

# === Backup ===
backup:
	bash scripts/backup.sh

# === Cleanup ===
clean:
	docker compose down -v
	docker system prune -f
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
