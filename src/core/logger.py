"""Logging setup."""

import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import aiohttp

from .config import settings


class TelegramHandler(logging.Handler):
    """Send logs to Telegram."""

    def __init__(self, token: str, chat_id: int) -> None:
        super().__init__()
        self.token = token
        self.chat_id = chat_id
        self.api_url = f'https://api.telegram.org/bot{token}/sendMessage'
        self.session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> None:
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def _send(self, message: str) -> None:
        await self._ensure_session()
        try:
            await self.session.post(
                self.api_url,
                json={
                    'chat_id': self.chat_id,
                    'text': f'<code>{message[:4000]}</code>',
                    'parse_mode': 'HTML',
                },
            )
        except Exception as e:
            print(f'Telegram log failed: {e}', file=sys.stderr)

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._send(message))
        except RuntimeError:
            asyncio.run(self._send(message))


async def init_logger() -> None:
    """Initialize logging."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper()))

    if root.handlers:
        return

    fmt = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )

    # Console
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    console.setLevel(logging.DEBUG)
    root.addHandler(console)

    # File
    try:
        Path(settings.log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            settings.log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding='utf-8',
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(logging.INFO)
        root.addHandler(file_handler)
    except Exception as e:
        print(f'File handler error: {e}', file=sys.stderr)

    # Telegram
    if (
        settings.log_tg_enabled
        and settings.log_tg_token
        and settings.log_tg_chat_id
    ):
        tg_handler = TelegramHandler(
            settings.log_tg_token, settings.log_tg_chat_id
        )
        tg_handler.setFormatter(fmt)
        tg_handler.setLevel(logging.INFO)
        root.addHandler(tg_handler)

    logging.getLogger('telethon').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
