# Pocket Accountant Bot

MVP scaffold for a Telegram "AI accountant in your pocket" focused on Russian entrepreneurs.

## Stack

- `Python 3.11`
- `aiogram` for Telegram bot flows and FSM
- `FastAPI` for webhook delivery, health checks, and admin endpoints
- `SQLAlchemy + PostgreSQL` for data storage
- `Redis` for lightweight queueing and transient state
- `APScheduler` for reminder and law-update jobs

## Project layout

- `shared/` common code for all services (config, db, contracts, secrets)
- `bot/` Telegram bot service (handlers, keyboards, states, backend_client)
- `backend/` FastAPI backend (routers, services, repositories, integrations)
- `worker/` APScheduler worker (cron tasks, Bot singleton for outgoing messages)
- `prompts/` AI prompt templates
- `data/` demo seed data that must be legally reviewed before production use
- `docs/` architecture, backlog, deployment, and production guidance
- `tests/` unit and integration tests (pytest, ≥75% coverage)

## Quick start

1. Create `.env` from `.env.example`.
2. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

3. Start infrastructure:

```bash
docker compose up -d postgres redis
```

4. Run migrations:

```bash
alembic upgrade head
```

5. Load demo templates:

```bash
python3 -m scripts.seed_db
```

6. Run API:

```bash
make run-api
```

7. Run bot:

```bash
make run-bot
```

8. Run worker:

```bash
make run-worker
```

## Testing

```bash
make test         # run tests
make test-cov     # run tests with coverage (≥75% required)
make lint         # ruff lint
make ci           # lint + tests with coverage
```

## Production deploy

```bash
docker compose up -d
```

Set `TELEGRAM_DELIVERY_MODE=polling` in `.env` for servers without a domain and TLS.

## CI/CD

- **CI** (`.github/workflows/ci.yml`): runs on every push/PR to `main` — lint (ruff) + tests with coverage ≥75%.
- **CD** (`.github/workflows/cd.yml`): runs on push to `main` — lint, tests, rsync to server, `docker compose up -d --build`, smoke test (`curl /health`).

Required GitHub Secrets for CD: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH`, `SSH_PRIVATE_KEY`.

## Refactoring

The project is undergoing a monolith → microservices decomposition.
See [docs/REFACTORING_PLAN.md](docs/REFACTORING_PLAN.md) for the full plan.

## Notes

- Tax and filing templates in `data/` are demo fixtures only. Production deadlines and legal texts must come from verified official sources and pass admin moderation.
- AI output is advisory-only and must not be treated as legal certainty without source verification.
- The repository is scaffolded for MVP implementation, not a complete production release.
