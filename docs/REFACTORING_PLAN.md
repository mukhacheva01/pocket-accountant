# План рефакторинга Pocket Accountant Bot

> Документ подготовлен архитектором-консультантом для передачи агенту-исполнителю.
> Бизнес-код не пишем — только структура, конфиги и спецификации.

---

## §1. Текущее состояние

### 1.1 Код

| Показатель | Значение |
|---|---|
| Python | 3.11 (Dockerfile) |
| Фреймворки | aiogram 3.4+, FastAPI 0.111+, APScheduler 3.10+, SQLAlchemy 2.0+ (asyncpg) |
| LLM | openai SDK → OpenRouter / OpenAI (Responses API) |
| Упаковка | setuptools, `src/` layout (`src/accountant_bot/`) |
| Тесты | 3 файла, unittest, ~158 строк. Покрытие ≈ 5–8 % |
| Линтер | ruff (в dev-зависимостях), без конфига |

#### Дублирование корневых файлов

В корне лежат «старые» монолитные модули, которые **дублируют** пакет `src/`:

| Корневой файл | Аналог в `src/` | Замечание |
|---|---|---|
| `config.py` (121 стр.) | `src/accountant_bot/core/config.py` (108 стр.) | Разные наборы полей; корневой содержит ozon-переменные, src — subscriptions. **Нужен merge.** |
| `secrets.py` (57 стр.) | `src/accountant_bot/core/secrets.py` (57 стр.) | **Идентичны.** Корневой — мёртвый код. |
| `ai_gateway.py` (245 стр.) | `src/accountant_bot/services/ai_gateway.py` (174 стр.) | Корневой — расширенная версия (rate limiting, seller_qa). Src — более новая (history, tax_qa). **Нужен merge.** |
| `container.py` (109 стр.) | `src/accountant_bot/services/container.py` (60 стр.) | Корневой добавляет Ozon, Google Sheets, SecretBox. Src — без них. **Нужен merge.** |
| `api.py` (283 стр.) | `src/accountant_bot/app/api.py` (87 стр.) | Корневой — расширенная (backend events, Ozon sync). Src — чистый webhook + admin. **Нужен merge.** |
| `router.py` (103 стр.) | `src/accountant_bot/admin/router.py` (487 стр.) | Оба — admin router. Src — полная версия (RBAC, CRUD). Корневой — устаревший. |
| `tasks.py` (119 стр.) | `src/accountant_bot/jobs/tasks.py` (130 стр.) | Src — чуть новее (TelegramForbiddenError, deactivation). Нужно синхронизировать и убрать ozon из корневого. |
| `worker.py` (81 стр.) | `src/accountant_bot/jobs/worker.py` (50 стр.) | Корневой добавляет ozon_sync job. **Нужен merge.** |

**Вывод:** корневые файлы — старый слой из предыдущей итерации (MP-Pilot / Ozon). Целевой пакет — `src/accountant_bot/`. При merge корневые удаляются.

#### Модули без парного дублирования (только в `src/`)

- `bot/router.py` — **1 415 строк**, god-object. Онбординг, финансы, AI-консультация, подписка, события, настройки — всё в одном файле.
- `bot/keyboards.py` — 333 строки, все клавиатуры.
- `services/tax_engine.py` — 446 строк, калькулятор + парсер.
- `services/subscription.py` — 118 строк, Telegram Stars платежи.

### 1.2 Инфра

- **docker-compose.prod.yml** — 6 сервисов: postgres, redis, migrate, api, bot (polling), worker. + nginx (webhook profile).
- **deploy.sh** — ручной скрипт: `docker build` → `docker compose run migrate` → `docker compose up`.
- **Dockerfile** — один образ, монолит. CMD = uvicorn.
- **CI/CD** — отсутствует.
- **Alembic** — 4 миграции, URL берётся из Settings (корневой config). `env.py` импортирует `core.config`.

### 1.3 Ключевые проблемы

1. **Дублирование** — два параллельных набора модулей (корень + src).
2. **God-object** — `bot/router.py` (1 415 строк) — один файл обрабатывает всё.
3. **Связность** — bot, api, worker ходят напрямую в БД через SessionFactory на уровне модуля.
4. **Отсутствие CI** — нет автоматических проверок.
5. **Тесты** — покрытие < 10%.
6. **Один Docker-образ** — нет изоляции сервисов.

---

## §2. Предлагаемый состав сервисов

### Целевой стек (5 контейнеров)

