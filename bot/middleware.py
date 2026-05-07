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
    """Injects user/profile/subscription data into handler data via BackendClient."""

    def __init__(self, client: BackendClient | None = None) -> None:
        super().__init__()
        self._client = client

    def _get_client(self) -> BackendClient:
        if self._client is not None:
            return self._client
        from shared.config import get_settings
        settings = get_settings()
        base_url = getattr(settings, "backend_base_url", "http://backend:8080")
        self._client = BackendClient(base_url=base_url)
        return self._client

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        actor = data.get("event_from_user")
        if actor is None:
            return await handler(event, data)

        client = self._get_client()

        user_data = await client.ensure_user(
            telegram_id=actor.id,
            username=actor.username,
            first_name=actor.first_name,
            timezone="Europe/Moscow",
        )
        user_id = user_data.get("user_id", "")
        profile_data = await client.get_profile(user_id)
        sub_data = await client.subscription_status(user_id)

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

        await client.touch(
            telegram_id=actor.id,
            username=actor.username,
            first_name=actor.first_name,
            event_type=event_type,
            payload=payload,
        )

        data["db_user"] = user_data
        data["db_profile"] = profile_data.get("profile")
        data["db_subscription"] = sub_data

        return await handler(event, data)
