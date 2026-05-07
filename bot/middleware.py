import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from shared.clock import utcnow
from shared.db.models import UserActivity
from shared.db.session import SessionFactory
from backend.services.container import build_services


logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception:
            logger.exception("unhandled_error_in_handler")
            try:
                if isinstance(event, Message) and event.chat:
                    await event.answer(
                        "⚠️ Произошла ошибка. Попробуй ещё раз или напиши /menu"
                    )
                elif isinstance(event, CallbackQuery) and event.message:
                    await event.answer("Ошибка, попробуй ещё раз", show_alert=True)
            except Exception:
                logger.exception("error_sending_error_message")
            return None


class UserInjectMiddleware(BaseMiddleware):
    """Injects db_user and db_profile into handler data."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        actor = data.get("event_from_user")
        if actor is None:
            return await handler(event, data)

        async with SessionFactory() as session:
            services = build_services(session)
            user = await services.onboarding.ensure_user(
                telegram_id=actor.id,
                username=actor.username,
                first_name=actor.first_name,
                timezone="Europe/Moscow",
            )
            profile = await services.onboarding.load_profile(str(user.id))
            sub = await services.subscription.get_subscription(str(user.id))
            now = utcnow()
            user.last_seen_at = now
            if not user.is_active:
                user.is_active = True
                user.reactivated_at = now

            event_type = "message"
            payload: Dict[str, Any] = {"source": event.__class__.__name__}
            if isinstance(event, Message):
                text = (event.text or "").strip()
                if text.startswith("/"):
                    command = text.split()[0].lstrip("/").lower()
                    event_type = "command"
                    payload["command"] = command
                    user.last_command = command
                else:
                    payload["text_length"] = len(text)
            elif isinstance(event, CallbackQuery):
                event_type = "callback"
                payload["callback_data"] = event.data or ""

            session.add(UserActivity(user_id=user.id, event_type=event_type, payload=payload))
            await session.commit()

            data["db_user"] = user
            data["db_profile"] = profile
            data["db_subscription"] = sub

        return await handler(event, data)