| Контейнер | Зона ответственности | Входящий трафик | БД | Redis |
|---|---|---|---|---|
| **bot** | aiogram Dispatcher, polling/webhook. Принимает Telegram updates. Вызывает backend по HTTP (httpx). | Telegram API (polling) или входящий webhook | **нет** | нет |
| **backend** | FastAPI. REST API: бизнес-логика, admin, webhook endpoint (проксирует в bot). | HTTP (8080) | **да** (asyncpg) | **да** |
| **worker** | APScheduler. Крон-задачи: напоминания, law-updates, ozon sync, calendar sync. Telegram send_message/send_photo. | нет | **да** (asyncpg) | **да** |
| **postgres** | PostgreSQL 16 | TCP 5432 (internal) | — | — |
| **redis** | Redis 7, AOF | TCP 6379 (internal) | — | — |

### Обоснование

- **bot** — изолирован от БД. Все мутации через backend API (httpx, внутренняя docker-сеть). Если bot падает, данные в безопасности.
- **backend** — единственный сервис с доступом к БД через HTTP API. Alembic запускается в его entrypoint перед uvicorn. Admin API тут же.
- **worker** — ходит в БД напрямую через `shared/db` (без HTTP-хопа). Это принятое решение. Использует `Bot(token=BOT_TOKEN)` singleton для исходящих сообщений (output-only, без Dispatcher/polling).
- **Один образ** — все три Python-сервиса используют один Docker-образ, отличаются CMD.

---

## §3. Целевая структура каталогов

```
pocket-accountant/
├── shared/                          # общий код для всех сервисов
│   ├── __init__.py
│   ├── config.py                    # Settings (pydantic-settings), единый конфиг
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                  # Base, mixins
│   │   ├── enums.py
│   │   ├── models.py
│   │   └── session.py               # engine + SessionFactory
│   ├── contracts/
│   │   ├── __init__.py
│   │   └── payloads.py              # Pydantic-контракты между сервисами
│   ├── secrets.py                   # SecretBox (Fernet)
│   ├── clock.py                     # utcnow()
│   └── logging.py                   # configure_logging()
│
├── bot/                             # Telegram bot сервис
│   ├── __init__.py
│   ├── entrypoint.py                # main(): polling или webhook relay
│   ├── runtime.py                   # build_bot(), build_dispatcher()
│   ├── middleware.py
│   ├── states.py
│   ├── callbacks.py
│   ├── keyboards.py
│   ├── messages.py                  # текстовые шаблоны
│   ├── backend_client.py            # httpx-клиент к backend API
│   └── handlers/                    # сплит god-object router.py
│       ├── __init__.py
│       ├── start.py                 # /start, welcome
│       ├── onboarding.py            # FSM онбординг
│       ├── finance.py               # доход/расход
│       ├── events.py                # календарь, дедлайны
│       ├── ai_consult.py            # AI-консультация
│       ├── subscription.py          # подписка, платежи
│       ├── profile.py               # профиль, настройки
│       ├── help.py                  # /help
│       └── regime.py                # подбор режима
│
├── backend/                         # FastAPI backend сервис
│   ├── __init__.py
│   ├── entrypoint.py                # main(): alembic upgrade head → uvicorn
│   ├── app.py                       # create_app()
│   ├── dependencies.py              # DI: get_session, get_services
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── webhook.py               # Telegram webhook (проксирует в bot)
│   │   ├── admin.py                 # admin CRUD
│   │   ├── finance.py               # API финансов (для bot)
│   │   ├── events.py                # API событий (для bot)
│   │   ├── users.py                 # API пользователей (для bot)
│   │   └── ozon.py                  # Ozon callbacks & sync trigger
│   ├── services/                    # бизнес-логика
│   │   ├── __init__.py
│   │   ├── container.py             # build_services()
│   │   ├── onboarding.py
│   │   ├── calendar.py
│   │   ├── reminders.py
│   │   ├── law_updates.py
│   │   ├── finance.py
│   │   ├── finance_parser.py
│   │   ├── documents.py
│   │   ├── document_templates.py
│   │   ├── tax_engine.py
│   │   ├── ai_gateway.py
│   │   ├── subscription.py
│   │   ├── notifications.py
│   │   ├── event_policies.py
│   │   ├── profile_matching.py
│   │   ├── marketplace_connections.py
│   │   ├── ozon_sync.py
│   │   ├── ozon_content.py
│   │   ├── ozon_feedback.py
│   │   ├── ozon_insights.py
│   │   └── google_sheets_export.py
│   ├── repositories/                # persistence
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── events.py
│   │   ├── finance.py
│   │   ├── reminders.py
│   │   ├── law_updates.py
│   │   ├── subscriptions.py
│   │   ├── marketplace_connections.py
│   │   ├── ozon_data.py
│   │   ├── ozon_insights.py
│   │   └── backend_events.py
│   └── integrations/                # внешние источники
│       ├── __init__.py
│       ├── law_sources.py
│       ├── ozon_seller.py
│       └── ozon_performance.py
│
├── worker/                          # Worker сервис
│   ├── __init__.py
│   ├── entrypoint.py                # main(): Bot singleton + scheduler
│   └── tasks.py                     # задачи (send_due_reminders, deliver_law_updates, sync_ozon, sync_events)
│
├── alembic/                         # миграции (перенесены)
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 20260306_0001_initial_schema.py
│       ├── 20260310_0002_marketplace_connections.py
│       ├── 20260405_0003_subscriptions_and_user_fields.py
│       └── 20260414_0004_admin_metrics_and_activity.py
│
├── docker/                          # Dockerfiles
│   ├── Dockerfile                   # единый образ (multi-stage не нужен)
│   └── entrypoint.sh                # if SERVICE=backend → alembic + uvicorn
│
├── prompts/                         # AI-промты (без изменений)
│   ├── finance_classification.md
│   ├── law_update_summary.md
│   └── legal_qa.md
│
├── data/                            # seed-данные (без изменений)
│   ├── calendar_templates.demo.json
│   └── marketplace_analytics_company_cards.json
│
├── scripts/                         # утилиты
│   ├── backup_db.sh
│   ├── set_webhook.py
│   └── seed_db.py                   # бывший db.bootstrap
│
├── tests/                           # тесты
│   ├── conftest.py                  # фикстуры: fake session, settings
│   ├── unit/
│   │   ├── test_finance_parser.py
│   │   ├── test_tax_engine.py
│   │   ├── test_event_policies.py
│   │   ├── test_profile_matching.py
│   │   ├── test_calendar.py
│   │   ├── test_reminders.py
│   │   ├── test_onboarding.py
│   │   ├── test_subscription.py
│   │   ├── test_notifications.py
│   │   ├── test_secrets.py
│   │   ├── test_config.py
│   │   └── test_ai_gateway.py
│   └── integration/
│       ├── test_api_health.py
│       ├── test_admin_api.py
│       └── test_webhook.py
│
├── docs/                            # документация
│   ├── solution-architecture.md
│   └── REFACTORING_PLAN.md          # этот файл
│
├── .github/
│   └── workflows/
│       └── cd.yml                   # GitHub Actions CD
│
├── docker-compose.yml               # единая точка входа
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml
├── Makefile
└── README.md
```

