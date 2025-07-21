import asyncio
import logging
from datetime import UTC, datetime
from typing import ClassVar, Self, override

from discord import Color, Embed, Webhook

from app.core.config import get_config


class DiscordWebhookHandler(logging.Handler):
    """
    A synchronous logging handler that sends logs to a Discord webhook.

    This is a simpler version that uses blocking HTTP requests.
    For production use, consider using AsyncDiscordWebhookHandler instead.
    """

    MAX_EMBED_DESCRIPTION: ClassVar[int] = 4096  # Discord's maximum embed description length
    MAX_CONTENT_LENGTH: ClassVar[int] = 2000  # Discord's maximum message content length
    DECORATORS_LEN: ClassVar[int] = 8  # Characters taken by ` and \n

    COLOR_MAP: ClassVar[dict[int, Color]] = {
        logging.NOTSET: Color.default(),
        logging.DEBUG: Color.blue(),
        logging.INFO: Color.green(),
        logging.WARNING: Color.yellow(),
        logging.ERROR: Color.red(),
        logging.CRITICAL: Color.red(),
    }

    def __init__(self, webhook_url: str) -> None:
        """
        Initialize the Discord webhook handler.

        Args:
            webhook_url: The Discord webhook URL to send logs to
        """
        super().__init__()
        self.webhook_url: str = webhook_url

    @classmethod
    def from_config(cls) -> Self:
        """
        Create a handler instance from application configuration.

        Returns:
            Configured handler instance
        """
        config = get_config()
        webhook_url = config.general.discord_webhook
        if not webhook_url:
            raise ValueError("Discord webhook URL not configured")
        return cls(webhook_url=webhook_url)

    def format_footer(self, record: logging.LogRecord) -> str:
        """Formats the timestamp from the log record for the embed footer."""
        dt = datetime.fromtimestamp(record.created, UTC)
        return (
            f"{dt.strftime('%Y-%m-%d %H:%M:%S UTC')} "
            f"- {record.process}:{record.processName} "
            f"- {record.funcName}:{record.lineno}"
        )

    @override
    def emit(self, record: logging.LogRecord) -> None:
        """Send the log record to the Discord webhook as an embed or plain text if too large."""
        try:
            formatted_message = self.format(record)

            if len(formatted_message) > self.MAX_EMBED_DESCRIPTION:
                self._send_as_content(record, formatted_message)
            else:
                self._send_as_embed(record, formatted_message)

        except Exception:
            self.handleError(record)

    def _send_as_embed(self, record: logging.LogRecord, formatted_message: str) -> None:
        """Send log record as a rich embed."""
        embed = Embed(title=record.name, description=formatted_message, color=self.COLOR_MAP.get(record.levelno))
        embed.set_footer(text=self.format_footer(record))

        webhook = Webhook.from_url(self.webhook_url)
        asyncio.run(webhook.send(embed=embed))

    def _send_as_content(self, record: logging.LogRecord, formatted_message: str) -> None:
        """Send long log record as split plain text messages."""
        webhook = Webhook.from_url(self.webhook_url)

        base_content = f"[{record.levelname}] {self.format_footer(record)} - {record.name}:\n"
        asyncio.run(webhook.send(content=base_content))

        available_length = self.MAX_CONTENT_LENGTH - self.DECORATORS_LEN
        lines = formatted_message.splitlines()
        chunk = ""
        chunks: list[str] = []

        for line in lines:
            # Check if adding this line would exceed the available length
            if len(chunk) + len(line) + 1 > available_length:  # +1 for newline
                chunks.append(chunk)
                chunk = line
            else:
                if chunk:
                    chunk += "\n"
                chunk += line

        # Append the last chunk if it exists
        if chunk:
            chunks.append(chunk)

        for chunk in chunks:
            content = f"```\n{chunk}\n```"
            asyncio.run(webhook.send(content=content[: self.MAX_CONTENT_LENGTH]))
