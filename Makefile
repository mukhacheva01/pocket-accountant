install:
	python3 -m pip install -e .[dev]

run-api:
	uvicorn backend.app:create_app --factory --reload

run-bot:
	python3 -m bot.entrypoint

run-worker:
	python3 -m worker.entrypoint

migrate:
	alembic upgrade head

seed:
	python3 -m scripts.seed_db

set-webhook:
	python3 scripts/set_webhook.py

test:
	pytest --tb=short -q

test-cov:
	pytest --cov --cov-fail-under=75 --cov-report=term-missing --tb=short -q

lint:
	ruff check .

ci: lint test-cov

up:
	docker compose up -d

down:
	docker compose down
