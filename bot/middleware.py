import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.backend_client import BackendClient


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
    """Injects user context into handler data via BackendClient."""

    def __init__(self, client: BackendClient) -> None:
        super().__init__()
        self.client = client

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        actor = data.get("event_from_user")
        if actor is None:
            return await handler(event, data)

        user_data = await self.client.ensure_user(
            telegram_id=actor.id,
            username=actor.username,
            first_name=actor.first_name,
            timezone="Europe/Moscow",
        )
        profile_data = await self.client.get_profile(user_data["user_id"])
        sub_data = await self.client.subscription_status(user_data["user_id"])

        event_type = "message"
        payload: Dict[str, Any] = {"source": event.__class__.__name__}
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
            await self.client.record_activity(user_data["user_id"], event_type, payload)
        except Exception:
            logger.warning("failed_to_record_activity", exc_info=True)

        data["db_user"] = user_data
        data["db_profile"] = profile_data
        data["db_subscription"] = sub_data

        return await handler(event, data)
