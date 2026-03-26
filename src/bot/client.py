"""Telegram client creation."""

import logging

from telethon import TelegramClient

from core.config import settings

logger = logging.getLogger(__name__)


async def create_client() -> TelegramClient:
    """Create and start Telegram client."""
    client = TelegramClient(
        settings.session_path,
        settings.api_id,
        settings.api_hash,
    )

    await client.start()
    logger.info('Telegram client started (session: %s)', settings.session_path)
    return client
