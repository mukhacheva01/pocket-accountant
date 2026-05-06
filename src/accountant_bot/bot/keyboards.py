from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from accountant_bot.bot.callbacks import EventActionCallback, NavigationCallback, PageCallback, SubscriptionCallback


def onboarding_entity_type_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Самозанятый"), KeyboardButton(text="ИП")],
            [KeyboardButton(text="ООО"), KeyboardButton(text="Пока не открыт")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выбери форму бизнеса",
    )


def planned_entity_type_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Самозанятый"), KeyboardButton(text="ИП")],
            [KeyboardButton(text="ООО")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Что планируешь открыть",
    )


def onboarding_tax_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="УСН 6%"), KeyboardButton(text="УСН доходы-расходы")],
            [KeyboardButton(text="ОСНО"), KeyboardButton(text="НПД")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выбери налоговый режим",
    )


def yes_no_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Ответь Да или Нет",
    )


def reminder_offsets_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="3,1")],
            [KeyboardButton(text="7,3,1")],
            [KeyboardButton(text="7,3,1,0")],
            [KeyboardButton(text="1,0")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Выбери интервалы напоминаний",
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Главная"), KeyboardButton(text="💬 AI Консультация")],
            [KeyboardButton(text="📅 События"), KeyboardButton(text="📋 Что подать")],
            [KeyboardButton(text="💰 Добавить доход"), KeyboardButton(text="💸 Добавить расход")],
            [KeyboardButton(text="📊 Финансы"), KeyboardButton(text="🔍 Подобрать режим")],
            [KeyboardButton(text="⭐ Подписка"), KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Напиши вопрос или выбери раздел",
    )


def navigation_keyboard(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=NavigationCallback(target=target).pack(),
                )
                for label, target in row
            ]
            for row in rows
        ]
    )


def back_home_row() -> list[tuple[str, str]]:
    return [("🏠 В меню", "home")]


def section_shortcuts_keyboard() -> InlineKeyboardMarkup:
    return navigation_keyboard(
        [
            [("📅 События", "events"), ("📋 Документы", "documents")],
            [("📊 Финансы", "finance"), ("👤 Профиль", "profile")],
            back_home_row(),
        ]
    )


def finance_shortcuts_keyboard() -> InlineKeyboardMarkup:
    return navigation_keyboard(
        [
            [("➕ Доход", "income_prompt"), ("➖ Расход", "expense_prompt")],
            [("💰 Баланс", "balance"), ("📊 Отчёт", "finance")],
            [("📈 Доходы", "income_list"), ("📉 Расходы", "expense_list")],
            back_home_row(),
        ]
    )


def documents_shortcuts_keyboard() -> InlineKeyboardMarkup:
    return navigation_keyboard(
        [
            [("📅 События", "events"), ("🔔 Напоминания", "reminders")],
            [("📊 Финансы", "finance")],
            back_home_row(),
        ]
    )


def profile_shortcuts_keyboard() -> InlineKeyboardMarkup:
    return navigation_keyboard(
        [
            [("📅 События", "events"), ("📋 Документы", "documents")],
            [("🔄 Обновить профиль", "restart_onboarding")],
            back_home_row(),
        ]
    )


def laws_shortcuts_keyboard() -> InlineKeyboardMarkup:
    return navigation_keyboard(
        [
            [("📋 Документы", "documents"), ("📅 События", "events")],
            back_home_row(),
        ]
    )


def reminders_shortcuts_keyboard() -> InlineKeyboardMarkup:
    return navigation_keyboard(
        [
            [("📅 События", "events"), ("⚙️ Настройки", "settings")],
            back_home_row(),
        ]
    )


def settings_shortcuts_keyboard() -> InlineKeyboardMarkup:
    return navigation_keyboard(
        [
            [("🔄 Обновить профиль", "restart_onboarding")],
            [("🔔 Напоминания", "reminders"), ("❓ Помощь", "help")],
            back_home_row(),
        ]
    )


