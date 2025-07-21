import logging
from logging import LogRecord
from unittest.mock import Mock

import pytest
from app.core.log_handlers import DiscordWebhookHandler
from discord import Color, Embed
from pytest_mock import MockerFixture


@pytest.fixture
def log_record() -> LogRecord:
    return LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="file.py",
        func="test_function",
        lineno=42,
        msg="Test info message",
        args=(),
        exc_info=None,
    )


class TestDiscordWebhookHandler:
    def test_emit(self, mocker: MockerFixture, log_record: LogRecord) -> None:
        webhook_mock = Mock()
        webhook_from_url_mock = mocker.patch("app.core.log_handlers.Webhook.from_url", return_value=webhook_mock)

        handler = DiscordWebhookHandler(webhook_url="https://discord.com/api/webhooks/test")
        handler.emit(log_record)

        webhook_from_url_mock.assert_called_once_with("https://discord.com/api/webhooks/test")
        webhook_mock.send.assert_called_once()

        _, kwargs = webhook_mock.send.call_args
        embed: Embed = kwargs["embed"]
        assert embed.description == "Test info message"
        assert embed.title == "test_logger"
        assert embed.color == Color.green()
        assert embed.footer is not None
        assert "test_function:42" in (embed.footer.text or "")

    def test_emit_with_error(self, mocker: MockerFixture, log_record: LogRecord) -> None:
        webhook_mock = Mock()
        mocker.patch("app.core.log_handlers.Webhook.from_url", return_value=webhook_mock)
        webhook_mock.send.side_effect = Exception("Network error")

        handler = DiscordWebhookHandler(webhook_url="https://discord.com/api/webhooks/test")

        handle_error_mock = mocker.patch.object(handler, "handleError")

        handler.emit(log_record)

        webhook_mock.send.assert_called_once()
        handle_error_mock.assert_called_once_with(log_record)

    def test_from_config(self, mocker: MockerFixture) -> None:
        config_mock = Mock()
        mocker.patch("app.core.log_handlers.get_config", return_value=config_mock)
        config_mock.general.discord_webhook = "https://discord.com/api/webhooks/test"

        handler = DiscordWebhookHandler.from_config()

        assert handler.webhook_url == "https://discord.com/api/webhooks/test"

    def test_from_config_with_missing_option(self, mocker: MockerFixture) -> None:
        config_mock = Mock()
        mocker.patch("app.core.log_handlers.get_config", return_value=config_mock)
        config_mock.general.discord_webhook = None

        with pytest.raises(ValueError, match="Discord webhook URL not configured"):
            DiscordWebhookHandler.from_config()
