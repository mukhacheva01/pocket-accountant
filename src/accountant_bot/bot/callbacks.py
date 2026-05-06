from aiogram.filters.callback_data import CallbackData


class EventActionCallback(CallbackData, prefix="event"):
    action: str
    event_id: str


class PageCallback(CallbackData, prefix="page"):
    screen: str
    page: int


class NavigationCallback(CallbackData, prefix="nav"):
    target: str


class SubscriptionCallback(CallbackData, prefix="sub"):
    action: str
    plan: str
