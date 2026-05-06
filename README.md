# Pocket Accountant Bot

MVP scaffold for a Telegram "AI accountant in your pocket" focused on Russian entrepreneurs.

## Stack

- `Python`
- `aiogram` for Telegram bot flows and FSM
- `FastAPI` for webhook delivery, health checks, and admin endpoints
- `SQLAlchemy + PostgreSQL` for data storage
- `Redis` for lightweight queueing and transient state
- `APScheduler` for reminder and law-update jobs

## Project layout

- `src/accountant_bot/bot/` Telegram handlers, states, keyboards, callbacks
- `src/accountant_bot/services/` business logic and orchestration
- `src/accountant_bot/repositories/` database access
- `src/accountant_bot/db/` models and session setup
- `src/accountant_bot/jobs/` cron-like tasks and scheduler bootstrap
- `src/accountant_bot/app/` FastAPI entrypoint
- `src/accountant_bot/contracts/` payload contracts shared across modules
- `prompts/` AI prompt templates
- `data/` demo seed data that must be legally reviewed before production use
- `docs/` architecture, backlog, deployment, and production guidance

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
PYTHONPATH=src python3 -m accountant_bot.db.bootstrap
```

6. Run API:

```bash
uvicorn accountant_bot.app.api:create_app --factory --reload
```

7. Run worker:

```bash
python3 -m accountant_bot.jobs.worker
```

## Production deploy

For a server without a domain and TLS, use Telegram polling mode instead of webhooks.

1. Set `TELEGRAM_DELIVERY_MODE=polling` in `.env`.
2. Add swap on low-memory VPS hosts before rebuilding images.
3. Build and start infrastructure, API, and worker without the polling bot:

```bash
./deploy/deploy.sh
```

4. After the old polling instance is stopped, start the new bot on this host:

```bash
START_BOT=1 ./deploy/deploy.sh
```

5. Check the containers:

```bash
docker compose -f deploy/docker-compose.prod.yml ps
```

Do not run `python -m accountant_bot.db.bootstrap` in production while the calendar data is still demo-only.

## Notes

- Tax and filing templates in `data/` are demo fixtures only. Production deadlines and legal texts must come from verified official sources and pass admin moderation.
- AI output is advisory-only and must not be treated as legal certainty without source verification.
- The repository is scaffolded for MVP implementation, not a complete production release.
