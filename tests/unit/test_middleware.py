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


class TestUserInjectMiddleware:
    async def test_injects_user_data(self):
        client = AsyncMock()
        user_data = {"id": "u1", "username": "alice"}
        profile_data = {"entity_type": "ip"}
        sub_data = {"plan": "basic"}
        client.track_activity = AsyncMock(return_value={
            "user": user_data, "profile": profile_data, "subscription": sub_data,
        })

        from aiogram.types import Message
        actor = MagicMock()
        actor.id = 123
        actor.username = "alice"
        actor.first_name = "Alice"
        event = MagicMock(spec=Message)
        event.text = "/start"

        handler = AsyncMock(return_value="ok")
        data = {"event_from_user": actor}
        mw = UserInjectMiddleware(client=client)
        result = await mw(handler, event, data)
        assert result == "ok"
        assert data["db_user"] == user_data
        assert data["db_profile"] == profile_data
        assert data["db_subscription"] == sub_data
        client.track_activity.assert_awaited_once()
        call_kwargs = client.track_activity.call_args[1]
        assert call_kwargs["event_type"] == "command"
        assert call_kwargs["payload"]["command"] == "start"

    async def test_callback_event(self):
        client = AsyncMock()
        client.track_activity = AsyncMock(return_value={
            "user": {"id": "u1"}, "profile": None, "subscription": None,
        })

        from aiogram.types import CallbackQuery
        actor = MagicMock()
        actor.id = 123
        actor.username = "bob"
        actor.first_name = "Bob"
        event = MagicMock(spec=CallbackQuery)
        event.data = "action:1"

        handler = AsyncMock(return_value="ok")
        data = {"event_from_user": actor}
        mw = UserInjectMiddleware(client=client)
        result = await mw(handler, event, data)
        assert result == "ok"
        call_kwargs = client.track_activity.call_args[1]
        assert call_kwargs["event_type"] == "callback"
        assert call_kwargs["payload"]["callback_data"] == "action:1"

    async def test_no_actor_passthrough(self):
        client = AsyncMock()
        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        data = {}
        mw = UserInjectMiddleware(client=client)
        result = await mw(handler, event, data)
        assert result == "ok"
        client.track_activity.assert_not_awaited()

    async def test_backend_error_still_calls_handler(self):
        client = AsyncMock()
        client.track_activity = AsyncMock(side_effect=RuntimeError("backend down"))

        from aiogram.types import Message
        actor = MagicMock()
        actor.id = 123
        actor.username = "alice"
        actor.first_name = "Alice"
        event = MagicMock(spec=Message)
        event.text = "hello"

        handler = AsyncMock(return_value="ok")
        data = {"event_from_user": actor}
        mw = UserInjectMiddleware(client=client)
        result = await mw(handler, event, data)
        assert result == "ok"
        assert "db_user" not in data

    async def test_plain_message_event_type(self):
        client = AsyncMock()
        client.track_activity = AsyncMock(return_value={
            "user": {"id": "u1"}, "profile": None, "subscription": None,
        })

        from aiogram.types import Message
        actor = MagicMock()
        actor.id = 123
        actor.username = "alice"
        actor.first_name = "Alice"
        event = MagicMock(spec=Message)
        event.text = "hello world"

        handler = AsyncMock(return_value="ok")
        data = {"event_from_user": actor}
        mw = UserInjectMiddleware(client=client)
        await mw(handler, event, data)
        call_kwargs = client.track_activity.call_args[1]
        assert call_kwargs["event_type"] == "message"
        assert call_kwargs["payload"]["text_length"] == 11