def help_shortcuts_keyboard() -> InlineKeyboardMarkup:
    return navigation_keyboard(
        [
            [("🏠 Главная", "home"), ("📊 Финансы", "finance")],
            [("🔍 Подобрать режим", "pick_regime"), ("📰 Законы", "laws")],
            back_home_row(),
        ]
    )


def regime_activity_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Услуги"), KeyboardButton(text="Торговля")],
            [KeyboardButton(text="Аренда"), KeyboardButton(text="Производство")],
            [KeyboardButton(text="Другое")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def regime_income_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="100000"), KeyboardButton(text="300000")],
            [KeyboardButton(text="700000"), KeyboardButton(text="1500000")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Доход в месяц, ₽",
    )


def counterparties_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Физлица"), KeyboardButton(text="Юрлица/ИП")],
            [KeyboardButton(text="Смешанно")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def event_actions_keyboard(event_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Выполнено",
                    callback_data=EventActionCallback(action="done", event_id=event_id).pack(),
                ),
                InlineKeyboardButton(
                    text="⏰ Отложить",
                    callback_data=EventActionCallback(action="snooze", event_id=event_id).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 Документы",
                    callback_data=NavigationCallback(target="documents").pack(),
                ),
                InlineKeyboardButton(
                    text="🏠 В меню",
                    callback_data=NavigationCallback(target="home").pack(),
                ),
            ],
        ]
    )


def subscription_keyboard(prices: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⭐ Базовый — {prices['basic']} Stars/мес",
                    callback_data=SubscriptionCallback(action="buy", plan="basic").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🚀 Про — {prices['pro']} Stars/мес",
                    callback_data=SubscriptionCallback(action="buy", plan="pro").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"💎 Годовой — {prices['annual']} Stars (экономия 30%)",
                    callback_data=SubscriptionCallback(action="buy", plan="annual").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👥 Пригласить друга (+3 запроса)",
                    callback_data=NavigationCallback(target="referral").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏠 В меню",
                    callback_data=NavigationCallback(target="home").pack(),
                ),
            ],
        ]
    )


def subscription_manage_keyboard() -> InlineKeyboardMarkup:
    return navigation_keyboard(
        [
            [("💳 Сменить тариф", "subscription"), ("🚫 Отменить подписку", "cancel_subscription")],
            [("👥 Рефералы", "referral")],
            back_home_row(),
        ]
    )


def retry_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Попробовать снова",
                    callback_data=NavigationCallback(target="home").pack(),
                ),
            ]
        ]
    )


def ai_consult_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🧮 Рассчитать налог", callback_data=NavigationCallback(target="ai_topic_calc").pack()),
                InlineKeyboardButton(text="📅 Сроки и дедлайны", callback_data=NavigationCallback(target="ai_topic_deadlines").pack()),
            ],
            [
                InlineKeyboardButton(text="📋 Отчётность", callback_data=NavigationCallback(target="ai_topic_reports").pack()),
                InlineKeyboardButton(text="💰 Взносы и вычеты", callback_data=NavigationCallback(target="ai_topic_deductions").pack()),
            ],
            [
                InlineKeyboardButton(text="🔍 Сравнить режимы", callback_data=NavigationCallback(target="pick_regime").pack()),
                InlineKeyboardButton(text="📰 Изменения законов", callback_data=NavigationCallback(target="laws").pack()),
            ],
            [
                InlineKeyboardButton(text="🗑 Новый диалог", callback_data=NavigationCallback(target="ai_clear_history").pack()),
            ],
            [
                InlineKeyboardButton(text="🏠 Завершить", callback_data=NavigationCallback(target="ai_exit").pack()),
            ],
        ]
    )


def ai_consult_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Главная"), KeyboardButton(text="🗑 Новый диалог")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Задай вопрос по налогам и бухгалтерии",
    )
