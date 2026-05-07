# Стратегия тестирования — Pocket Accountant Bot

## Обзор

Проект использует **pytest** + **pytest-asyncio** + **pytest-cov** для тестирования.
Порог покрытия: **≥ 75%** (`fail_under = 75` в `pyproject.toml`).

---

## Структура тестов

```
tests/
├── conftest.py                        # Общие фикстуры (fake_settings, fake_async_session)
├── unit/                              # Модульные тесты (изолированные, без БД)
│   ├── test_handlers_helpers.py       # Утилиты хэндлеров: _entity_label, _format_records и т.д.
│   ├── test_handlers_commands.py      # Обработчики команд: /start, /menu, /help...
│   ├── test_handlers_onboarding.py    # FSM онбординга: entity_type → tax → employees → region
│   ├── test_handlers_finance.py       # FSM финансов: income/expense state handlers
│   ├── test_handlers_regime.py        # FSM подбора режима: activity → income → employees → ...
│   ├── test_handlers_callbacks.py     # Callback handlers: NavigationCallback, SubscriptionCallback
│   ├── test_handlers_ai.py           # AI консультация: chatting state, topic shortcuts, catch-all
│   ├── test_keyboards.py             # Фабрики клавиатур
│   ├── test_messages.py              # Шаблоны текстов
│   ├── test_callbacks.py             # Callback-классы (NavigationCallback, EventActionCallback)
│   ├── test_states.py                # FSM-состояния
│   ├── test_middleware.py            # Middleware (ErrorHandler, UserInject)
│   ├── test_backend_client.py        # HTTP-клиент к бэкенду
│   ├── test_runtime.py              # Runtime-модуль
│   ├── test_config.py               # Настройки (shared.config)
│   ├── test_tax_engine.py           # Налоговый калькулятор
│   ├── test_finance_parser.py       # Парсер финансовых операций
│   ├── test_finance_service.py      # Финансовый сервис
│   ├── test_event_policies.py       # Политики событий
│   ├── test_profile_matching.py     # Матчинг профиля
│   ├── test_ai_gateway.py          # AI шлюз
│   ├── test_ai_providers.py        # AI провайдеры (OpenAI, OpenRouter)
│   ├── test_subscription.py        # Подписки
│   ├── test_reminders.py           # Напоминания
│   ├── test_secrets.py             # Шифрование секретов
│   ├── test_enums.py               # Перечисления
│   └── ...
├── integration/                      # Интеграционные тесты (in-memory SQLite)
│   ├── conftest.py                  # AsyncSession + TestClient фикстуры
│   ├── test_admin_router.py        # Админ-роутер
│   ├── test_repositories.py        # Репозитории (CRUD)
│   └── ...
```

---

## Подход к тестированию бота

### Уровни тестирования

| Уровень | Что тестируем | Как тестируем |
|---------|--------------|---------------|
| **Unit** | Утилитарные функции хэндлеров | Прямой вызов функции |
| **Unit** | Команды и FSM-хэндлеры | Mock `Message`, `FSMContext`, `SessionFactory`, `build_services` |
| **Unit** | Callback-хэндлеры | Mock `CallbackQuery`, `NavigationCallback` |
| **Unit** | Middleware | Mock `TelegramObject`, `handler` |
| **Unit** | Клавиатуры, сообщения | Прямой вызов, проверка структуры |
| **Integration** | API-роутеры | `httpx.AsyncClient` + TestClient |
| **Integration** | Репозитории | In-memory SQLite через `aiosqlite` |

### Паттерн мокирования для хэндлеров

Все хэндлеры бота вызывают `SessionFactory` и `build_services` для работы с БД.
Тестируем через `unittest.mock.patch`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

def _mock_message(text="/start", user_id=123, first_name="Test", username="tester"):
    msg = AsyncMock(spec=Message)
    msg.text = text
    msg.from_user = MagicMock(id=user_id, first_name=first_name, username=username)
    msg.answer = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.bot = AsyncMock()
    msg.chat = MagicMock(id=user_id)
    return msg

def _mock_state():
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={})
    state.get_state = AsyncMock(return_value=None)
    return state

# Пример теста:
@patch("bot.handlers.SessionFactory")
@patch("bot.handlers.build_services")
async def test_start_handler(mock_build, mock_sf):
    router = build_router()
    ...
```

### Фикстура `router_and_services`

Для тестирования хэндлеров создаётся фикстура, которая:
1. Патчит `SessionFactory` — возвращает mock сессию
2. Патчит `build_services` — возвращает mock сервисы
3. Вызывает `build_router()` — получает готовый роутер с хэндлерами

---

## Что покрывается тестами бота

### Утилитарные функции (100% покрытие)
- `_entity_label()` — маппинг EntityType → русская строка
- `_tax_regime_label()` — маппинг TaxRegime → русская строка
- `_category_label()` — маппинг категории → русская строка
- `_contains_hint()` — поиск подсказки в тексте
- `_normalize_finance_text()` — нормализация текста финансовой операции
- `_planned_entity_label()` — метка планируемого бизнеса
- `_format_records()` — форматирование списка записей
- `_format_money()` — форматирование суммы

### FSM-хэндлеры (основные сценарии)
- **Онбординг:** ИП → УСН 6% → нет сотрудников → Москва → профиль создан
- **Онбординг:** Самозанятый → регион → профиль (пропуск шага tax)
- **Финансы:** ввод дохода/расхода текстом, ошибки парсинга
- **Режим:** прохождение 5-шагового визарда, валидация на каждом шаге

### Callback-хэндлеры
- `NavigationCallback` → маппинг target → show_* функция
- `SubscriptionCallback` → покупка подписки (invoice)
- `EventActionCallback` → snooze / complete
- Обработка `query.message is None`

### AI-консультация
- Вход в режим AI (проверка лимитов, paywall)
- Обработка вопросов в chatting state
- Выход из AI через меню-кнопки
- Quick-topic shortcuts

---

## Запуск тестов

```bash
# Все тесты
make test

# С покрытием (≥75% обязательно)
make test-cov

# Только bot-тесты
pytest tests/unit/test_handlers_*.py tests/unit/test_keyboards.py tests/unit/test_middleware.py -v

# Конкретный файл
pytest tests/unit/test_handlers_commands.py -v

# С отчётом по покрытию бота
pytest --cov=bot --cov-report=term-missing -q
```

---

## Правила

1. **Не модифицировать тесты ради прохождения** — если тест падает, исправить код
2. **Mock на границах** — мокаем `SessionFactory`, `build_services`, `allow_ai_request`, но не внутреннюю логику
3. **Каждый хэндлер — отдельный тест** — для атомарности
4. **Edge cases обязательны** — пустой текст, неизвестные команды, None значения
5. **asyncio_mode = "auto"** — все async тесты запускаются автоматически
