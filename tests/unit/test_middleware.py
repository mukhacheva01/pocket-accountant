"""Tests for bot.middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.middleware import ErrorHandlerMiddleware


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
