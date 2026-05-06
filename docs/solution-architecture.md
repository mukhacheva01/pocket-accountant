# AI-Бухгалтер / Telegram Tax Assistant

## 1. Полная архитектура проекта

### Runtime layout

- `api` process: FastAPI, Telegram webhook endpoint, health checks, admin API.
- `worker` process: APScheduler jobs, reminder dispatch, law-update delivery, calendar sync.
- `postgres`: primary relational store for users, templates, events, reminders, law updates, finance.
- `redis`: transient state, rate limits, lightweight queueing, future cache layer.

### Architectural principles

- Telegram handlers only orchestrate I/O and FSM.
- Business logic lives in `services/`.
- Persistence lives in `repositories/`.
- Models and contracts are shared across `bot`, `app`, and `jobs`.
- AI calls go through one gateway only.
- Legal data is never trusted without source metadata and moderation when impact is material.

### MVP operating model

- Admin curates template events and approves legal updates.
- User profile drives event personalization.
- Worker expands templates into user events and schedules reminders.
- Bot surfaces deadlines, documents, finance input, and AI explanations.

## 2. Структура директорий

```text
.
├── data/
├── docs/
├── prompts/
├── src/accountant_bot/
│   ├── admin/
│   ├── app/
│   ├── bot/
│   ├── contracts/
│   ├── core/
│   ├── db/
│   ├── integrations/
│   ├── jobs/
│   ├── repositories/
│   └── services/
├── tests/
├── .env.example
├── Dockerfile
├── Makefile
├── docker-compose.yml
└── pyproject.toml
```

### Module intent

- `bot/`: commands, callback handlers, keyboards, FSM onboarding.
- `app/`: FastAPI factory and webhook entry.
- `services/`: onboarding, calendar, reminders, laws, finance, AI gateway, notifications.
- `integrations/`: fetcher interfaces for official sources.
- `jobs/`: scheduler bootstrap and periodic tasks.
- `admin/`: token-protected admin endpoints.
- `contracts/`: payload contracts shared between services and jobs.

## 3. Схема БД

### Core tables

- `users`
  - `telegram_id` unique
  - `timezone`, `locale`, `is_active`
- `business_profiles`
  - `user_id` unique FK
  - `entity_type`, `tax_regime`, `has_employees`, `marketplaces_enabled`
  - `region`, `industry`, `reminder_settings`
- `calendar_events`
  - template catalog
  - profile applicability fields
  - `due_date`, `recurrence_rule`, `notification_offsets`
  - `requires_manual_review`
- `user_events`
  - personalized event instances
  - `status`, `dismissed`, `completed_at`, `snoozed_until`
- `reminders`
  - one row per reminder delivery attempt
  - unique `(user_event_id, reminder_type)` for idempotency
- `law_updates`
  - normalized regulatory updates with tags, impact, source metadata, review status
- `law_update_deliveries`
  - once-per-user delivery ledger
- `finance_records`
  - free-text source plus parsed payload
- `ai_dialogs`
  - audit trail for answers and source metadata
- `admin_logs`
  - moderation and bulk actions

### Data model decisions

- Template events are separated from user events so one legal change can regenerate future obligations.
- Reminder idempotency lives in DB, not only in memory.
- Law updates are delivered only after moderation for high-impact changes.
- Financial records keep raw text for auditability and parser improvements.

## 4. Список env переменных

### Application

- `APP_ENV`
- `APP_NAME`
- `APP_BASE_URL`
- `API_HOST`
- `API_PORT`
- `LOG_LEVEL`
- `TIMEZONE`