---

## §4. Маппинг файлов: было → стало

### Принцип Фазы 1
Толстые файлы в Фазе 1 переезжают **целиком** (без сплитов). Сплиты (`bot/router.py` → `handlers/*`) — в Фазе 2.

### Корневые файлы (удаляются после merge в src)

| Было (корень) | Стало | Действие |
|---|---|---|
| `config.py` | ❌ удалить | Merge ozon-полей в `shared/config.py` |
| `secrets.py` | ❌ удалить | Идентичен `shared/secrets.py` |
| `ai_gateway.py` | ❌ удалить | Merge rate-limiting + seller_qa в `backend/services/ai_gateway.py` |
| `container.py` | ❌ удалить | Merge Ozon/GSheets/SecretBox в `backend/services/container.py` |
| `api.py` | ❌ удалить | Merge backend events/Ozon sync в `backend/routers/` |
| `router.py` | ❌ удалить | Устаревший admin router |
| `tasks.py` | ❌ удалить | Merge ozon_sync в `worker/tasks.py` |
| `worker.py` | ❌ удалить | Merge ozon_sync job в `worker/entrypoint.py` |

### Пакет `src/accountant_bot/` → новая структура

| Было | Стало | Действие Ф1 |
|---|---|---|
| `core/config.py` | `shared/config.py` | Переместить + merge |
| `core/secrets.py` | `shared/secrets.py` | Переместить |
| `core/clock.py` | `shared/clock.py` | Переместить |
| `core/logging.py` | `shared/logging.py` | Переместить |
| `core/rate_limit.py` | `backend/services/rate_limit.py` | Переместить (backend-only) |
| `contracts/payloads.py` | `shared/contracts/payloads.py` | Переместить |
| `db/base.py` | `shared/db/base.py` | Переместить |
| `db/enums.py` | `shared/db/enums.py` | Переместить |
| `db/models.py` | `shared/db/models.py` | Переместить |
| `db/session.py` | `shared/db/session.py` | Переместить |
| `db/bootstrap.py` | `scripts/seed_db.py` | Переместить |
| `bot/runtime.py` | `bot/runtime.py` | Переместить |
| `bot/polling.py` | `bot/entrypoint.py` | Переместить + переименовать |
| `bot/middleware.py` | `bot/middleware.py` | Переместить |
| `bot/states.py` | `bot/states.py` | Переместить |
| `bot/callbacks.py` | `bot/callbacks.py` | Переместить |
| `bot/keyboards.py` | `bot/keyboards.py` | Переместить (целиком, без сплита) |
| `bot/messages.py` | `bot/messages.py` | Переместить |
| `bot/router.py` (1 415 стр.) | `bot/handlers/` | **Ф1: целиком** → `bot/handlers/__init__.py` (re-export). **Ф2: сплит** на 9 модулей. |
| `app/api.py` | `backend/app.py` | Переместить + переименовать |
| `admin/router.py` | `backend/routers/admin.py` | Переместить |
| `services/*.py` | `backend/services/*.py` | Переместить все 17 файлов |
| `repositories/*.py` | `backend/repositories/*.py` | Переместить все 7 файлов |
| `integrations/*.py` | `backend/integrations/*.py` | Переместить |
| `jobs/tasks.py` | `worker/tasks.py` | Переместить |
| `jobs/worker.py` | `worker/entrypoint.py` | Переместить + переименовать |

