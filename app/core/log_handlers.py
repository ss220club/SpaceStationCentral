import logging
from datetime import UTC, datetime
from typing import override

import requests

from app.core.config import CONFIG


class DiscordWebhookHandler(logging.Handler):
    """
    A logging handler that sends logs to a Discord webhook with formatted embeds or plain text for large messages.
    """

    MAX_EMBED_DESCRIPTION: int = 4096  # Discord's maximum embed description length
    MAX_CONTENT_LENGTH: int = 2000  # Discord's maximum message content length
    DECORATORS_LEN: int = 8  # Characters taken by ` and \n
    COLOR_MAP: dict[int, int] = {  # noqa: RUF012
        logging.DEBUG: 255,  # Blue
        logging.INFO: 65280,  # Green
        logging.WARNING: 16776960,  # Yellow
        logging.ERROR: 16711680,  # Red
        logging.CRITICAL: 16711680,  # Red
    }

    webhook_url: str = CONFIG.general.discord_webhook

    def get_color(self, level: int) -> int:
        """
        Returns the Discord embed color code for the given log level.
        """
        return next(
            (color for log_level, color in sorted(self.COLOR_MAP.items(), reverse=True) if level >= log_level),
            0,
        )

    def format_footer(self, record: logging.LogRecord) -> str:
        """
        Formats the timestamp from the log record for the embed footer.
        """
        dt = datetime.fromtimestamp(record.created, UTC)
        return (
            f"{dt.strftime('%Y-%m-%d %H:%M:%S UTC')} "
            f"- {record.process}:{record.processName} "
            f"- {record.funcName}:{record.lineno}"
        )

    @override
    def emit(self, record: logging.LogRecord) -> None:
        """
        Send the log record to the Discord webhook as an embed or plain text if too large.
        """
        try:
            formatted_message = self.format(record)

            if len(formatted_message) > self.MAX_EMBED_DESCRIPTION:
                self._send_as_content(record, formatted_message)
            else:
                self._send_as_embed(record, formatted_message)

        except Exception as _:
            self.handleError(record)

    def _send_as_embed(self, record: logging.LogRecord, formatted_message: str) -> None:
        """Send log record as a rich embed."""
        embed = {
            "title": record.name,
            "description": formatted_message,
            "color": self.get_color(record.levelno),
            "footer": {"text": self.format_footer(record)},
        }

        payload = {
            "embeds": [embed],
        }

        response = requests.post(self.webhook_url, json=payload, timeout=10)
        response.raise_for_status()

    def _send_as_content(self, record: logging.LogRecord, formatted_message: str) -> None:
        """Send long log record as split plain text messages."""
        base_content = f"[{record.levelname}] {self.format_footer(record)} - {record.name}:\n"
        payload = {
            "content": base_content,
        }
        requests.post(self.webhook_url, data=payload, timeout=10).raise_for_status()

        available_length = self.MAX_CONTENT_LENGTH - self.DECORATORS_LEN
        lines = formatted_message.splitlines()
        chunk = ""
        chunks: list[str] = []

        for line in lines:
            # Check if adding this line would exceed the available length
            if len(chunk) + len(line) + 1 > available_length:  # +1 accounts for the newline character
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
            payload = {
                "content": content[: self.MAX_CONTENT_LENGTH],
            }
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