### Telegram

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`
- `TELEGRAM_WEBHOOK_PATH`
- `TELEGRAM_WEBHOOK_URL`
- `ADMIN_TELEGRAM_IDS`
- `ADMIN_API_TOKEN`

### Storage and queue

- `DATABASE_URL`
- `REDIS_URL`

### AI

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `AI_ENABLED`
- `AI_MAX_REQUESTS_PER_MINUTE`

### Jobs

- `REMINDER_BATCH_SIZE`
- `LAW_MIN_IMPORTANCE_SCORE`
- `LAW_FETCH_INTERVAL_MINUTES`
- `REMINDER_DISPATCH_INTERVAL_MINUTES`
- `USER_EVENT_SYNC_HOUR`

### Sources

- `FNS_SOURCE_URL`
- `MINFIN_SOURCE_URL`
- `GOV_SOURCE_URL`
- `DUMA_SOURCE_URL`

## 5. Roadmap по шагам

### Phase 1: MVP

1. Scaffold runtime, config, DB models, Docker stack.
2. Build onboarding FSM and business profile persistence.
3. Add template events, personalization, and nearest deadlines view.
4. Add reminder generation and delivery worker.
5. Add "what do I need to file" scenario.
6. Add law-update ingest pipeline with admin review.
7. Add admin API and admin bot whitelist.
8. Add basic finance parsing and 30-day report.
9. Add AI Q&A through gateway with disclaimer.

### Phase 2

1. Replace heuristics with AI-assisted finance parsing fallback.
2. Add recurring-event expansion engine.
3. Add richer admin moderation workflows.
4. Add source-specific fetchers and deduplication scoring.
5. Add user data export/delete flows.

### Phase 3

1. Multi-business profiles per Telegram account.
2. White-label tenant config.
3. Dedicated queue workers and horizontal scaling.
4. Marketplace integrations and bank statement imports.

## 6. Ключевые модули

- `OnboardingService`: creates user and business profile.
- `CalendarService`: matches template obligations to profile and syncs user events.
- `ReminderService`: creates and dispatches reminder rows.
- `LawUpdateService`: filters approved changes by profile relevance.
- `FinanceService`: parses text records and builds summaries.
- `AIGateway`: single entry point for LLM usage.
- `NotificationComposer`: creates delivery payloads for Telegram.
- `Admin API`: moderation and operational visibility.

## 7. Контракты между модулями

### Handler -> Service

- Input: Telegram user id, command payload, FSM data.
- Output: domain object or DTO-ready dict.
- Rule: no raw SQL or model-provider calls in handlers.

### Service -> Repository

- Input: validated domain parameters.
- Output: persisted ORM entity or list.
- Rule: repositories never compose Telegram text.

### Worker -> Service

- Input: schedule tick plus config.
- Output: pending reminders, delivered updates, sync counts.
- Rule: worker owns retries and batch limits.

### Service -> AI Gateway

- Input: `purpose` + structured payload.
- Output: `AIResponse { text, sources, confidence }`.
- Rule: service adds user-facing disclaimer and fallbacks.

## 8. Сценарии onboarding

### Flow

1. `/start`
2. Ask `entity_type`
3. Ask `tax_regime`
4. Ask `has_employees`
5. Ask `marketplaces_enabled`
6. Ask `industry`
7. Ask `region`
8. Ask `timezone`
9. Ask reminder offsets
10. Persist `users` + `business_profiles`
11. Sync template calendar events into `user_events`
12. Show main menu and nearest events

### Validation rules

- Only allow known entity and tax-regime options in FSM buttons.
- Timezone must be IANA name in production validation.
- Reminder offsets are normalized to `[7, 3, 1, 0]` subset.

## 9. Сценарии уведомлений

### Reminder notification

- Triggered at `D-7`, `D-3`, `D-1`, `D0`, `D+1`.
- Message body:
  - what the event is
  - deadline
  - what to do
  - consequence hint
- Buttons:
  - `Выполнено`
  - `Отложить`
  - `Документы`
  - `Подробнее`

### Law update notification

- Triggered after admin approval and relevance filtering.
- Message body:
  - what changed
  - who it affects
  - effective date
  - action required
  - source link

## 10. Cron/jobs архитектура

### Implemented jobs

- `sync_user_events`
  - daily at `USER_EVENT_SYNC_HOUR`
  - re-applies templates to active profiles
- `send_due_reminders`
  - every `REMINDER_DISPATCH_INTERVAL_MINUTES`
  - sends unsent reminders with `scheduled_at <= now`
- `deliver_law_updates`
  - every `LAW_FETCH_INTERVAL_MINUTES`
  - sends relevant approved updates

### Recommended next jobs

- `fetch_law_updates`
  - pull official sources hourly
- `plan_future_reminders`
  - materialize reminders for newly created `user_events`
- `cleanup_exports`
  - prune expired export files
- `retry_failed_deliveries`
  - retry Telegram send failures with capped backoff

## 11. Format payload для law updates

```json
{
  "law_update_id": "uuid",
  "source": "FNS",
  "title": "Изменение формы уведомления",
  "summary": "Короткое пояснение простым языком",
  "published_at": "2026-03-06T10:00:00Z",
  "effective_date": "2026-04-01",
  "affected_profiles": ["ip:usn_income", "ooo:osno"],
  "importance_score": 84,
  "action_required": "Проверить, нужно ли обновить шаблон подачи",
  "source_url": "https://example.gov/item",
  "needs_admin_review": true
}
```

## 12. Format payload для reminders

```json
{
  "reminder_id": "uuid",
  "user_id": "uuid",
  "user_event_id": "uuid",
  "reminder_type": "days_3",
  "scheduled_at": "2026-04-22T06:00:00Z",
  "due_date": "2026-04-25",
  "title": "Проверить квартальные обязательства по УСН",
  "description": "Что именно нужно сделать",
  "category": "tax",
  "legal_basis": "manual review",
  "consequence_hint": "Возможны штрафы или блокирующие последствия",
  "action_required": "Подготовьте документы и закройте обязательство",
  "buttons": ["mark_done", "details", "documents", "snooze"]
}
```

## 13. Format payload для finance records

```json
{
  "record_type": "expense",
  "amount": 35000.0,
  "currency": "RUB",
  "category": "marketing",
  "subcategory": null,
  "operation_date": "2026-03-06",
  "source_text": "расход 35000 реклама",
  "parsed_payload": {
    "confidence": 0.78
  },
  "confidence": 0.78
}
```

## 14. Примеры Telegram UI flow

### Main menu

- `Мои ближайшие события`
- `Что нужно подать`
- `Налоговый календарь`
- `Напоминания`
- `Новости законов`
- `Финансы`
- `Настройки`
- `Помощь`

### Example flow: nearest events

1. User taps `Мои ближайшие события`
2. Bot returns top 5 nearest user events
3. Inline keyboard on first item:
   - `Выполнено`
   - `Отложить`
   - `Еще`
4. Bot edits the same message on callback

### Example flow: finance input

1. User sends `/add_expense расход 35000 реклама`
2. Parser extracts amount and category
3. Bot confirms saved record
4. User sends `/report`
5. Bot returns income, expenses, profit, top expense categories

## 15. MVP backlog

- [x] Config, Docker, package structure
- [x] DB models and repositories
- [x] Onboarding FSM
- [x] Main commands and menus
- [x] Calendar sync service
- [x] Reminder contracts and worker
- [x] Law update relevance service
- [x] Finance text parser
- [x] Admin API skeleton
- [x] Alembic migrations
- [x] Seed loader for calendar templates
- [x] Production deploy scaffold
- [ ] Rate limiting with Redis
- [ ] Data export/delete endpoints
- [ ] Source-specific fetchers
- [ ] True recurring-event engine
- [ ] Delivery retry/backoff ledger

## 16. Production checklist

- Enforce HTTPS and webhook secret.
- Move from demo templates to verified moderated templates.
- Add Alembic migration baseline.
- Validate timezones against IANA database.
- Add Redis-based rate limits per `telegram_id`.
- Add Telegram send retry with jitter and dead-letter logging.
- Add advisory lock or leader election for scheduler in multi-instance mode.
- Add user data export and deletion flow.
- Add admin audit log on approve/reject/broadcast actions.
- Add backup and restore for Postgres.

## 17. Рекомендации по деплою на сервер

### Recommended topology

- 1 VM for MVP
- Docker Compose with `api`, `worker`, `postgres`, `redis`
- Nginx or Caddy in front of `api`
- Telegram webhook routed to `https://<domain>/telegram/webhook`