### Конфиги и инфра

| Было | Стало | Действие |
|---|---|---|
| `deploy/docker-compose.prod.yml` | `docker-compose.yml` (корень) | Переписать |
| `deploy/deploy.sh` | ❌ удалить | Заменяется на CD workflow |
| `deploy/nginx/` | `docker/nginx/` | Переместить (webhook profile) |
| `Dockerfile` | `docker/Dockerfile` | Переписать |
| `migrations/` | `alembic/` | Переименовать |
| `alembic.ini` | `alembic.ini` | Обновить path |
| `.env.example` | `.env.example` | Обновить |
| `Makefile` | `Makefile` | Обновить |

---

## §5. docker-compose.yml (черновик)

```yaml
# docker-compose.yml — единственная точка входа: docker compose up -d
x-app: &app-base
  build:
    context: .
    dockerfile: docker/Dockerfile
  env_file: .env
  restart: unless-stopped
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_started

services:
  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-pocket_accountant}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data

  backend:
    <<: *app-base
    command: ["python", "-m", "backend.entrypoint"]
    # entrypoint.py: alembic upgrade head → uvicorn
    ports:
      - "${API_PORT:-8080}:8080"

  bot:
    <<: *app-base
    command: ["python", "-m", "bot.entrypoint"]
    depends_on:
      backend:
        condition: service_started
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  worker:
    <<: *app-base
    command: ["python", "-m", "worker.entrypoint"]

  # Опционально: nginx для webhook-режима
  nginx:
    image: nginx:1.27-alpine
    profiles: ["webhook"]
    restart: unless-stopped
    depends_on:
      - backend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/accountant-bot.conf:/etc/nginx/conf.d/default.conf:ro

volumes:
  pg_data:
  redis_data:
```

### Заметки

- `backend` — запускает Alembic в entrypoint, затем uvicorn. Миграции выполняются **до** старта API.
- `bot` — зависит от `backend` (нужен API). При `TELEGRAM_DELIVERY_MODE=polling` использует long polling. При webhook — принимает update из nginx → backend → relay в bot (или bot напрямую слушает webhook path).
- `worker` — зависит от postgres + redis. Bot singleton для исходящих.
- `healthcheck` на postgres — чтобы backend не стартовал до готовности БД.

---

## §6. .env.example + .gitignore

### .env.example

