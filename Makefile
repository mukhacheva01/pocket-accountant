install:
	python3 -m pip install -e .[dev]

run-api:
	uvicorn accountant_bot.app.api:create_app --factory --reload

run-worker:
	python3 -m accountant_bot.jobs.worker

migrate:
	alembic upgrade head

seed:
	PYTHONPATH=src python3 -m accountant_bot.db.bootstrap

set-webhook:
	python3 scripts/set_webhook.py

test:
	python3 -m unittest discover -s tests