### Hardening

- Run app containers as non-root.
- Keep Postgres and Redis private to Docker network.
- Terminate TLS at reverse proxy.
- Store `.env` outside repo and rotate tokens.
- Restrict admin API by token and IP allowlist where possible.

### Rollout

1. Provision domain and TLS.
2. Populate `.env`.
3. `docker compose up -d --build`
4. Check `/health` and `/admin/health`
5. Set Telegram webhook
6. Load reviewed template events
7. Enable scheduler

## 18. Рекомендации по логированию и мониторингу

### Logging

- JSON logs from both `api` and `worker`
- Log fields:
  - `event`
  - `telegram_id`
  - `user_id`
  - `job_name`
  - `reminder_id`
  - `law_update_id`
  - `trace_id`
- Never log tokens or personal free-text beyond what is needed for debugging.

### Monitoring

- Health checks: `/health`, `/admin/health`
- Metrics to add next:
  - reminders scheduled
  - reminders sent
  - reminder failures
  - law updates fetched
  - law updates approved
  - AI requests and failures
- Error tracking:
  - application exceptions
  - Telegram API failures
  - DB connectivity
  - job lag

## 19. Рекомендации по масштабированию

### Near-term

- Separate reminder planning from reminder sending.
- Replace in-process scheduler with dedicated worker leadership or queue.
- Add Redis cache for user profile and menu read paths.

### Mid-term

- Move to dedicated job queue for reminder and law delivery fan-out.
- Partition `user_events` and `reminders` by month if volume grows.
- Add per-tenant configuration if white-label mode is introduced.

### High-scale rules

- Webhook receivers stay stateless.
- Only one scheduler leader plans jobs at a time.
- Delivery workers are horizontally scalable and idempotent.
- Legal content pipeline remains moderated and source-traceable.