```bash
# ── App ──────────────────────────────────────────────
APP_ENV=development
APP_NAME=Pocket Accountant Bot
APP_BASE_URL=http://localhost:8080
APP_SECRET_KEY=                          # Fernet key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ALLOW_INSECURE_SECRET_STORAGE=false
EXPOSE_API_DOCS=false
API_HOST=0.0.0.0
API_PORT=8080
LOG_LEVEL=INFO
TIMEZONE=Europe/Moscow

# ── Telegram ─────────────────────────────────────────
TELEGRAM_BOT_TOKEN=
TELEGRAM_DELIVERY_MODE=polling           # polling | webhook
TELEGRAM_WEBHOOK_SECRET=
TELEGRAM_WEBHOOK_PATH=/telegram/webhook
TELEGRAM_WEBHOOK_URL=
ADMIN_TELEGRAM_IDS=                      # comma-separated
ADMIN_API_TOKEN=change-me
ADMIN_ALLOWED_IPS=
ADMIN_TOKENS=                            # role:token pairs, comma-separated
TESTER_TELEGRAM_IDS=

# ── Database ─────────────────────────────────────────
POSTGRES_DB=pocket_accountant
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

# ── Redis ────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── AI / LLM ────────────────────────────────────────
LLM_PROVIDER=openrouter                  # openai | openrouter | disabled
LLM_TIMEOUT_SECONDS=30
AI_ENABLED=false
AI_MAX_REQUESTS_PER_MINUTE=30
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4.1-nano
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=
OPENROUTER_APP_NAME=Pocket Accountant Bot

# ── Subscription / Stars ─────────────────────────────
FREE_AI_REQUESTS_PER_DAY=3
STARS_PRICE_BASIC=150
STARS_PRICE_PRO=400
STARS_PRICE_ANNUAL=3500

# ── Jobs ─────────────────────────────────────────────
REMINDER_BATCH_SIZE=100
LAW_MIN_IMPORTANCE_SCORE=70
LAW_FETCH_INTERVAL_MINUTES=60
REMINDER_DISPATCH_INTERVAL_MINUTES=5
USER_EVENT_SYNC_HOUR=3

# ── Ozon ─────────────────────────────────────────────
OZON_API_BASE_URL=https://api-seller.ozon.ru
OZON_API_TIMEOUT_SECONDS=30
OZON_ADS_API_BASE_URL=https://api-performance.ozon.ru
OZON_ADS_API_TIMEOUT_SECONDS=30
OZON_SYNC_INTERVAL_MINUTES=30
OZON_SYNC_DAYS_BACK=30
OZON_SYNC_BATCH_LIMIT=20

# ── Google Sheets ────────────────────────────────────
GOOGLE_SHEETS_ENABLED=false
GOOGLE_SHEETS_SPREADSHEET_ID=
GOOGLE_SERVICE_ACCOUNT_JSON=

# ── Law sources ──────────────────────────────────────
FNS_SOURCE_URL=https://www.nalog.gov.ru/
MINFIN_SOURCE_URL=https://minfin.gov.ru/
GOV_SOURCE_URL=https://government.ru/
DUMA_SOURCE_URL=https://sozd.duma.gov.ru/
```

### .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.egg
.venv/
venv/

# Env / secrets
.env
.env.local
.env.production

# DB
*.db
*.sqlite3

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# Testing / quality
.mypy_cache/
.pytest_cache/
.coverage
htmlcov/
.ruff_cache/

# Logs
*.log

# OS
.DS_Store
Thumbs.db
```

---

## §7. GitHub Actions CD workflow

```yaml
# .github/workflows/cd.yml
name: CD — deploy to production

on:
  push:
    branches: [main]

env:
  DEPLOY_HOST: ${{ secrets.DEPLOY_HOST }}
  DEPLOY_USER: ${{ secrets.DEPLOY_USER }}
  DEPLOY_PATH: ${{ secrets.DEPLOY_PATH }}           # e.g. /opt/pocket-accountant
  SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint (ruff)
        run: ruff check .

      - name: Tests
        run: pytest --tb=short -q
        env:
          DATABASE_URL: "sqlite+aiosqlite:///test.db"
          REDIS_URL: "redis://localhost:6379/0"

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "$SSH_PRIVATE_KEY" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          ssh-keyscan -H "$DEPLOY_HOST" >> ~/.ssh/known_hosts

      - name: Sync files to server
        run: |
          rsync -avz --delete \
            --exclude='.git' \
            --exclude='.env' \
            --exclude='__pycache__' \
            --exclude='.venv' \
            -e "ssh -i ~/.ssh/deploy_key" \
            ./ "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/"

      - name: Rebuild and restart
        run: |
          ssh -i ~/.ssh/deploy_key "${DEPLOY_USER}@${DEPLOY_HOST}" \
            "cd ${DEPLOY_PATH} && docker compose up -d --build"
