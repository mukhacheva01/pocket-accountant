import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


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
    """Injects db_user and db_profile into handler data via backend API."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        actor = data.get("event_from_user")
        if actor is None:
            return await handler(event, data)

        from bot.runtime import get_backend_client

        client = get_backend_client()

        event_type = "message"
        payload: Dict[str, Any] = {"source": event.__class__.__name__}
        command: str | None = None

        if isinstance(event, Message):
            text = (event.text or "").strip()
            if text.startswith("/"):
                command = text.split()[0].lstrip("/").lower()
                event_type = "command"
                payload["command"] = command
            else:
                payload["text_length"] = len(text)
        elif isinstance(event, CallbackQuery):
            event_type = "callback"
            payload["callback_data"] = event.data or ""

        try:
            result = await client.track_activity(
                telegram_id=actor.id,
                username=actor.username,
                first_name=actor.first_name,
                event_type=event_type,
                payload=payload,
                command=command,
            )
            data["db_user"] = result
            data["db_profile"] = result.get("profile")
            data["db_subscription"] = result.get("subscription")
        except Exception:
            logger.exception("user_inject_middleware_error")

        return await handler(event, data)
