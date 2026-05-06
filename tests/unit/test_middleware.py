"""Tests for bot.middleware."""

from unittest.mock import AsyncMock, MagicMock, patch


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
    @patch("bot.middleware.SessionFactory")
    @patch("bot.middleware.build_services")
    async def test_injects_user_data(self, mock_build, mock_sf):
        session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_sf.return_value.__aexit__ = AsyncMock()
        session.commit = AsyncMock()
        session.add = MagicMock()

        user = MagicMock()
        user.id = "u1"
        user.is_active = True
        profile = MagicMock()
        sub = MagicMock()

        services = MagicMock()
        services.onboarding.ensure_user = AsyncMock(return_value=user)
        services.onboarding.load_profile = AsyncMock(return_value=profile)
        services.subscription.get_subscription = AsyncMock(return_value=sub)
        mock_build.return_value = services

        from aiogram.types import Message
        actor = MagicMock()
        actor.id = 123
        actor.username = "alice"
        actor.first_name = "Alice"
        event = MagicMock(spec=Message)
        event.text = "/start"

        handler = AsyncMock(return_value="ok")
        data = {"event_from_user": actor}
        mw = UserInjectMiddleware()
        result = await mw(handler, event, data)
        assert result == "ok"
        assert data["db_user"] == user
        assert data["db_profile"] == profile
        assert data["db_subscription"] == sub
        assert user.last_command == "start"

    @patch("bot.middleware.SessionFactory")
    @patch("bot.middleware.build_services")
    async def test_callback_event(self, mock_build, mock_sf):
        session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_sf.return_value.__aexit__ = AsyncMock()
        session.commit = AsyncMock()
        session.add = MagicMock()

        user = MagicMock()
        user.id = "u1"
        user.is_active = True
        services = MagicMock()
        services.onboarding.ensure_user = AsyncMock(return_value=user)
        services.onboarding.load_profile = AsyncMock(return_value=None)
        services.subscription.get_subscription = AsyncMock(return_value=None)
        mock_build.return_value = services

        from aiogram.types import CallbackQuery
        actor = MagicMock()
        actor.id = 123
        actor.username = "bob"
        actor.first_name = "Bob"
        event = MagicMock(spec=CallbackQuery)
        event.data = "action:1"

        handler = AsyncMock(return_value="ok")
        data = {"event_from_user": actor}
        mw = UserInjectMiddleware()
        await mw(handler, event, data)

    async def test_no_actor_passthrough(self):
        handler = AsyncMock(return_value="ok")
        event = MagicMock()
        data = {}
        mw = UserInjectMiddleware()
        result = await mw(handler, event, data)
        assert result == "ok"

    @patch("bot.middleware.SessionFactory")
    @patch("bot.middleware.build_services")
    async def test_reactivates_inactive_user(self, mock_build, mock_sf):
        session = AsyncMock()
        mock_sf.return_value.__aenter__ = AsyncMock(return_value=session)
        mock_sf.return_value.__aexit__ = AsyncMock()
        session.commit = AsyncMock()
        session.add = MagicMock()

        user = MagicMock()
        user.id = "u1"
        user.is_active = False
        services = MagicMock()
        services.onboarding.ensure_user = AsyncMock(return_value=user)
        services.onboarding.load_profile = AsyncMock(return_value=None)
        services.subscription.get_subscription = AsyncMock(return_value=None)
        mock_build.return_value = services

        from aiogram.types import Message
        actor = MagicMock()
        actor.id = 123
        actor.username = "alice"
        actor.first_name = "Alice"
        event = MagicMock(spec=Message)
        event.text = "hello"

        handler = AsyncMock(return_value="ok")
        data = {"event_from_user": actor}
        mw = UserInjectMiddleware()
        await mw(handler, event, data)
        assert user.is_active is True
        assert user.reactivated_at is not None
