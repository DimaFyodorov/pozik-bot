"""Pozik Bot - Telegram userbot with AI integration."""

import asyncio
import signal
import sys
from pathlib import Path

from ai import DeepSeekModel, GeminiModel, Router
from bot import create_client, register_handlers
from core import (
    AccessControl,
    AntiSpam,
    ContextManager,
    SearchEngine,
    init_logger,
    settings,
)
from core.storage import JsonStore


class BotApplication:
    """Main application orchestrator."""

    def __init__(self) -> None:
        """Initialize all components."""
        self.client = None
        self.router = None
        self.context_manager = None
        self.access = None
        self.anti_spam = None
        self.search = None
        self.handlers = None

    async def initialize(self) -> None:
        """Initialize all bot components."""
        # AI Models
        deepseek = DeepSeekModel(
            api_key=settings.deepseek_api_key,
            model=settings.model_deepseek,
        )
        gemini = GeminiModel(
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
            model=settings.model_gemini,
        )
        self.router = Router(deepseek=deepseek, gemini=gemini)

        # Context & Storage
        enabled_store = JsonStore(
            Path(settings.data_path) / 'enabled_chats.json'
        )
        banned_store = JsonStore(Path(settings.data_path) / 'banned_users.json')
        self.access = AccessControl(enabled_store, banned_store)
        self.context_manager = ContextManager(
            router=self.router,
            limit=settings.context_limit,
            keep=settings.context_keep,
            data_path=settings.data_path,
        )
        self.anti_spam = AntiSpam(cooldown=settings.rate_limit_seconds)
        self.search = SearchEngine()

        # Telegram Client

        self.client = await create_client()

        # Register handlers
        from bot.handlers import MessageHandlers

        self.handlers = MessageHandlers(
            client=self.client,
            router=self.router,
            context_manager=self.context_manager,
            access=self.access,
            anti_spam=self.anti_spam,
            search=self.search,
        )
        register_handlers(self.client, self.handlers)

    async def run(self) -> None:
        """Run the bot."""
        await self.initialize()
        await self.client.run_until_disconnected()

    async def stop(self) -> None:
        """Gracefully stop the bot."""
        if self.context_manager:
            await self.context_manager.shutdown()
        if self.client:
            await self.client.disconnect()


async def main() -> None:
    """Entry point with signal handling."""
    await init_logger()

    app = BotApplication()

    loop = asyncio.get_running_loop()

    def handle_signal(sig: int, _) -> None:
        """Handle shutdown signals."""
        asyncio.create_task(app.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal, sig, None)

    try:
        await app.run()
    except KeyboardInterrupt:
        pass
    finally:
        await app.stop()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f'Fatal error: {e}', file=sys.stderr)
        sys.exit(1)