```

### Секреты GitHub Actions

| Secret | Описание |
|---|---|
| `DEPLOY_HOST` | IP или домен прод-сервера |
| `DEPLOY_USER` | SSH-пользователь |
| `DEPLOY_PATH` | Путь к проекту на сервере (e.g. `/opt/pocket-accountant`) |
| `SSH_PRIVATE_KEY` | Приватный SSH-ключ для деплоя |

---

## §8. Дорожная карта по фазам

### Фаза 0 — Git + Cleanup (1 день)

**Цель:** чистый репозиторий, готовый к рефакторингу.

- [ ] Создать ветку `refactor/phase-0-cleanup` от `main`
- [ ] Удалить пустой каталог `containerd/`
- [ ] Добавить `.gitignore` (из §6)
- [ ] Удалить `deploy/deploy.sh` (заменяется CD)
- [ ] Удалить `scripts/vpn_test_runner.sh` (инфра-утилита, не нужна в репо)
- [ ] Удалить `scripts/post_ops.py` (одноразовый скрипт)
- [ ] Обновить `README.md` (краткое описание + ссылка на план)
- [ ] Commit → PR → merge в `main`

---

### Фаза 1 — Структура каталогов, без сплитов (2–3 дня)

**Цель:** код переезжает в целевые каталоги. Файлы перемещаются **целиком** (без разбивки на подмодули). Merge дублей. Всё работает `docker compose up -d`.

- [ ] Создать ветку `refactor/phase-1-structure` от `main`
- [ ] Создать каталог `shared/` с `__init__.py`
- [ ] Переместить `src/accountant_bot/core/config.py` → `shared/config.py`
  - Merge полей из корневого `config.py` (ozon, google sheets)
  - Удалить корневой `config.py`
- [ ] Переместить `src/accountant_bot/core/secrets.py` → `shared/secrets.py`
  - Удалить корневой `secrets.py`
- [ ] Переместить `src/accountant_bot/core/clock.py` → `shared/clock.py`
- [ ] Переместить `src/accountant_bot/core/logging.py` → `shared/logging.py`
- [ ] Переместить `src/accountant_bot/db/` → `shared/db/`
- [ ] Переместить `src/accountant_bot/contracts/` → `shared/contracts/`
- [ ] Создать каталог `bot/` (top-level)
- [ ] Переместить `src/accountant_bot/bot/*.py` → `bot/`
- [ ] `bot/polling.py` → `bot/entrypoint.py` (переименовать)
- [ ] `bot/router.py` (1 415 стр.) → `bot/handlers/__init__.py` (целиком, сплит — Фаза 2)
- [ ] Создать `bot/backend_client.py` — заглушка httpx-клиента (пустой класс, наполним в Фазе 2)
- [ ] Создать каталог `backend/`
- [ ] Переместить `src/accountant_bot/app/api.py` → `backend/app.py`
- [ ] Переместить `src/accountant_bot/admin/router.py` → `backend/routers/admin.py`
- [ ] Переместить `src/accountant_bot/services/` → `backend/services/`
  - Merge корневого `ai_gateway.py` (rate limiting, seller_qa) в `backend/services/ai_gateway.py`
  - Merge корневого `container.py` (Ozon, GSheets, SecretBox) в `backend/services/container.py`
  - Удалить корневые `ai_gateway.py`, `container.py`
- [ ] Переместить `src/accountant_bot/repositories/` → `backend/repositories/`
- [ ] Переместить `src/accountant_bot/integrations/` → `backend/integrations/`
- [ ] `src/accountant_bot/core/rate_limit.py` → `backend/services/rate_limit.py`
- [ ] Создать каталог `worker/`
- [ ] Переместить `src/accountant_bot/jobs/tasks.py` → `worker/tasks.py`
  - Merge корневого `tasks.py` (ozon_sync)
  - Удалить корневой `tasks.py`
- [ ] Переместить `src/accountant_bot/jobs/worker.py` → `worker/entrypoint.py`
  - Merge корневого `worker.py` (ozon_sync job)
  - Удалить корневой `worker.py`
- [ ] Удалить корневой `api.py`, `router.py`
- [ ] Переименовать `migrations/` → `alembic/`
- [ ] Обновить `alembic.ini` — путь к `alembic/`
- [ ] Обновить `alembic/env.py` — импорт из `shared.db`
- [ ] Перенести `Dockerfile` → `docker/Dockerfile`, обновить COPY paths
- [ ] Перенести `deploy/nginx/` → `docker/nginx/`
- [ ] Удалить `deploy/` (целиком)
- [ ] Обновить `pyproject.toml`:
  - `package-dir` → убрать, сделать root packages: `shared`, `bot`, `backend`, `worker`
  - `packages.find.where = ["."]`
- [ ] Обновить `Makefile`
- [ ] Обновить все import paths во всех `.py` файлах: `accountant_bot.` → `shared.` / `bot.` / `backend.` / `worker.`
- [ ] Удалить пустой каталог `src/`
- [ ] Проверить: `docker compose up -d` → все 5 контейнеров стартуют
- [ ] Commit → PR → merge в `main`

---

### Фаза 2 — Разделение сервисов (3–5 дней)

**Цель:** bot не ходит в БД. Все данные — через httpx → backend API. Worker работает с БД напрямую.

- [ ] Создать ветку `refactor/phase-2-services` от `main`
- [ ] **Сплит bot/router.py** → 9 handler-модулей:
  - `bot/handlers/start.py` — `/start`, welcome, main menu
  - `bot/handlers/onboarding.py` — FSM онбординг (States, entity type, tax, region)
  - `bot/handlers/finance.py` — добавление дохода/расхода, отчёты
  - `bot/handlers/events.py` — календарь, дедлайны, actions
  - `bot/handlers/ai_consult.py` — AI-консультация, FSM
  - `bot/handlers/subscription.py` — подписка, Telegram Stars, платежи
  - `bot/handlers/profile.py` — профиль, настройки, referral
  - `bot/handlers/help.py` — `/help`, FAQ
  - `bot/handlers/regime.py` — подбор налогового режима
- [ ] **Backend API эндпоинты** (для bot):
  - `POST /api/users/ensure` — создать/получить пользователя по telegram_id
  - `GET /api/users/{user_id}/profile`
  - `POST /api/users/{user_id}/onboarding`
  - `GET /api/events/{user_id}/upcoming`
  - `POST /api/events/{user_event_id}/action` (complete/dismiss/snooze)
  - `POST /api/finance/{user_id}/record`
  - `GET /api/finance/{user_id}/report`
  - `POST /api/ai/{user_id}/question`
  - `GET /api/subscription/{user_id}/status`
  - `POST /api/subscription/{user_id}/activate`
  - `POST /api/tax/calculate`
- [ ] **bot/backend_client.py** — реализация httpx-клиента ко всем эндпоинтам
- [ ] Удалить из `bot/` все импорты `shared.db.session`, `shared.db.models`
- [ ] Worker: Bot singleton, output-only:
  - `bot = Bot(token=BOT_TOKEN)` в `worker/entrypoint.py`
  - Запрещено: `set_webhook`, `delete_webhook`, `get_updates`, `Dispatcher`, `start_polling`
  - В shutdown: `await bot.session.close()`
  - `DefaultBotProperties` — идентичны bot-сервису
- [ ] Проверить: все контейнеры стартуют, bot вызывает backend через httpx
- [ ] Commit → PR → merge в `main`

---

### Фаза 3 — Docker Compose production-ready (1–2 дня)

**Цель:** `docker-compose.yml` финальный, единственная точка входа.

- [ ] Создать ветку `refactor/phase-3-docker` от `main`
- [ ] Финализировать `docker-compose.yml` (из §5):
  - healthcheck на postgres
  - depends_on с condition
  - volume mounts
  - webhook nginx profile
- [ ] `docker/Dockerfile` — один образ, multi-CMD через переменную `SERVICE`
- [ ] `docker/entrypoint.sh`:
  ```bash
  #!/bin/bash
  set -e
  case "$SERVICE" in
    backend)
      alembic upgrade head
      exec uvicorn backend.app:create_app --factory --host 0.0.0.0 --port 8080
      ;;
    bot)
      exec python -m bot.entrypoint
      ;;
    worker)
      exec python -m worker.entrypoint
      ;;
  esac
  ```
- [ ] Проверить: `docker compose up -d` — все 5 контейнеров healthy
- [ ] Проверить: `docker compose down && docker compose up -d` — идемпотентно
- [ ] Commit → PR → merge в `main`

---

### Фаза 4 — Тесты 75% (5–7 дней)

**Цель:** pytest + pytest-cov ≥ 75% покрытие.

- [ ] Создать ветку `refactor/phase-4-tests` от `main`
- [ ] Добавить `pytest-cov`, `pytest-asyncio`, `httpx` (для TestClient) в dev-зависимости
- [ ] `pyproject.toml`:
  ```toml
  [tool.pytest.ini_options]
  asyncio_mode = "auto"
  testpaths = ["tests"]
  
  [tool.coverage.run]
  source = ["shared", "bot", "backend", "worker"]
  omit = ["*/migrations/*", "*/alembic/*"]
  ```
- [ ] `tests/conftest.py`:
  - Фикстура `fake_settings` — Settings с SQLite in-memory
  - Фикстура `db_session` — AsyncSession для тестов
  - Фикстура `test_client` — FastAPI TestClient
- [ ] **Unit-тесты** (приоритет — самые толстые модули):
  - [ ] `test_tax_engine.py` — полное покрытие TaxCalculatorService + TaxQueryParser (446 стр.)
  - [ ] `test_finance_parser.py` — все категории + edge cases
  - [ ] `test_event_policies.py` — расширить существующий
  - [ ] `test_profile_matching.py` — расширить существующий
  - [ ] `test_calendar.py` — CalendarService.sync_user_events, upcoming
  - [ ] `test_reminders.py` — ReminderService.create_reminders_for_event, due_reminders
  - [ ] `test_onboarding.py` — OnboardingService полный CRUD
  - [ ] `test_subscription.py` — SubscriptionService: activate, check, limits
  - [ ] `test_notifications.py` — NotificationComposer
  - [ ] `test_secrets.py` — SecretBox encrypt/decrypt/edge cases
  - [ ] `test_config.py` — Settings properties, admin_tokens parsing
  - [ ] `test_ai_gateway.py` — mock OpenAI, NoopProvider, rate limiting
  - [ ] `test_finance_service.py` — FinanceService CRUD + report
  - [ ] `test_documents.py` — DocumentsService
  - [ ] `test_law_updates.py` — LawUpdateService
- [ ] **Integration-тесты** (с TestClient):
  - [ ] `test_api_health.py` — GET /health
  - [ ] `test_admin_api.py` — admin endpoints с auth
  - [ ] `test_webhook.py` — POST /telegram/webhook (mock update)
- [ ] Запустить `pytest --cov --cov-report=term-missing` → ≥ 75%
- [ ] Добавить в CI: `pytest --cov --cov-fail-under=75`
- [ ] Commit → PR → merge в `main`

---

### Фаза 5 — CD + Smoke на проде (1–2 дня)

**Цель:** push в `main` → автоматический деплой → smoke-тест.

- [ ] Создать ветку `refactor/phase-5-cd` от `main`
- [ ] Добавить `.github/workflows/cd.yml` (из §7)
- [ ] Настроить GitHub Secrets (DEPLOY_HOST, DEPLOY_USER, DEPLOY_PATH, SSH_PRIVATE_KEY)
- [ ] Добавить smoke-тест в workflow:
  ```yaml
  - name: Smoke test
    run: |
      ssh -i ~/.ssh/deploy_key "${DEPLOY_USER}@${DEPLOY_HOST}" \
        "curl -sf http://localhost:8080/health || exit 1"
  ```
- [ ] Первый деплой: push в main → rsync → docker compose up -d --build
- [ ] Проверить:
  - [ ] `curl /health` → 200
  - [ ] Telegram bot отвечает на /start
  - [ ] Worker логирует `worker_started`
  - [ ] Alembic migration applied
- [ ] Commit → PR → merge в `main`

---

## Итого

| Фаза | Цель | Ориентировочно |
|---|---|---|
| 0 | Git cleanup | 1 день |
| 1 | Структура каталогов (без сплитов) | 2–3 дня |
| 2 | Разделение сервисов (bot ↔ backend ↔ worker) | 3–5 дней |
| 3 | Docker Compose production-ready | 1–2 дня |
| 4 | Тесты ≥ 75% | 5–7 дней |
| 5 | CD + smoke на проде | 1–2 дня |
| **Итого** | | **13–20 дней** |

### Зависимости между фазами

```
Фаза 0 → Фаза 1 → Фаза 2 → Фаза 3 → Фаза 5
                                ↘
                          Фаза 4 (можно параллельно с Фазой 3)
```

### Критерии приёмки (для архитектора)

1. Каждая фаза — отдельный PR.
2. `docker compose up -d` — работает после каждой фазы.
3. Существующие тесты проходят после каждой фазы.
4. Нет прямых импортов `shared.db.*` из `bot/` (после Фазы 2).
5. Worker не использует Dispatcher / polling (после Фазы 2).
6. Покрытие ≥ 75% (после Фазы 4).
7. Push в `main` → деплой на сервер (после Фазы 5).
