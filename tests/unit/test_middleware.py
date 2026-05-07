"""Tests for bot.middleware."""

from unittest.mock import AsyncMock, MagicMock

from bot.middleware import ErrorHandlerMiddleware, UserInjectMiddleware


class TestErrorHandlerMiddleware:
    async def test_success_passthrough(self):
        middleware = ErrorHandlerMiddleware()
        handler = AsyncMock(return_value="ok")
        result = await middleware(handler, MagicMock(), {})
        assert result == "ok"

    async def test_exception_in_message_handler(self):
        from aiogram.types import Message
        middleware = ErrorHandlerMiddleware()
        handler = AsyncMock(side_effect=RuntimeError("boom"))
        event = MagicMock(spec=Message)
        event.chat = MagicMock()
        event.answer = AsyncMock()

        result = await middleware(handler, event, {})
        assert result is None
        event.answer.assert_awaited_once()
        assert "ошибка" in event.answer.call_args[0][0].lower()

    async def test_exception_in_callback_handler(self):
        from aiogram.types import CallbackQuery
        middleware = ErrorHandlerMiddleware()
        handler = AsyncMock(side_effect=RuntimeError("boom"))
        event = MagicMock(spec=CallbackQuery)
        event.message = MagicMock()
        event.answer = AsyncMock()

        result = await middleware(handler, event, {})
        assert result is None
        event.answer.assert_awaited_once()

    async def test_exception_in_error_sending(self):
        from aiogram.types import Message
        middleware = ErrorHandlerMiddleware()
        handler = AsyncMock(side_effect=RuntimeError("boom"))
        event = MagicMock(spec=Message)
        event.chat = MagicMock()
        event.answer = AsyncMock(side_effect=RuntimeError("send failed"))

        result = await middleware(handler, event, {})
        assert result is None


def _make_mock_client():
    client = AsyncMock()
    client.ensure_user = AsyncMock(return_value={"user_id": "u1", "telegram_id": 123})
    client.get_profile = AsyncMock(return_value={"profile": {"entity_type": "ip"}})
    client.subscription_status = AsyncMock(return_value={"is_active": False})
    client.touch = AsyncMock(return_value={})
    return client


class TestUserInjectMiddleware:
    async def test_injects_user_data(self):
        mc = _make_mock_client()
        profile_data = {"entity_type": "ip"}
        mc.get_profile = AsyncMock(return_value={"profile": profile_data})
        sub_data = {"is_active": True, "remaining_ai_requests": 3}
        mc.subscription_status = AsyncMock(return_value=sub_data)

        from aiogram.types import Message
        actor = MagicMock()
        actor.id = 123
        actor.username = "alice"
        actor.first_name = "Alice"
        event = MagicMock(spec=Message)
        event.text = "/start"

        handler = AsyncMock(return_value="ok")
        data = {"event_from_user": actor}
        mw = UserInjectMiddleware(client=mc)
        result = await mw(handler, event, data)
        assert result == "ok"
        assert data["db_user"] == {"user_id": "u1", "telegram_id": 123}
        assert data["db_profile"] == profile_data
        assert data["db_subscription"] == sub_data
        mc.touch.assert_awaited()

    async def test_callback_event(self):
        mc = _make_mock_client()

        from aiogram.types import CallbackQuery
        actor = MagicMock()
        actor.id = 123
        actor.username = "bob"
        actor.first_name = "Bob"
        event = MagicMock(spec=CallbackQuery)
        event.data = "action:1"

        handler = AsyncMock(return_value="ok")
        data = {"event_from_user": actor}
        mw = UserInjectMiddleware(client=mc)
        await mw(handler, event, data)
        mc.touch.assert_awaited()

    async def test_no_actor_passthrough(self):
        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        data = {}
        mw = UserInjectMiddleware(client=_make_mock_client())
        result = await mw(handler, event, data)
        assert result == "ok"

    async def test_touch_called_with_command(self):
        mc = _make_mock_client()

        from aiogram.types import Message
        actor = MagicMock()
        actor.id = 123
        actor.username = "alice"
        actor.first_name = "Alice"
        event = MagicMock(spec=Message)
        event.text = "/start"

        handler = AsyncMock(return_value="ok")
        data = {"event_from_user": actor}
        mw = UserInjectMiddleware(client=mc)
        await mw(handler, event, data)
        mc.touch.assert_awaited_once()
        call_kwargs = mc.touch.call_args[1]
        assert call_kwargs["event_type"] == "command"
        assert call_kwargs["payload"]["command"] == "start"
